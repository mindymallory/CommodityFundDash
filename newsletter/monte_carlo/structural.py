"""Monte Carlo v2: structural (identity-based) partial equilibrium for U.S. corn.

Economics (project design memo section 4): within one marketing year supply is
predetermined, so price clears the identity

    sum_i Q_i(P*) + Q_stocks(P*) = S1

with constant-elasticity demand curves

    Q_i(P) = (Q_i0 + dD_i) * (P / P0)^eps_i

Q_i0 are the perturbed WASDE #675 base quantities (v1's error machinery),
dD_i an optional additive demand shock, eps_i drawn per draw from triangular
literature priors, P0 = $4.80. Ending stocks is the stock-demand curve's
quantity at P* — it is *demand for carry*, not a residual dump — so the
identity supply = use + ending holds by construction and the memo's price
flexibility form dP/P ~= (dS/S) / sum(share_i * eps_i) holds in the limit.

This fixes v1's left-tail pathology: in v1, use was fixed and the whole shock
went into ending stocks, which the fitted inverse price curve then priced
explosively as stocks-to-use -> 0. Here demand rationing is structural, so
extreme draws behave economically (price rises, use falls, stocks stay
nonnegative).
"""
import math

import numpy as np

from . import config as C
from . import structural_config as SC
from . import simulate

CATS = SC.CATEGORIES
N_CAT = len(CATS)


# ---------------------------------------------------------------- inputs ---
def load_inputs():
    """Reuse v1's input loader: finals, error correlation, plus the
    demand-curve-consistent export shifter inference (export_errors module).
    Nothing invented; same validated workbook layer."""
    from monte_carlo import export_errors as ee
    finals = simulate.load_finals()
    corr = simulate.error_correlation(finals)
    eh = ee.load_history()
    live = ee.current_week_commitments()
    if SC.CURRENT_WEEK not in live:
        raise KeyError(
            f"No live commitments for week {SC.CURRENT_WEEK}; "
            "update PACE_EXPORT before running.")
    export_shift = dict(hist=eh, week=SC.CURRENT_WEEK,
                        C_w=live[SC.CURRENT_WEEK], P_cur=SC.P0,
                        eps=SC.EXPORT_EPS_WORK, purge=SC.EXPORT_PACE_PURGE)
    return {"finals": finals, "corr": corr, "export_shift": export_shift}


def draw_elasticities(n, seed):
    """Triangular draws per category, independent across categories.
    Returns (n, 5) array in CATS order; values are negative."""
    rng = np.random.default_rng(seed)
    cols = []
    for cat in CATS:
        lo, mode, hi = SC.ELASTICITY_PRIORS[cat]
        cols.append(rng.triangular(lo, mode, hi, size=n))
    return np.column_stack(cols)


def draw_base_quantities(n, err_seed, inputs):
    """Perturb the WASDE #675 base: correlated normals for
    production/ethanol/feed (leading 3x3 block of v1's first-difference
    correlation matrix), and the demand-curve-consistent export shifter
    from monte_carlo.export_errors (purged of the price->booking-pace
    channel; week-conditioned bands that tighten through the season).

    Each line's error shifts that line's schedule at P0: the production error
    shifts supply; use-line errors shift their demand curves. The stock-demand
    baseline is fixed at the WASDE ending (1,567 M bu) — it is the market's
    demand for carry at $4.80, not a plug that absorbs the other errors
    (that would pin every base-scenario price at exactly $4.80).
    """
    from monte_carlo import export_errors as ee
    errors = _draw_errors_no_export(n, err_seed, inputs["corr"])
    es = inputs["export_shift"]
    Ahat = ee.draw_export_shifters(n, es["hist"], es["week"], es["C_w"],
                                   es["P_cur"], es["eps"],
                                   seed=err_seed + SC.EXPORT_ERR_SEED_OFFSET,
                                   purge=es["purge"])
    # multiplicative export-base factor, drop-in for (1 + export_pct):
    # Q_exp0 = Ahat * P0^eps_work, so at P0 the curve passes through the
    # inferred demand shifter. eps_work is the triangular mode, so this is
    # median-consistent when the per-draw elasticity differs.
    m_exp = Ahat * SC.P0 ** es["eps"] / C.BASE["exports"]
    b = C.BASE
    prod = b["production"] + errors["production"]
    exp = b["exports"] * m_exp
    eth = b["ethanol_grind"] + errors["ethanol_grind"]
    feed = b["feed_residual"] + errors["feed_residual"]
    fsi = np.full(n, b["fsi_non_ethanol"])
    S0 = b["beg_stocks"] + prod + b["imports"]
    T0 = exp + eth + feed + fsi
    E0 = S0 - T0  # perturbed implied ending (diagnostic only)
    Qs0 = np.full(n, C.BASE_ENDING)  # WASDE #675 ending stocks: fixed anchor
    errors["export_pct"] = m_exp - 1.0  # keep diagnostics key working
    return {"S0": S0, "exp": exp, "eth": eth, "feed": feed, "fsi": fsi,
            "Qs0": Qs0, "E0_implied": E0, "errors": errors}


