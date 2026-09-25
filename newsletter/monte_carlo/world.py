"""Monte Carlo v3-world: global extension of the structural U.S. corn model.

Economics. The v2 U.S. structural model is kept intact (4 domestic demand
curves + stock-demand curve, constant elasticity, P0=$4.80). v2's fixed
export demand curve is REPLACED by a residual export demand curve from the
world module:

    X_US(P) = M_ROW(P) + M_CH(P) - XS_BR(P) - XS_AR(P) - XS_UP(P) - X_OTHER

- Competitor export supply: XS_i(P) = max(0, beg_i + prod_draw_i + imp_i
  - dom_i(P) - floor_i - kval_i), with dom_i(P) = dom_i0*(P/P0)^eps_dom,
  eps_dom ~ triangular(-0.3,-0.2,-0.1). floor_i = 0.05*dom_i0 is pipeline
  stocks; kval_i = end_i0 - floor_i is the competitor's demand for carry,
  held FIXED across prices (a documented v3-world modeling choice). Why the
  kval term exists: without it the formula's XS_i(P0) would exceed observed
  exports by (end_i0 - floor_i) — Brazil carries 417 M bu, not the 201 M bu
  pipeline floor — and the residual curve could not be calibrated to pass
  through the WASDE point (P0, 3275). With kval, XS_i(P0) = observed
  exports exactly and XS_i slopes up in P purely through domestic demand
  rationing (as P rises, dom_i falls, so more is left for export).
- prod_draw_i: competitor production competing with OUR marketing year
  (Mindy's timing rule, 2026-09-18: no H1/H2 split; for US MY Sep-Aug, use the
  harvests landing in our window whatever local MY USDA files them under).
  For 2026/27: BR = local MY 2027/28 (first crop Feb-Apr 2027 + safrinha
  Jun-Aug 2027); AR = local MY 2027/28 (Mar-Jun 2027); UP = local MY 2026/27
  (Sep-Nov 2026, being harvested now). USDA had not published BR/AR local
  2027/28 in the Sep-2026 vintage, so anchors are the latest observed
  productions as no-change expectation proxies. Baseline sds are FORWARD
  uncertainties now: BR 385 / AR 260 M bu (detrended historical volatility;
  the competing crops are unplanted in Sep 2026), UP 80 (nearly final).
  BR-AR corr 0.5, UP independent, truncated at +/-3 sd. The +/-500 M bu
  Brazil scenarios (~1.3 sd) are the named forward-safrinha scenarios.
- World import demand (China broken out): M_ROW(P) = 7799.1*(P/P0)^eps_ROW,
  eps_ROW ~ triangular(-0.6,-0.4,-0.2); M_CH(P) = 196.8*(P/P0)^eps_CH,
  eps_CH ~ triangular(-0.9,-0.6,-0.3); per-draw multiplicative anchor noise
  4% / 15%. (v1-world choices, documented in world_config.py.)
- X_OTHER ~= 665.9 M bu (the brief's 666): calibration constant so
  X_US(P0) = 3275 exactly at median parameters. The 666-vs-941 gap to
  implied other-exporter exports (world exports 8270.6 - BR/AR/UP/US 7329.9
  = 940.7) is the PSD world imports/exports statistical discrepancy
  (8270.6 - 7995.9 = 274.7 M bu, MY/TY timing): X_OTHER is anchored to
  world IMPORTS (7995.9 - 4055 - 3275), while 941 is anchored to world
  exports. The residual curve clears against import demand, so the
  imports-anchored constant is the right one.

U.S. clearing: sum of the 4 domestic demand curves + X_US(P) = S_US, solved
by bisection on z = ln(P/P0). X_US is decreasing in P (import demands fall,
competitor export supplies rise), so the root is unique. The U.S.-side
baseline errors reuse v2's production/ethanol/feed draws (same seeds, so
base_global's U.S.-side draws ARE v2 base's draws); the export pace-residual
draw is DROPPED because exports are endogenous now.

China allocation (level): China's realized import demand M_CH(P*) is split
across US/BR/AR/UP by logit shares on landed cost
(FOB spread vs US Gulf + freight to China, per-draw spread noise sd 0.10).
Spread centers come from the weekly freight monitor (monte_carlo/freight.py)
when FREIGHT_LIVE is True, with per-leg fallback to the static priors when
a leg is stale, a proxy, or missing. As of the week ending 2026-09-16 ALL
four legs are on static fallback: BR's fixture-mean leg is 28 days old vs
the 14-day FREIGHT_MAX_VINTAGE_DAYS gate (GTR fixtures cover a 28-day
window plus reporting lag), US_PNW is a stale assumption, AR is a proxy
fixture, UP has no freight leg. The wiring is live; the first weekly
refresh that stages fresh fixtures will flip qualifying legs to live
automatically. This is a "pool" accounting assumption — it does not feed
back into clearing. The MARGINAL question (who supplies the +200 surge) is
answered structurally: compare equilibrium exports by origin vs base.

Seasonality: this is a full-year clearing model (Mindy: no H1/H2 split).
The h2_brazil_bumper / h2_brazil_drought presets use the same +/-500
mechanics as brazil_bumper / drought; under the timing rule the +/-500 IS
the forward safrinha uncertainty for our 2026/27 (Jun-Aug 2027 harvest,
USDA-filed under BR local MY 2027/28), and the h2 labels are kept only for
the newsletter's seasonal framing. No second mechanism is faked here.
"""
import math

