"""Corrected export demand-error module — measure the error against the
model's OWN demand curve, not a cross-era average pace.

Mindy's critique of the old scheme (monte_carlo/simulate.py::
export_pct_residuals): the old week-w residual

    r_y = [C_w(y) / sbar_w] / C_53(y) - 1

compares this year's bookings against the historical-average booking pace
sbar_w.  That benchmark is contaminated: booking pace responds to price
(panic front-loading in high-price years, lethargy in low-price years), so
r_y embeds movement ALONG the demand curve.  The old code then applied r_y
as a demand-curve SHIFT and the structural model applied the price
elasticity a second time — double counting.  Empirically, regressing r_y on
log season-average price gives t = +3.7, p = 0.0025, R^2 = 0.52: over half
the "error" variance was price.

The fix, in three steps:

1. Estimate the export demand curve X = A * P^eps properly.  Price and
   exports are jointly determined, so OLS of log X on log P is biased
   (demand shocks push both up).  Instrument log price with supply shocks
   (yield deviation from trend x harvested acres).  With n = 15 the
   instrument is honest about its strength (first-stage F reported); the
   working elasticity stays the literature mode (-1.0), validated -- not
   replaced -- by the IV point estimate.

2. Recover genuine demand shifters Ahat_t = X_t / P_t^eps.  These are purged
   of along-curve price movement by construction.

3. Week-w forecasting rule purged of the pace-price channel.  Booking pace
   itself responds to price, s_{y,w} = sbar_w * (P_y/Pbar)^gamma_w, so the
   inference is

       Ahat_hat = C_w / [sbar_w * (P_cur/Pbar)^gamma_w] / P_cur^eps,

   and the error distribution is the empirical distribution of the
   purged log inference errors

       e*_{y,w} = log[ C_w(y) / (sbar_w * phi_w(P_y)) ] - log(X_y),

   across historical years.  sd(e*) falls naturally with w (bands tighten
   as the season fills in); at w = 53 only the commitment/export wedge
   remains.

Nothing here edits structural.py / simulate.py / world.py -- see
INTEGRATION_SPEC.md for the exact swap-in diffs.
"""

import csv
import os

import numpy as np
import openpyxl
from scipy import stats

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKBOOK = os.path.join(BASE, "US_Corn_History_and_Pace_v1.xlsx")
STAGED_WEEKLY = os.path.join(BASE, "fas_corn_weekly_commitment_stage_2007-2026.csv")
SCURVE_WINDOWS = os.path.join(BASE, "fas_corn_scurve_windows.csv")
CHART_DIR = os.path.join(BASE, "mc_charts")

P0 = 4.80          # anchor price -- must match structural_config.SC.P0
EPS_WORK = -1.0    # working demand elasticity: literature mode (see below)
WEEKS_GRID = [2, 8, 16, 26, 40, 53]


# ------------------------------------------------------------ data -------
def load_history():
    """15 clean final years, MY 2010/11--2024/25.

    2025/26 is excluded as provisional: the marketing year ended 2026-08-31
    and the workbook row still carries the September WASDE projection /
    FAS week-53 proxy rather than a Census final.
    Returns dict of numpy arrays + staged weekly commitments.
    """
    wb = openpyxl.load_workbook(WORKBOOK, data_only=True)
    ws = wb["HIST_BALANCE"]
    # cols: A=MY, C=harvested ac, D=yield, L=exports, P=season-avg price
    recs = []
    for r in range(4, 19):  # rows 4..18 = 2010/11..2024/25
        recs.append(dict(
            my=ws.cell(r, 1).value,
            myear=2011 + (r - 4),          # FAS marketYear: 2011 = MY 2010/11
            harv=float(ws.cell(r, 3).value),
            yld=float(ws.cell(r, 4).value),
            X=float(ws.cell(r, 12).value),  # final exports, M bu
            P=float(ws.cell(r, 16).value),  # season-avg price, $/bu
        ))
    staged = {}
    with open(STAGED_WEEKLY) as f:
        for row in csv.DictReader(f):
            staged.setdefault(int(row["market_year"]), {})[
                int(row["week_of_marketing_year"])] = float(
                    row["commitment_mil_bu"])
    curve = {}
    with open(SCURVE_WINDOWS) as f:
        for row in csv.DictReader(f):
            curve[int(row["week_of_marketing_year"])] = (
                float(row["avg20_pct"]) / 100.0)
    h = {k: np.array([r[k] for r in recs]) for k in
         ("myear", "harv", "yld", "X", "P")}
    h["my"] = [r["my"] for r in recs]
    h["staged"] = staged
    h["curve"] = curve
    return h