def _draw_errors_no_export(n, seed, corr):
    """Correlated normals for production/ethanol/feed only (3x3 leading
    block of the v1 first-difference correlation matrix; LINES order is
    [production, ethanol_grind, feed_residual, exports], so exports is
    the dropped 4th row/col). The export draw is now the independent
    purged Ahat bootstrap -- see INTEGRATION_SPEC.md for why the old
    correlation is not carried over."""
    import numpy as np
    from monte_carlo import config as C
    rng = np.random.default_rng(seed)
    L = np.linalg.cholesky(np.asarray(corr)[:3, :3])
    z = rng.standard_normal((n, 3)) @ L.T
    return {
        "production": z[:, 0] * C.ERROR_SD["production"],
        "ethanol_grind": z[:, 1] * C.ERROR_SD["ethanol_grind"],
        "feed_residual": z[:, 2] * C.ERROR_SD["feed_residual"],
    }


# ---------------------------------------------------------------- solver ---
def _excess(z, Q0, elas, S1):
    """Excess demand at log-relative-price z = ln(P/P0). Q0: (n,5)."""
    return (Q0 * np.exp(elas * z[:, None])).sum(axis=1) - S1


def clear_market(Q0, elas, S1, p0=SC.P0):
    """Solve sum_i Q0_i * (P/P0)^eps_i = S1 by bisection on z = ln(P/P0).

    Vectorized over draws. Demand is strictly decreasing in price
    (all eps < 0), so the root is unique. Returns (P, Q1, max_resid_frac).
    """
    n = Q0.shape[0]
    lo = np.full(n, math.log(SC.PRICE_FLOOR / p0))
    hi = np.full(n, math.log(SC.PRICE_CAP / p0))
    f_lo, f_hi = _excess(lo, Q0, elas, S1), _excess(hi, Q0, elas, S1)
    # Adaptive bracket expansion (should essentially never trigger: demand at
    # $0.50 is many multiples of any plausible supply, and ~0 at $50).
    for _ in range(8):
        bad = ~((f_lo > 0) & (f_hi < 0))
        if not bad.any():
            break
        lo[bad] -= 1.0
        hi[bad] += 1.0
        f_lo, f_hi = _excess(lo, Q0, elas, S1), _excess(hi, Q0, elas, S1)
    if ((f_lo <= 0) | (f_hi >= 0)).any():
        raise RuntimeError("bisection bracket failed to sign-change")
    for _ in range(SC.BISECTION_ITERS):
        mid = 0.5 * (lo + hi)
        f = _excess(mid, Q0, elas, S1)
        lo = np.where(f > 0, mid, lo)
        hi = np.where(f <= 0, mid, hi)
    z = 0.5 * (lo + hi)
    P = p0 * np.exp(z)
    Q1 = Q0 * np.exp(elas * z[:, None])
    resid = np.abs(_excess(z, Q0, elas, S1)) / S1
    return P, Q1, float(resid.max())


