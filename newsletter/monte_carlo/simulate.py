"""Monte Carlo v1: 2026/27 U.S. corn ending-stocks / stocks-to-use / price distribution.

Method (see monte_carlo/README.md for full assumptions):
  1. Draw correlated forecast errors for production, ethanol grind, feed &
     residual (stated normal priors) and exports (empirical pace residuals,
     week-conditioned), correlated via the empirical first-difference
     correlation matrix of historical finals.
  2. Propagate through the balance-sheet identity -> ending stocks -> s/u.
  3. Map s/u -> price with the fitted Westcott-Hoffman inverse curve.
"""
import csv
import numpy as np
import openpyxl

from . import config as C
from . import price_model

LINES = ["production", "ethanol_grind", "feed_residual", "exports"]


def load_finals():
    wb = openpyxl.load_workbook(C.WORKBOOK, data_only=False)
    ws = wb["HIST_BALANCE"]
    rows = []
    for r in range(4, 20):  # 2010/11..2025/26 finals
        rows.append({
            "my": ws.cell(r, 1).value,
            "production": ws.cell(r, 6).value,
            "feed_residual": ws.cell(r, 9).value,
            "ethanol_grind": ws.cell(r, 11).value,
            "exports": ws.cell(r, 12).value,
        })
    return rows


def error_correlation(finals):
    """Empirical correlation of year-over-year first differences (proxy for
    forecast-error co-movement; see README). Order: LINES."""
    arr = np.array([[f[l] for l in LINES] for f in finals], dtype=float)
    d = np.diff(arr, axis=0)
    corr = np.corrcoef(d.T)
    return corr


def export_pct_residuals(week):
    """Implied-final vs actual-final commitment residuals (fraction) at a
    given marketing-year week, across the 20 staged years.

    implied_final(y, w) = commitment(y, w) / avg20_curve(w); the avg20 curve
    is self-normalized (converges to 100% of each year's own final), so
    residuals are mean ~0 by construction at week 53.
    Approximation: final commitments ~= final exports (within ~5% per the
    FAS validation report), so commitment residuals proxy export errors.
    """
    staged = {}
    with open(C.STAGED_WEEKLY) as f:
        for row in csv.DictReader(f):
            staged.setdefault(int(row["market_year"]),
                              {})[int(row["week_of_marketing_year"])] = \
                float(row["commitment_mil_bu"])
    curve = {}
    with open(C.SCURVE_WINDOWS) as f:
        for row in csv.DictReader(f):
            curve[int(row["week_of_marketing_year"])] = float(row["avg20_pct"])
    resid = []
    for y, wks in sorted(staged.items()):
        final = wks[53]
        implied = wks[week] / (curve[week] / 100.0)
        resid.append(implied / final - 1.0)
    return np.array(resid)


def draw_errors(n, seed, corr, export_resid):
    """Correlated error draws.

    Correlated standard normals via Cholesky; the export component is mapped
    through the empirical residual CDF (inverse-transform) so its marginal
    matches the week-conditioned pace residuals exactly.
    Returns dict of M-bu errors keyed by line.
    """
    rng = np.random.default_rng(seed)
    L = np.linalg.cholesky(corr)
    z = rng.standard_normal((n, 4)) @ L.T  # correlated N(0,1), order LINES
    # normal CDF of the export z -> uniform -> empirical residual quantile
    from scipy import stats  # noqa  (fallback below if missing)
    u = stats.norm.cdf(z[:, 3])
    q = np.quantile(export_resid, np.clip(u, 0, 1))
    return {
        "production": z[:, 0] * C.ERROR_SD["production"],
        "ethanol_grind": z[:, 1] * C.ERROR_SD["ethanol_grind"],
        "feed_residual": z[:, 2] * C.ERROR_SD["feed_residual"],
        "export_pct": q,  # fraction; applied multiplicatively to base exports
    }