def current_week_commitments():
    """Live 2026/27 commitments (M bu) from the workbook PACE_EXPORT tab.

    Computed from C (outstanding, MMT) + D (accumulated, MMT) x 39.368 --
    the G column is a formula with no cached value in an openpyxl-written
    file, so data_only reads return None.
    """
    wb = openpyxl.load_workbook(WORKBOOK, data_only=True)
    ws = wb["PACE_EXPORT"]
    out = {}
    for r in range(5, 60):
        wk = ws.cell(r, 2).value
        c, d = ws.cell(r, 3).value, ws.cell(r, 4).value
        if wk and c is not None and d is not None:
            out[int(wk)] = (float(c) + float(d)) * 39.368
    return out


# ------------------------------------------------- old (naive) method ----
def old_residuals(h, week):
    """Naive week-w residuals: implied-final vs final commitments.

    r_y = [C_w(y)/sbar_w] / C_53(y) - 1.  Kept only to demonstrate the
    contamination; do not use for simulation.
    """
    s = h["curve"][week]
    return np.array([(h["staged"][y][week] / s) / h["staged"][y][53] - 1.0
                     for y in h["myear"]])


def contamination_demo(h, week=2):
    """Regress the naive residuals on log price.

    A significant coefficient proves price was baked into the "error":
    the benchmark was reading along-curve movement as demand shifts.
    """
    r = old_residuals(h, week)
    res = stats.linregress(np.log(h["P"]), r)
    return dict(week=week, coef=res.slope, se=res.stderr,
                t=res.slope / res.stderr, p=res.pvalue, r2=res.rvalue ** 2,
                n=len(r), resid=r)


# ------------------------------------------------- demand estimation -----
def supply_shocks(h):
    """Exogenous supply instrument: (yield - trend) x harvested acres, M bu."""
    t = np.arange(len(h["yld"]))
    res = stats.linregress(t, h["yld"])
    return (h["yld"] - (res.intercept + res.slope * t)) * h["harv"], res.slope


def estimate_elasticity(h):
    """OLS vs IV estimate of the export demand elasticity.

    Demand: log X = a + eps * log P + u.  OLS is biased toward zero because
    demand shocks move P and X together.  IV instruments log P with the
    yield-deviation supply shock (exogenous weather variation; affects
    exports only through price).
    """
    lx, lp = np.log(h["X"]), np.log(h["P"])
    shock, trend = supply_shocks(h)
    n = len(lx)

    ols = stats.linregress(lp, lx)

    # first stage: lp on shock
    fs = stats.linregress(shock, lp)
    F = (fs.slope / fs.stderr) ** 2

    # 2SLS, manual
    Z = np.column_stack([np.ones(n), shock])
    Xr = np.column_stack([np.ones(n), lp])
    Pz = Z @ np.linalg.inv(Z.T @ Z) @ Z.T
    Xh = Pz @ Xr
    beta = np.linalg.inv(Xh.T @ Xh) @ Xh.T @ lx
    u = lx - Xr @ beta
    s2 = u @ u / (n - 2)
    se_iv = np.sqrt(np.diag(s2 * np.linalg.inv(Xh.T @ Xh)))

    return dict(
        n=n, yield_trend=trend,
        ols_eps=ols.slope, ols_se=ols.stderr,
        first_stage_t=fs.slope / fs.stderr, first_stage_F=F,
        iv_eps=beta[1], iv_se=se_iv[1], iv_intercept=beta[0],
        # working choice: literature mode; IV is the cross-check
        eps_work=EPS_WORK,
    )