# ------------------------------------------------------------- simulation ---
def run_scenario(name, n=None, err_seed=None, elas_seed=None, inputs=None,
                 verbose=True):
    """One full Monte Carlo scenario. Returns dict of draws + summary."""
    n = n or SC.N_DRAWS
    spec = SC.SCENARIOS[name]
    err_seed = SC.SEED if err_seed is None else err_seed
    elas_seed = SC.ELAS_SEED if elas_seed is None else elas_seed
    inputs = inputs or load_inputs()

    bq = draw_base_quantities(n, err_seed, inputs)
    elas = draw_elasticities(n, elas_seed)

    dD = np.zeros(N_CAT)
    for cat, val in spec["dD"].items():
        dD[CATS.index(cat)] = val
    Q0 = np.column_stack([bq["exp"], bq["eth"], bq["feed"], bq["fsi"],
                          bq["Qs0"]]) + dD[None, :]
    S1 = bq["S0"] + spec["dS"]

    P, Q1, max_resid = clear_market(Q0, elas, S1)

    use = Q1[:, :4].sum(axis=1)
    ending = Q1[:, 4]
    # Identity: supply == use + ending, by construction. Assert it.
    ident_resid = np.abs(S1 - (use + ending))
    assert (ident_resid < 1e-3).all(), "identity violated"
    assert max_resid < 1e-6, "solver did not converge"

    draws = {
        "price": P,
        "ending": ending,
        "stocks_use": ending / use,
        "supply": S1,
        "total_use": use,
        "q1": Q1,            # (n,5) per-category quantities at P*
        "elas": elas,        # (n,5) drawn elasticities
        "q0": Q0,            # (n,5) baseline quantities (shock-shifted)
        "max_solver_resid_frac": max_resid,
        "max_identity_resid_mbu": float(ident_resid.max()),
        # v1-compatible keys for simulate.summarize
        "production": bq["S0"] - C.BASE["beg_stocks"] - C.BASE["imports"],
        "exports": Q1[:, 0], "ethanol": Q1[:, 1], "feed": Q1[:, 2],
        "out_of_bounds": np.zeros(n, dtype=bool),
    }
    summary = simulate.summarize(draws)
    summary["scenario"] = name
    summary["dS"] = spec["dS"]
    summary["dD"] = spec["dD"]
    if verbose:
        print(f"[{name}] dS={spec['dS']:+.1f} dD={spec['dD'] or 'none'}")
        print("  P50 price=$%.2f  P50 ending=%.0f  P(s/u<10%%)=%.1f%%" % (
            summary["price"]["p50"], summary["ending"]["p50"],
            summary["p_su_lt_10"] * 100))
        print("  solver: 100%% converged (%d bisection iters/draw), "
              "max resid %.2e of supply" % (SC.BISECTION_ITERS, max_resid))
        print("  identity: max |S1-(use+ending)| = %.2e M bu"
              % float(ident_resid.max()))
    return {"draws": draws, "summary": summary, "inputs": inputs}


def deterministic(elas_values, dS=0.0, dD=None):
    """Single no-uncertainty run at given elasticities (dict cat->eps).

    Used for the demand-rationing waterfall and the flexibility cross-check.
    """
    b = C.BASE
    S0 = b["beg_stocks"] + b["production"] + b["imports"]
    T0 = b["exports"] + b["ethanol_grind"] + b["feed_residual"] + b["fsi_non_ethanol"]
    E0 = S0 - T0
    q0 = np.array([[b["exports"], b["ethanol_grind"], b["feed_residual"],
                    b["fsi_non_ethanol"], E0]])
    dDv = np.zeros(N_CAT)
    for cat, val in (dD or {}).items():
        dDv[CATS.index(cat)] = val
    elas = np.array([[elas_values[c] for c in CATS]])
    S1 = S0 + dS
    P, Q1, _ = clear_market(q0 + dDv[None, :], elas, np.array([S1]))
    return {"price": float(P[0]), "q1": Q1[0], "ending": float(Q1[0, 4]),
            "stocks_use": float(Q1[0, 4] / Q1[0, :4].sum()),
            "supply": float(S1)}


def median_elasticities():
    """Modes of the (symmetric) triangular priors == medians."""
    return {c: v[1] for c, v in SC.ELASTICITY_PRIORS.items()}


# -------------------------------------------------------------- validation ---
def flexibility_crosscheck():
    """At small uniform elasticity, the solver must reproduce the memo's
    price-flexibility form dP/P ~= (dS/S) / sum(share_i * eps_i).

    Exact limit (all eps equal): S0 * e^{eps*z} = S1  =>  z = ln(S1/S0)/eps.
    Test: -1 bu/ac supply shock (-88.5 M bu), eps = -0.05 everywhere,
    no other uncertainty.
    """
    eps = -0.05
    dS = -1.0 * C.BASE["harvested_ac_m"]  # -88.5 M bu
    elas = {c: eps for c in CATS}
    det = deterministic(elas, dS=dS)
    b = C.BASE
    S0 = b["beg_stocks"] + b["production"] + b["imports"]
    z_exact = math.log((S0 + dS) / S0) / eps
    z_solver = math.log(det["price"] / SC.P0)
    memo_approx = (dS / S0) / eps          # first-order form from the memo
    dp_solver = det["price"] / SC.P0 - 1.0
    return {
        "dS": dS, "eps": eps,
        "z_solver": z_solver, "z_exact": z_exact,
        "z_agreement": abs(z_solver - z_exact),
        "memo_dP_over_P": memo_approx, "solver_dP_over_P": dp_solver,
        "memo_vs_solver_pct": abs(memo_approx - dp_solver) / abs(dp_solver) * 100,
        "pass": abs(z_solver - z_exact) < 1e-9,
    }