import numpy as np

from . import config as C
from . import structural as S
from . import structural_config as SC
from . import world_config as WC
from . import simulate
from . import freight as _FREIGHT  # live landed-cost monitor

COMP_ORDER = WC.COMP_ORDER
US_CATS = WC.US_CATEGORIES
ORIGINS = WC.CHINA_ORIGINS


# ------------------------------------------------------- freight legs ---
def _live_legs():
    """Return ({'spreads': {o: $/bu}, 'freight': {o: $/bu},
    'week_ending': str, 'estimated_legs': [o]}, [fallback legs]).

    Falls back per-leg to FREIGHT_FALLBACK_* when the monitor is off, the
    staged CSV is missing, a leg value is None, or the leg vintage exceeds
    FREIGHT_MAX_VINTAGE_DAYS. Never raises: the model must stay runnable.

    Basis note: the monitor's fob_spread_bu is vs US_GULF for EVERY leg,
    including the US leg (e.g. the PNW FOB discount shows as a negative US
    spread). All legs therefore share one common basis and landed-cost
    differences are exact. (An older version forced the US spread to 0.0
    "by definition"; that was a no-op for the Gulf basis but would have
    biased a PNW basis by the full FOB discount, so it was removed.)

    Estimated legs: a leg flagged "estimated" in the staged CSV (currently
    only US_PNW_EST — see freight_pnw_proxy.md) is NEVER used silently. It
    is used only when FREIGHT_ALLOW_ESTIMATED_PNW is True, and it is
    recorded in freight_basis["estimated_legs"] (not in fallback_legs).
    """
    fb_spreads = dict(WC.FREIGHT_FALLBACK_SPREADS)
    fb_freight = dict(WC.FREIGHT_FALLBACK_FREIGHT)
    if not WC.FREIGHT_LIVE:
        return ({"spreads": fb_spreads, "freight": fb_freight,
                 "week_ending": None, "estimated_legs": []},
                list(ORIGINS))
    try:
        legs = _FREIGHT.get_landed_costs("CN")
    except (FileNotFoundError, OSError):
        print("freight monitor: no staged CSV; using static spreads")
        return ({"spreads": fb_spreads, "freight": fb_freight,
                 "week_ending": None, "estimated_legs": []},
                list(ORIGINS))
    us_key = "US_" + WC.FREIGHT_US_PORT  # "US_GULF" | "US_PNW" | "US_PNW_EST"
    fmap = {"US": us_key, "BR": "BR", "AR": "AR", "UP": "UP"}
    out_sp, out_fr, fell_back, estimated = {}, {}, [], []
    week_ending = None
    for o in ORIGINS:
        lg = legs.get(fmap[o], {})
        sp = lg.get("fob_spread_bu")
        fr = lg.get("freight_bu")
        week_ending = week_ending or lg.get("week_ending")
        is_est = "estimated" in (lg.get("flag") or "").lower()
        allow_est = is_est and WC.FREIGHT_ALLOW_ESTIMATED_PNW
        ok = (sp is not None and fr is not None
              and (not lg.get("stale", True) or allow_est)
              and (lg.get("vintage_days") or 10 ** 9)
              <= WC.FREIGHT_MAX_VINTAGE_DAYS)
        out_sp[o] = sp if ok else fb_spreads[o]
        out_fr[o] = fr if ok else fb_freight[o]
        if not ok:
            fell_back.append(o)
        elif is_est:
            estimated.append(o)
    if fell_back:
        print("freight monitor: static fallback for legs: %s"
              % ",".join(fell_back))
    if estimated:
        print("freight monitor: ESTIMATED legs (modeled, not quotes): %s"
              % ",".join(estimated))
    return ({"spreads": out_sp, "freight": out_fr,
             "week_ending": week_ending, "estimated_legs": estimated},
            fell_back)