def demand_shifters(h, eps=EPS_WORK):
    """Genuine demand shifters: Ahat_t = X_t / P_t^eps.

    Along-curve price movement is divided out, so cross-year variation in
    Ahat is demand-curve shifting, not price response.
    """
    Ahat = h["X"] / h["P"] ** eps
    return Ahat


# ------------------------------------------- pace-price purge ------------
def estimate_pace_price(h, week):
    """Does week-w booking pace respond to price?  log s_{y,w} on log P_y.

    s_{y,w} = C_w(y)/C_53(y).  Returns gamma_w (pace elasticity wrt price)
    and its significance.  In high-price years early bookings run hot
    (panic front-loading); the purge removes this channel from the
    inference error.
    """
    s = np.array([h["staged"][y][week] / h["staged"][y][53]
                  for y in h["myear"]])
    with np.errstate(invalid="ignore", divide="ignore"):
        res = stats.linregress(np.log(h["P"]), np.log(s))
    t = res.slope / res.stderr if res.stderr else 0.0
    return dict(week=week, gamma=res.slope, se=res.stderr, t=t,
                p=res.pvalue, mean_logP=np.log(h["P"]).mean())


def _phi(h, week, P, gamma_fit=None):
    """Pace-price adjustment factor phi_w(P) = (P/Pbar)^gamma_w."""
    gamma_fit = gamma_fit or estimate_pace_price(h, week)
    return (P / np.exp(gamma_fit["mean_logP"])) ** gamma_fit["gamma"]


# ------------------------------------------- week-w inference ------------
def week_forecast(h, week, C_w, P_cur, eps=EPS_WORK, purge=True):
    """Point inference of the demand shifter from week-w commitments.

    Ahat_hat = C_w / [sbar_w * phi_w(P_cur)] / P_cur^eps.
    With purge=False this collapses to the spec's literal rule
    (average pace, no price adjustment).
    """
    sbar = h["curve"][week]
    phi = _phi(h, week, P_cur) if purge else 1.0
    return C_w / (sbar * phi) / P_cur ** eps


def inference_errors(h, week, eps=EPS_WORK, purge=True):
    """Historical purged log inference errors e*_{y,w}.

    e* = log[ C_w(y)/(sbar_w * phi_w(P_y)) ] - log(X_y): how wrong the
    week-w Ahat inference was, with the price-driven pace channel removed.
    Price cancels algebraically AND economically (via the purge), so these
    are genuine demand-shifter forecast errors.
    """
    sbar = h["curve"][week]
    gf = estimate_pace_price(h, week) if purge else None
    errs = []
    for y, Xy, Py in zip(h["myear"], h["X"], h["P"]):
        phi = _phi(h, week, Py, gf) if purge else 1.0
        errs.append(np.log(h["staged"][y][week] / (sbar * phi)) - np.log(Xy))
    return np.array(errs)


def error_sd_by_week(h, eps=EPS_WORK, purge=True, weeks=WEEKS_GRID):
    """sd of the purged inference error at each week -- the tightening bands."""
    return {w: float(np.std(inference_errors(h, w, eps, purge), ddof=1))
            for w in weeks}


def fit_decay(h, eps=EPS_WORK, purge=True, weeks=WEEKS_GRID):
    """Fit sd(w) = c + a*exp(-b*w): bands collapse as the season fills in."""
    from scipy.optimize import curve_fit
    sds = error_sd_by_week(h, eps, purge, weeks)
    w = np.array(sorted(sds), dtype=float)
    s = np.array([sds[k] for k in sorted(sds)])
    f = lambda x, c, a, b: c + a * np.exp(-b * x)
    (c, a, b), _ = curve_fit(f, w, s, p0=(s[-1], s[0] - s[-1], 0.1),
                             bounds=([0.0, 0.0, 0.0],
                                     [0.2, 1.0, 1.0]),
                             maxfev=10000)
    return dict(weeks=w, sds=s, c=c, a=a, b=b,
                fitted=c + a * np.exp(-b * w))