def propagate(errors, price_params, prod_shift=0.0):
    """Balance-sheet identity per draw. Returns dict of arrays."""
    n = len(errors["production"])
    b = C.BASE
    prod = b["production"] + prod_shift + errors["production"]
    exp = b["exports"] * (1.0 + errors["export_pct"])
    eth = b["ethanol_grind"] + errors["ethanol_grind"]
    feed = b["feed_residual"] + errors["feed_residual"]
    supply = b["beg_stocks"] + prod + b["imports"]
    total_use = exp + eth + feed + b["fsi_non_ethanol"]
    ending = supply - total_use
    # identity check (vectorized): supply == total_use + ending, exactly
    assert np.allclose(supply, total_use + ending), "identity violated"
    su = ending / total_use
    price = price_model.predict(su, price_params)
    out_of_bounds = (su < C.SU_LO) | (su > C.SU_HI)
    return {
        "production": prod, "exports": exp, "ethanol": eth, "feed": feed,
        "supply": supply, "total_use": total_use, "ending": ending,
        "stocks_use": su, "price": price,
        "out_of_bounds": out_of_bounds,
    }


def summarize(draws):
    def pct(x, q):
        return float(np.percentile(x, q))
    return {
        "ending": {"mean": float(draws["ending"].mean()),
                   "sd": float(draws["ending"].std(ddof=1)),
                   "p10": pct(draws["ending"], 10), "p50": pct(draws["ending"], 50),
                   "p90": pct(draws["ending"], 90)},
        "stocks_use": {"mean": float(draws["stocks_use"].mean()),
                       "sd": float(draws["stocks_use"].std(ddof=1)),
                       "p10": pct(draws["stocks_use"], 10),
                       "p50": pct(draws["stocks_use"], 50),
                       "p90": pct(draws["stocks_use"], 90)},
        "price": {"mean": float(draws["price"].mean()),
                  "sd": float(draws["price"].std(ddof=1)),
                  "p10": pct(draws["price"], 10), "p50": pct(draws["price"], 50),
                  "p90": pct(draws["price"], 90)},
        "p_su_lt_10": float((draws["stocks_use"] < 0.10).mean()),
        "n_out_of_bounds": int(draws["out_of_bounds"].sum()),
        "n": len(draws["ending"]),
    }


def run(n=None, seed=None, week=None, prod_shift=0.0, verbose=True):
    n = n or C.N_DRAWS
    seed = C.SEED if seed is None else seed
    week = week or C.CURRENT_WEEK
    finals = load_finals()
    corr = error_correlation(finals)
    export_resid = export_pct_residuals(week)
    try:
        errors = draw_errors(n, seed, corr, export_resid)
    except ImportError:
        errors = _draw_errors_no_scipy(n, seed, corr, export_resid)
    price_params = price_model.fit()
    draws = propagate(errors, price_params, prod_shift=prod_shift)
    summary = summarize(draws)
    if verbose:
        print(f"week={week} n={n} seed={seed}")
        print("error corr (prod, eth, feed, exp):\n", np.round(corr, 3))
        print(f"export resid: n={len(export_resid)} mean={export_resid.mean():+.3f} "
              f"sd={export_resid.std(ddof=1):.3f}")
        print(f"price model: P = {price_params['a']:.3f} + "
              f"{price_params['b']:.4f}/(s/u), R2={price_params['r2']:.3f}")
        print("P50 ending=%.0f  P50 price=%.2f  P(s/u<10%%)=%.1f%%  OOB=%d" % (
            summary["ending"]["p50"], summary["price"]["p50"],
            summary["p_su_lt_10"] * 100, summary["n_out_of_bounds"]))
    return {"draws": draws, "summary": summary, "corr": corr,
            "export_resid": export_resid, "price_params": price_params,
            "finals": finals}


def _draw_errors_no_scipy(n, seed, corr, export_resid):
    """Fallback if scipy is unavailable: normal CDF via math.erf."""
    import math
    rng = np.random.default_rng(seed)
    L = np.linalg.cholesky(corr)
    z = rng.standard_normal((n, 4)) @ L.T
    u = np.vectorize(lambda v: 0.5 * (1 + math.erf(v / math.sqrt(2))))(z[:, 3])
    q = np.quantile(export_resid, np.clip(u, 0, 1))
    return {
        "production": z[:, 0] * C.ERROR_SD["production"],
        "ethanol_grind": z[:, 1] * C.ERROR_SD["ethanol_grind"],
        "feed_residual": z[:, 2] * C.ERROR_SD["feed_residual"],
        "export_pct": q,
    }


if __name__ == "__main__":
    run()