# ------------------------------------------------------- world draws ---
def draw_world_quantities(n, seed, spec):
    """One draw-set for the world module. All randomness here is in the
    WORLD_SEED stream; the scenario only shifts anchors (dProd, dM_CH), so
    common random numbers hold across scenarios."""
    rng = np.random.default_rng(seed)

    # Competitor production draws: BR-AR correlated 0.5, UP independent,
    # truncated at +/-3 sd.
    z = rng.standard_normal((n, 3))
    zs = np.column_stack([
        z[:, 0],
        0.5 * z[:, 0] + math.sqrt(0.75) * z[:, 1],
        z[:, 2],
    ])
    zs = np.clip(zs, -3.0, 3.0)
    prod = {}
    for j, c in enumerate(COMP_ORDER):
        g = WC.COMPETITORS[c]
        prod[c] = (g["prod"] + spec["dProd"].get(c, 0.0)
                   + zs[:, j] * g["prod_sd"])

    # Elasticities (triangular priors, independent).
    elas_dom = np.column_stack(
        [rng.triangular(*WC.DOM_ELAS_PRIOR, size=n) for _ in COMP_ORDER])
    elas_row = rng.triangular(*WC.ROW_ELAS_PRIOR, size=n)
    elas_ch = rng.triangular(*WC.CH_ELAS_PRIOR, size=n)

    # Import-demand anchors with per-draw multiplicative noise.
    mrow0 = WC.M_ROW0 * (1.0 + rng.standard_normal(n) * WC.ROW_ANCHOR_SD)
    mch0 = ((WC.M_CH0 + spec["dM_CH"])
            * (1.0 + rng.standard_normal(n) * WC.CH_ANCHOR_SD))

    # China FOB spread draws per origin (sd 0.10), ORIGINS order.
    # Centered on the freight monitor's live week when available;
    # per-leg fallback to the static priors when a leg is missing/stale.
    _legs, _fb = _live_legs()
    spreads = np.column_stack([
        np.full(n, _legs["spreads"][o])
        + rng.standard_normal(n) * WC.CHINA_SPREAD_SD
        for o in ORIGINS])

    return {"prod": prod, "elas_dom": elas_dom, "elas_row": elas_row,
            "elas_ch": elas_ch, "mrow0": mrow0, "mch0": mch0,
            "spreads": spreads, "freight": _legs["freight"],
            "freight_basis": {"week_ending": _legs["week_ending"],
                              "fallback_legs": _fb,
                              "estimated_legs": _legs["estimated_legs"],
                              "us_port": WC.FREIGHT_US_PORT}}