# ------------------------------------------------- simulation draws ------
def draw_export_shifters(n, h, week, C_w, P_cur, eps=EPS_WORK, seed=7,
                         purge=True):
    """Bootstrap draws of the demand shifter Ahat for the current year.

    Ahat_draw = Ahat_hat_current * exp(e*),  e* ~ empirical purged
    week-w inference errors (NOT recentered: the historical bias, if any,
    is reported and preserved -- same convention as the old code).
    Returns Ahat_draw and the multiplicative export-base factor
    m_draw = Ahat_draw * P0^eps_draw / base_exports for the structural model.
    """
    rng = np.random.default_rng(seed)
    Ahat_hat = week_forecast(h, week, C_w, P_cur, eps, purge)
    e = inference_errors(h, week, eps, purge)
    return Ahat_hat * np.exp(rng.choice(e, size=n, replace=True))


def unconditional_shifter_dist(h, eps=EPS_WORK):
    """Spec-literal alternative: empirical distribution of log Ahat itself
    (normalized), ignoring week-w conditioning.  Reported for comparison;
    the week-conditioned e* distribution is the recommended primary."""
    Ahat = demand_shifters(h, eps)
    l = np.log(Ahat / np.exp(np.log(Ahat).mean()))
    return l


# ------------------------------------------------- validation demos ------
def no_double_count_demo(h, eps=EPS_WORK):
    """A pure price spike with NO demand shift must leave Ahat ~= 1.

    Synthetic data-generating process faithful to the model: take each
    historical year's Ahat_y; spike price 50% (P' = 1.5*P_y); true exports
    move ALONG the curve to X' = Ahat_y * P'^eps; week-2 bookings follow
    the estimated price-adjusted pace, C_2 = sbar_2 * phi_2(P') * X'.
    The purged inference must recover Ahat'/Ahat_y = 1 exactly --
    no phantom demand shift.  The old method, blind to both channels,
    misreads the episode as a demand shock.
    """
    sbar = h["curve"][2]
    Ahat = demand_shifters(h, eps)
    new_ratio, old_r = [], []
    for Ay, Py in zip(Ahat, h["P"]):
        Pp = 1.5 * Py
        Xp = Ay * Pp ** eps
        C2 = sbar * _phi(h, 2, Pp) * Xp   # bookings follow price-adjusted pace
        Ahat_hat = week_forecast(h, 2, C2, Pp, eps, purge=True)
        new_ratio.append(Ahat_hat / Ay)
        Xy = Ay * Py ** eps
        old_r.append((C2 / sbar) / Xy - 1.0)
    return dict(new_ratio=np.array(new_ratio), old_r=np.array(old_r),
                spike=1.5)


def worst_contaminated_year(h, week=2, eps=EPS_WORK):
    """The historical year where old and new methods disagree most."""
    r = old_residuals(h, week)
    e = inference_errors(h, week, eps, purge=True)
    gap = np.abs(r - e)
    i = int(np.argmax(gap))
    return dict(my=h["my"][i], P=h["P"][i], X=h["X"][i],
                old_r=r[i], new_e=e[i])


# ------------------------------------------------- charts ----------------
def _save(fig, name):
    import matplotlib
    matplotlib.use("Agg")
    path = os.path.join(CHART_DIR, name)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    return path