# ------------------------------------------------- world demand curves ---
def competitor_xs(z, wq):
    """(n,3) competitor export supply at z = ln(P/P0), COMP_ORDER columns."""
    cols = []
    for j, c in enumerate(COMP_ORDER):
        g = WC.COMPETITORS[c]
        dom = g["dom"] * np.exp(wq["elas_dom"][:, j] * z)
        inside = (g["beg"] + wq["prod"][c] + g["imp"] - dom
                  - g["floor"] - g["kval"])
        cols.append(np.maximum(inside, 0.0))
    return np.column_stack(cols)


def us_export_residual(z, wq):
    """(n,) residual U.S. export demand at z = ln(P/P0). Decreasing in P."""
    m = (wq["mrow0"] * np.exp(wq["elas_row"] * z)
         + wq["mch0"] * np.exp(wq["elas_ch"] * z))
    return m - competitor_xs(z, wq).sum(axis=1) - WC.X_OTHER


def _excess_world(z, Q0, elas, S1, wq):
    """Excess U.S. demand at z: domestic curves + residual exports - supply."""
    return ((Q0 * np.exp(elas * z[:, None])).sum(axis=1)
            + us_export_residual(z, wq) - S1)


def clear_market_world(Q0, elas, S1, wq, p0=WC.P0):
    """Solve sum_k Q0_k*(P/P0)^eps_k + X_US(P) = S1 by bisection on z.

    Same pattern as structural.clear_market. Demand is strictly decreasing
    in price (all domestic eps < 0; X_US decreasing), so the root is unique.
    Returns (P, Q1_us, max_resid_frac)."""
    n = Q0.shape[0]
    lo = np.full(n, math.log(WC.PRICE_FLOOR / p0))
    hi = np.full(n, math.log(WC.PRICE_CAP / p0))
    f_lo = _excess_world(lo, Q0, elas, S1, wq)
    f_hi = _excess_world(hi, Q0, elas, S1, wq)
    for _ in range(8):
        bad = ~((f_lo > 0) & (f_hi < 0))
        if not bad.any():
            break
        lo[bad] -= 1.0
        hi[bad] += 1.0
        f_lo = _excess_world(lo, Q0, elas, S1, wq)
        f_hi = _excess_world(hi, Q0, elas, S1, wq)
    if ((f_lo <= 0) | (f_hi >= 0)).any():
        raise RuntimeError("bisection bracket failed to sign-change")
    for _ in range(WC.BISECTION_ITERS):
        mid = 0.5 * (lo + hi)
        f = _excess_world(mid, Q0, elas, S1, wq)
        lo = np.where(f > 0, mid, lo)
        hi = np.where(f <= 0, mid, hi)
    z = 0.5 * (lo + hi)
    P = p0 * np.exp(z)
    Q1 = Q0 * np.exp(elas * z[:, None])
    resid = np.abs(_excess_world(z, Q0, elas, S1, wq)) / S1
    return P, Q1, z, float(resid.max())


# ------------------------------------------------- China allocation ---
def calibrate_china_lambda():
    """Grid-search lambda in [1,4] (landed costs, no noise) for the
    lambda minimizing |US share - CHINA_US_SHARE_MID|.

    The midpoint is the trailing-3MY actual US share of China's corn imports
    (reset 2026-09-18; replaced the old 0.35 boom-era target — see
    world_config.py and CALIBRATION.md).

    Uses the freight monitor's live legs (with per-leg static fallback),
    so the calibration reflects the actual landed-cost ranking. As of the
    week ending 2026-09-16 the BR leg is LIVE on its 28-day fixture mean
    (35-day gate per Mindy's 2026-09-18 apples-to-apples decision) and the
    US leg runs on the ESTIMATED PNW leg US_PNW_EST (live GTR Table 1
    PNW->Japan $37.75/mt + estimated China premium -$0.96/mt; see
    freight_pnw_proxy.md — flagged "estimated" everywhere, never a quote);
    AR is a proxy-fallback and UP has no freight leg. With PNW as the US
    basis the US is competitive into China again (landed ~$6.93/bu), which
    matches the economics: the PNW is the shorter Asia route for corn (the
    Gulf is mainly a soybean-to-China artery). The allocation is level
    accounting only and does not affect price clearing.
    """
    legs, _fb = _live_legs()
    landed = np.array([legs["spreads"][o] + legs["freight"][o]
                       for o in ORIGINS])  # US, BR, AR, UP
    best = None
    for lam in np.arange(1.0, 4.0 + 1e-9, 0.01):
        u = np.exp(-lam * landed)
        shares = u / u.sum()
        d = abs(shares[0] - WC.CHINA_US_SHARE_MID)
        if best is None or d < best[0]:
            best = (d, lam, shares)
    _, lam, shares = best
    return {"lambda": float(lam),
            "shares": {o: float(s) for o, s in zip(ORIGINS, shares)},
            "landed_costs": {o: float(l) for o, l in zip(ORIGINS, landed)},
            "fallback_legs": _fb,
            "target_band": WC.CHINA_US_SHARE_TARGET,
            "target_met": bool(WC.CHINA_US_SHARE_TARGET[0] <= shares[0]
                               <= WC.CHINA_US_SHARE_TARGET[1])}


def china_shares(wq, lam):
    """(n,4) per-draw logit shares on landed cost, ORIGINS order."""
    landed = np.column_stack([
        wq["spreads"][:, j] + wq["freight"][o]
        for j, o in enumerate(ORIGINS)])
    u = np.exp(-lam * landed)
    return u / u.sum(axis=1, keepdims=True)


# ------------------------------------------------- deterministic curves ---
def residual_export_curve(P, dProd_BR=0.0, dM_CH=0.0):
    """Deterministic residual U.S. export demand at median parameters
    (elasticity modes, anchors, no noise). Used for chart (c) and the
    calibration check: residual_export_curve(P0) == 3275 by construction."""
    P = np.asarray(P, dtype=float)
    r = P / WC.P0
    m = (WC.M_ROW0 * r ** WC.ROW_ELAS_PRIOR[1]
         + (WC.M_CH0 + dM_CH) * r ** WC.CH_ELAS_PRIOR[1])
    xs = 0.0
    for c in COMP_ORDER:
        g = WC.COMPETITORS[c]
        prod = g["prod"] + (dProd_BR if c == "BR" else 0.0)
        dom = g["dom"] * r ** WC.DOM_ELAS_PRIOR[1]
        inside = prod + g["beg"] + g["imp"] - dom - g["floor"] - g["kval"]
        xs = xs + np.maximum(inside, 0.0)
    return m - xs - WC.X_OTHER


def v2_export_curve(P):
    """v2's constant-elasticity export demand at its mode elasticity (-1.0),
    for chart (c) comparison."""
    P = np.asarray(P, dtype=float)
    return C.BASE["exports"] * (P / WC.P0) ** SC.ELASTICITY_PRIORS["exports"][1]