def chart_contamination(h, week=2):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = contamination_demo(h, week)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    lp = np.log(h["P"])
    ax.scatter(h["P"], d["resid"], s=45, alpha=0.8)
    for x, y, m in zip(h["P"], d["resid"], h["my"]):
        ax.annotate(m, (x, y), fontsize=7, xytext=(3, 3),
                    textcoords="offset points")
    xs = np.linspace(lp.min(), lp.max(), 50)
    ax.plot(np.exp(xs), d["coef"] * xs + (
        d["resid"].mean() - d["coef"] * lp.mean()), "r--",
        label=f"fit: t={d['t']:+.2f}, p={d['p']:.4f}, R²={d['r2']:.2f}")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Season-average price ($/bu)")
    ax.set_ylabel(f"Naive week-{week} residual (implied vs final)")
    ax.set_title("The contamination: the old 'error' was half price signal")
    ax.legend(fontsize=8)
    return _save(fig, "mc_export_errors_contamination.png")


def chart_decay(h, eps=EPS_WORK):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fit = fit_decay(h, eps)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(fit["weeks"], fit["sds"], s=50, label="empirical sd(e*)",
               zorder=3)
    wf = np.linspace(2, 53, 200)
    ax.plot(wf, fit["c"] + fit["a"] * np.exp(-fit["b"] * wf), "r--",
            label=f"fit: {fit['c']:.3f}+{fit['a']:.3f}·exp(-{fit['b']:.3f}·w)")
    for w, s in zip(fit["weeks"], fit["sds"]):
        ax.annotate(f"{s:.1%}", (w, s), fontsize=8, xytext=(4, 4),
                    textcoords="offset points")
    ax.set_xlabel("Marketing-year week")
    ax.set_ylabel("sd of purged inference error")
    ax.set_title("Bands tighten as the season fills in")
    ax.legend(fontsize=8)
    return _save(fig, "mc_export_errors_decay.png")


def chart_iv(h):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    est = estimate_elasticity(h)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    lp, lx = np.log(h["P"]), np.log(h["X"])
    ax.scatter(h["P"], h["X"], s=45, alpha=0.8)
    for x, y, m in zip(h["P"], h["X"], h["my"]):
        ax.annotate(m, (x, y), fontsize=7, xytext=(3, 3),
                    textcoords="offset points")
    Ps = np.linspace(h["P"].min() * 0.95, h["P"].max() * 1.05, 50)
    ax.plot(Ps, np.exp(est["ols_eps"] * np.log(Ps) + (
        lx.mean() - est["ols_eps"] * lp.mean())), "g--",
        label=f"OLS eps={est['ols_eps']:+.2f} (biased toward 0)")
    ax.plot(Ps, np.exp(est["iv_eps"] * np.log(Ps) + est["iv_intercept"]),
            "r-", label=f"IV eps={est['iv_eps']:+.2f}±{est['iv_se']:.2f}")
    ax.set_xlabel("Season-average price ($/bu)")
    ax.set_ylabel("Final exports (M bu)")
    ax.set_title("Export demand: OLS vs supply-shock IV")
    ax.legend(fontsize=8)
    return _save(fig, "mc_export_errors_iv.png")