# ------------------------------------------------------------- simulation ---
def run_scenario(name, n=None, err_seed=None, elas_seed=None, world_seed=None,
                 inputs=None, verbose=True):
    """One full global Monte Carlo scenario. Returns dict of draws + summary.

    U.S.-side errors/elasticities reuse v2's streams (same seeds); the v2
    export error draw is not used — exports are endogenous via the world
    module now.
    """
    n = n or WC.N_DRAWS
    spec = WC.SCENARIOS[name]
    err_seed = WC.SEED_US_ERR if err_seed is None else err_seed
    elas_seed = WC.SEED_US_ELAS if elas_seed is None else elas_seed
    world_seed = WC.WORLD_SEED if world_seed is None else world_seed
    inputs = inputs or S.load_inputs()

    # U.S. side: v2 machinery, export pace draw dropped.
    bq = S.draw_base_quantities(n, err_seed, inputs)
    elas5 = S.draw_elasticities(n, elas_seed)
    us_idx = [SC.CATEGORIES.index(c) for c in US_CATS]
    elas_us = elas5[:, us_idx]
    Q0_us = np.column_stack([bq["eth"], bq["feed"], bq["fsi"], bq["Qs0"]])
    S1 = bq["S0"]  # no U.S. supply shock in the world scenarios

    # World side.
    wq = draw_world_quantities(n, world_seed, spec)

    P, Q1_us, z, max_resid = clear_market_world(Q0_us, elas_us, S1, wq)

    use_dom = Q1_us[:, :3].sum(axis=1)
    ending = Q1_us[:, 3]
    us_exports = us_export_residual(z, wq)
    total_use = use_dom + us_exports
    # U.S. identity: supply == domestic use + exports + ending.
    ident_resid = np.abs(S1 - (total_use + ending))
    assert (ident_resid < 1e-3).all(), "U.S. identity violated"
    assert max_resid < 1e-6, "solver did not converge"

    # Competitor diagnostics at the clearing price (identity per country via
    # residual ending stocks: end_i = S_i - dom_i - XS_i).
    xs = competitor_xs(z, wq)                       # (n,3)
    comp = {}
    for j, c in enumerate(COMP_ORDER):
        g = WC.COMPETITORS[c]
        dom_i = g["dom"] * np.exp(wq["elas_dom"][:, j] * z)
        s_i = g["beg"] + wq["prod"][c] + g["imp"]
        comp[c] = {"dom": dom_i, "xs": xs[:, j],
                   "end": s_i - dom_i - xs[:, j], "supply": s_i}

    # World identity per draw: modeled blocks (US/BR/AR/UP) balance by
    # construction; ROW is fixed at September-vintage levels with ending
    # defined residually (see world_config.ROW).
    world_supply = (S1 + sum(comp[c]["supply"] for c in COMP_ORDER)
                    + WC.ROW["supply"])
    world_use = (total_use + ending
                 + sum(comp[c]["dom"] + comp[c]["xs"] + comp[c]["end"]
                       for c in COMP_ORDER)
                 + WC.ROW["dom"] + WC.ROW["exp"] + WC.ROW["end"])
    world_ident = np.abs(world_supply - world_use)
    assert (world_ident < 1e-3).all(), "world identity violated"

    # U.S. exports <= world imports per draw (holds by construction:
    # X_US = M - XS - X_OTHER with XS >= 0, X_OTHER > 0).
    world_imports = (wq["mrow0"] * np.exp(wq["elas_row"] * z)
                     + wq["mch0"] * np.exp(wq["elas_ch"] * z))
    assert (us_exports <= world_imports + 1e-9).all(), \
        "U.S. exports exceed world imports"

    # China allocation (level, pool assumption): logit shares of China's
    # realized import demand at the clearing price.
    lam = WC.CHINA_LAMBDA
    shares = china_shares(wq, lam)                  # (n,4) US/BR/AR/UP
    mch_star = wq["mch0"] * np.exp(wq["elas_ch"] * z)
    china_buys = shares * mch_star[:, None]

    stocks_use = ending / total_use
    draws = {
        "price": P,
        "ending": ending,
        "stocks_use": stocks_use,
        "supply": S1,
        "domestic_use": use_dom,
        "us_exports": us_exports,
        "total_use": total_use,
        "world_imports": world_imports,
        "q1_us": Q1_us,
        "elas_us": elas_us,
        "comp": comp,
        "china_shares": shares,       # (n,4) US/BR/AR/UP
        "china_buys": china_buys,     # (n,4) M bu allocated
        "china_imports": mch_star,
        "max_solver_resid_frac": max_resid,
        "max_identity_resid_mbu": float(ident_resid.max()),
        "max_world_identity_resid_mbu": float(world_ident.max()),
        "n_neg_us_exports": int((us_exports < 0).sum()),
        "n_neg_comp_ending": int(sum((comp[c]["end"] < 0).sum()
                                     for c in COMP_ORDER)),
        # v1-compatible keys for simulate.summarize
        "production": bq["S0"] - C.BASE["beg_stocks"] - C.BASE["imports"],
        "exports": us_exports, "ethanol": Q1_us[:, 0], "feed": Q1_us[:, 1],
        "out_of_bounds": (stocks_use < C.SU_LO) | (stocks_use > C.SU_HI),
    }
    summary = simulate.summarize(draws)
    summary["scenario"] = name
    summary["dProd"] = spec["dProd"]
    summary["dM_CH"] = spec["dM_CH"]

    def _pq(x):
        return {"p10": float(np.percentile(x, 10)),
                "p50": float(np.percentile(x, 50)),
                "p90": float(np.percentile(x, 90))}
    summary["us_exports"] = _pq(us_exports)
    summary["china_level_shares"] = {
        o: float(shares[:, j].mean()) for j, o in enumerate(ORIGINS)}
    if verbose:
        print(f"[{name}] dProd={spec['dProd'] or 'none'} "
              f"dM_CH={spec['dM_CH']:+.0f}")
        print("  P50 price=$%.2f  P50 US exports=%.0f  P50 ending=%.0f  "
              "P(s/u<10%%)=%.1f%%" % (
                  summary["price"]["p50"], summary["us_exports"]["p50"],
                  summary["ending"]["p50"], summary["p_su_lt_10"] * 100))
        print("  solver: 100%% converged (%d bisection iters/draw), "
              "max resid %.2e of supply" % (WC.BISECTION_ITERS, max_resid))
        print("  identity: max |S1-(use+ending)| = %.2e M bu; "
              "world identity max = %.2e M bu" % (
                  float(ident_resid.max()), float(world_ident.max())))
        print("  China level shares (logit, mean): " +
              ", ".join(f"{o}={summary['china_level_shares'][o]*100:.1f}%"
                        for o in ORIGINS))
    return {"draws": draws, "summary": summary, "inputs": inputs, "wq": wq}


# -------------------------------------------------------------- validation ---
def validation_checks():
    """Model-level checks independent of any scenario's random draws."""
    out = {}
    # 1. Calibration: residual curve passes through (P0, 3275) at median params.
    x0 = float(residual_export_curve(np.array([WC.P0]))[0])
    out["calibration_X_US_at_P0"] = x0
    out["calibration_ok"] = abs(x0 - 3275.0) < 1e-6
    # 2. Competitor export supply increasing in P at median draws.
    P_grid = np.array([0.9, 1.0, 1.1]) * WC.P0
    wq_med = {
        "prod": {c: np.full(3, WC.COMPETITORS[c]["prod"]) for c in COMP_ORDER},
        "elas_dom": np.full((3, 3), WC.DOM_ELAS_PRIOR[1]),
    }
    z = np.log(P_grid / WC.P0)
    xs = competitor_xs(z, wq_med)
    out["xs_increasing"] = bool(((np.diff(xs, axis=0) > 0).all()))
    out["xs_at_grid"] = {c: [float(v) for v in xs[:, j]]
                         for j, c in enumerate(COMP_ORDER)}
    # 3. X_US decreasing in P at median params (unique root).
    x_curve = residual_export_curve(np.array([3.0, 4.8, 7.0]))
    out["x_us_decreasing"] = bool((np.diff(x_curve) < 0).all())
    return out