# ------------------------------------------------- main ------------------
def main():
    h = load_history()
    print(f"history: n={len(h['X'])} clean final years "
          f"({h['my'][0]}..{h['my'][-1]}); 2025/26 excluded as provisional")

    # 1. contamination proof
    d = contamination_demo(h, 2)
    print("\n[1] CONTAMINATION: naive week-2 residual ~ log price")
    print(f"    coef={d['coef']:+.3f} se={d['se']:.3f} t={d['t']:+.2f} "
          f"p={d['p']:.4f} R2={d['r2']:.2f}")
    print("    -> over half the old 'error' variance was price. "
          "Benchmark was reading along-curve movement as demand shifts.")

    # 2. elasticity: OLS vs IV
    est = estimate_elasticity(h)
    print("\n[2] DEMAND ELASTICITY (log X ~ log P)")
    print(f"    OLS eps = {est['ols_eps']:+.3f} (se {est['ols_se']:.3f}) "
          "-- biased toward zero by demand shocks")
    print(f"    first stage (supply shock -> log P): t={est['first_stage_t']:+.2f}, "
          f"F={est['first_stage_F']:.1f} {'(strong: F>10)' if est['first_stage_F'] > 10 else '(WEAK)'}")
    print(f"    IV  eps = {est['iv_eps']:+.3f} (se {est['iv_se']:.3f})")
    print(f"    working eps = {est['eps_work']:+.1f} (literature mode); "
          "IV is the cross-check, not the replacement")

    # 3. pace-price purge at the grid weeks
    print("\n[3] PACE-PRICE PURGE: log pace_w ~ log P")
    for w in (2, 8, 16, 26):
        g = estimate_pace_price(h, w)
        print(f"    wk {w:2d}: gamma={g['gamma']:+.3f} t={g['t']:+.2f} "
              f"p={g['p']:.3f}")

    # 4. new vs old error scale
    e2 = inference_errors(h, 2)
    r_old = old_residuals(h, 2)
    l_uncond = unconditional_shifter_dist(h)
    print("\n[4] ERROR SCALE at week 2")
    print(f"    old naive resid:  sd={r_old.std(ddof=1):.3f} "
          f"mean={r_old.mean():+.3f} median={np.median(r_old):+.3f}")
    print(f"    new purged e*:    sd={e2.std(ddof=1):.3f} "
          f"mean={e2.mean():+.3f} median={np.median(e2):+.3f}")
    print(f"    (spec-literal unconditional log-Ahat sd: "
          f"{l_uncond.std(ddof=1):.3f} -- wider: ignores week-2 info)")
    iv_resid = np.log(h["X"]) - (est["iv_intercept"]
                                     + est["iv_eps"] * np.log(h["P"]))
    print(f"    IV demand-fit residuals: mean={iv_resid.mean():+.2e} "
          "(~zero by construction), "
          f"sd={iv_resid.std(ddof=1):.3f} in log points")

    # 5. worst contaminated year
    w = worst_contaminated_year(h)
    print("\n[5] WORST-CONTAMINATED YEAR")
    print(f"    {w['my']}: P=${w['P']:.2f}, X={w['X']:.0f} M bu | "
          f"old r={w['old_r']:+.1%}, new e*={w['new_e']:+.1%}")

    # 6. no-double-count demo
    nd = no_double_count_demo(h)
    print("\n[6] NO-DOUBLE-COUNT DEMO (synthetic +50% price spike, Ahat fixed)")
    print(f"    new method inferred Ahat'/Ahat: mean={nd['new_ratio'].mean():.4f} "
          f"(must be 1.000)")
    print(f"    old method invents a 'demand shock' from the pure price move: "
          f"mean={nd['old_r'].mean():+.1%}, range "
          f"{nd['old_r'].min():+.1%}..{nd['old_r'].max():+.1%} across years")

    # 7. time decay
    fit = fit_decay(h)
    print("\n[7] BANDS TIGHTEN BY WEEK: sd(e*)")
    for wk, s in zip(fit["weeks"], fit["sds"]):
        print(f"    wk {int(wk):2d}: {s:.1%}")
    print(f"    decay fit: sd(w) = {fit['c']:.3f} + {fit['a']:.3f} * "
          f"exp(-{fit['b']:.3f} w)")

    # 8. current-year point inference (week 2 live)
    live = current_week_commitments()
    C2 = live.get(2)
    Ahat_hat = week_forecast(h, 2, C2, P0)
    Ahat_hat_nopurge = week_forecast(h, 2, C2, P0, purge=False)
    X_at_P0 = Ahat_hat * P0 ** EPS_WORK
    print(f"\n[8] CURRENT YEAR (2026/27, week 2: C={C2:.1f} M bu, P_cur=${P0:.2f})")
    print(f"    Ahat_hat (purged) = {Ahat_hat:,.0f}; without purge = "
          f"{Ahat_hat_nopurge:,.0f}")
    print(f"    implied exports at $4.80 = {X_at_P0:,.0f} M bu "
          f"(WASDE 3,275)")

    p1 = chart_contamination(h)
    p2 = chart_iv(h)
    p3 = chart_decay(h)
    print("\ncharts:", p1, "\n       ", p2, "\n       ", p3)


if __name__ == "__main__":
    main()
