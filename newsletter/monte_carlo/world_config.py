"""Configuration for Monte Carlo v3-world: global extension of the structural
U.S. corn model (September 2026 vintage).

The v2 U.S. structural model is kept intact (4 domestic demand curves +
stock-demand curve, constant elasticity, P0=$4.80). v2's fixed export demand
curve is REPLACED by a residual export demand curve from the world module
(monte_carlo/world.py):

    X_US(P) = M_ROW(P) + M_CH(P) - XS_BR(P) - XS_AR(P) - XS_UP(P) - X_OTHER

Data: USDA FAS PSD, September 2026 vintage, staged in
psd_corn_world_stage_2026-09-18.csv (frozen raw pulls in
raw/psd_corn_2026-09-18/). All 2026/27 country identities were verified at
staging time (supply = use + ending). Anchors below are the exact staged
values (M bu); the task brief's rounded values are shown in comments.
"""
from . import config as C
from . import structural_config as SC

# --- Anchors (M bu, September 2026 vintage = 2026/27 MY) ---
P0 = SC.P0  # $4.80 — anchors every demand curve, same as v2

# U.S. demand categories kept from v2 (the export column of v2's elasticity
# draws is discarded; exports are endogenous now).
US_CATEGORIES = ["ethanol_grind", "feed_residual", "fsi", "stocks"]

# Competitor anchors: beg/prod/imp/dom/end (M bu). floor = 0.05*dom (pipeline
# stocks); kval = end - floor is the competitor's demand for carry, held
# fixed across prices (see world.py for the economics note).
#
# TIMING (Mindy's rule, 2026-09-18): no H1/H2 split. For a US marketing year
# (Sep-Aug), competitor PRODUCTION = the harvests that land/ship during OUR
# window, regardless of which local MY USDA files them under. See
# competitor_my_mapping_2026-09-18.csv for the full table. For US MY 2026/27:
#   BR -> local MY 2027/28 production (first crop Feb-Apr 2027 + safrinha
#         Jun-Aug 2027). The safrinha is USDA-filed under BR local MY 2027/28
#         but competes with our 2026/27 balance sheet, so it counts here.
#   AR -> local MY 2027/28 production (harvest Mar-Jun 2027).
#   UP -> local MY 2026/27 production (harvest Sep-Nov 2026; already aligned).
# USDA had not published BR/AR local-MY 2027/28 estimates in the Sep-2026
# vintage, so the prod anchors below are the latest observed local-MY
# productions used as no-change expectation proxies (flagged, not hidden).
# beg/imp/dom/end stay at September-vintage local-MY levels: the competitor
# block is an annual exportable-surplus identity, and a true Sep-Aug balance
# sheet would need monthly data PSD does not publish. The residual-curve
# calibration XS_i(P0) = observed exports is unaffected (anchors unchanged).
def _comp(beg, prod, imp, dom, end, exp, prod_sd):
    floor = 0.05 * dom
    return {"beg": beg, "prod": prod, "imp": imp, "dom": dom, "end": end,
            "exp": exp, "prod_sd": prod_sd, "floor": floor,
            "kval": end - floor}

COMPETITORS = {
    # task anchors: beg 583, prod 5472, imp 71, dom 4016, end 417, exp 1693
    "BR": _comp(582.8, 5472.2, 70.9, 4015.5, 417.5, 1692.8, 385.0),
    # task anchors: beg 185, prod 2165, imp 0, dom 697, end 158, exp 1496
    "AR": _comp(185.3, 2165.2, 0.2, 696.8, 157.9, 1496.0, 260.0),
    # task anchors: beg 112, prod 1252, imp 0, dom 283, end 215, exp 866
    "UP": _comp(112.1, 1251.9, 0.4, 283.4, 214.9, 866.1, 80.0),
}
COMP_ORDER = ["BR", "AR", "UP"]

# Documented local-MY -> US-MY production mapping (Mindy's timing rule).
# Keys: competitor -> dict with the PSD market_year whose production counts
# toward the given US marketing year, the harvest window, and the basis.
# USDA PSD local marketing years for corn: US Sep-Aug; BR Mar-Feb;
# AR Mar-Feb; UP Oct-Sep. General rule: competitor production for US MY
# Y/Y+1 = the harvest(s) landing Sep(Y)-Aug(Y+1).
COMPETITOR_MY_MAP = {
    # US MY 2026/27 (Sep 2026 - Aug 2027)
    "2026/27": {
        "BR": {"psd_market_year": 2027, "local_my": "2027/28 (Mar-Feb)",
               "harvests": "first crop Feb-Apr 2027 + safrinha Jun-Aug 2027",
               "anchor_basis": "proxy: local 2026/27 prod (2027/28 not yet published)"},
        "AR": {"psd_market_year": 2027, "local_my": "2027/28 (Mar-Feb)",
               "harvests": "Mar-Jun 2027",
               "anchor_basis": "proxy: local 2026/27 prod (2027/28 not yet published)"},
        "UP": {"psd_market_year": 2026, "local_my": "2026/27 (Oct-Sep)",
               "harvests": "Sep-Nov 2026",
               "anchor_basis": "staged PSD value (crop ~final)"},
    },
}

# Baseline production-draw sds (M bu). Under the timing rule, BR/AR
# production competing with our 2026/27 is ENTIRELY FORWARD (unplanted in
# September 2026: BR first crop plants Oct-Dec 2026, safrinha Jan-Mar 2027;
# AR plants Sep-Dec 2026), so the old "September vintage ~final" sds of 100
# were wrong for them. New sds = detrended historical volatility of PSD
# production 2018-2026 (resid sds: BR 384, AR 258 M bu). UP's competing
# harvest (Sep-Nov 2026) is being harvested now, so its sd stays 80.
# BR-AR draw correlation 0.5 (shared Southern-Hemisphere weather) is, if
# anything, MORE defensible now that both are forward crops; UP independent.
# Truncated at +/-3 sd. The +/-500 M bu safrinha scenarios (~1.3 sd of total
# BR production uncertainty) remain the named forward-uncertainty scenarios.
BR_AR_PROD_CORR = 0.5

# Competitor domestic-use elasticity: triangular (lo, mode, hi).
# v1-world choice (memo is silent on foreign domestic elasticities).
DOM_ELAS_PRIOR = (-0.30, -0.20, -0.10)

# --- World import demand (China broken out) ---
# M_ROW anchor = world imports - China imports = 7995.9 - 196.8 (task: 7799).
# M_CH anchor = 196.8 (task: 197). Elasticities are v1-world choices.
M_ROW0 = 7799.1
M_CH0 = 196.8
ROW_ELAS_PRIOR = (-0.60, -0.40, -0.20)   # rest-of-world import demand
CH_ELAS_PRIOR = (-0.90, -0.60, -0.30)    # China import demand
ROW_ANCHOR_SD = 0.04   # multiplicative anchor noise per draw, documented
CH_ANCHOR_SD = 0.15    # multiplicative anchor noise per draw, documented

# --- Residual calibration ---
# X_OTHER is the constant that makes the residual US export curve pass
# through the WASDE point (P0, 3275) at median parameters:
#   X_OTHER = (M_ROW0 + M_CH0) - sum_i XS_i(P0) - 3275  = 665.9 M bu
# i.e. the task's 666 M bu up to 0.1 M bu of staged-CSV rounding. The
# 666-vs-941 gap to implied other-exporter exports
# (world exports 8270.6 - BR/AR/UP/US exports 7329.9 = 940.7)
# is the PSD world imports/exports statistical discrepancy
# (8270.6 - 7995.9 = 274.7, MY/TY timing), documented in world.py.
def _xs_at_p0():
    tot = 0.0
    for c in COMP_ORDER:
        g = COMPETITORS[c]
        tot += g["beg"] + g["prod"] + g["imp"] - g["dom"] - g["floor"] - g["kval"]
    return tot

X_OTHER = (M_ROW0 + M_CH0) - _xs_at_p0() - C.BASE["exports"]  # ~= 665.9
assert abs(X_OTHER - 666.0) < 1.0, "X_OTHER calibration drifted from ~666"

# --- China allocation (level): logit on landed cost ---
# FOB spreads vs US Gulf ($/bu, v1-world choices); freight to China ($/bu).
CHINA_FOB_SPREADS = {"US": 0.0, "BR": -0.25, "AR": -0.20, "UP": -0.45}
CHINA_FREIGHT = {"US": 0.55, "BR": 0.45, "AR": 0.50, "UP": 0.65}
CHINA_SPREAD_SD = 0.10   # per-draw spread noise, documented
CHINA_ORIGINS = ["US", "BR", "AR", "UP"]
# US share of China's corn imports: calibrated to RECENT ACTUALS (reset
# 2026-09-18 per Mindy; the old (0.25, 0.45) band was a 2020/21-2022/23
# boom-era number). USDA FAS PSD, China corn, attribute "TY Imp. from U.S."
# / "TY Imports" (thousand MT), frozen in raw/psd_corn_2026-09-18/:
#   MY2023/24: 2,301 / 23,330 = 9.9%  (marketYear 2023, Sep-2025 vintage)
#   MY2024/25:    27 /  1,823 = 1.5%  (marketYear 2024, Jan-2026 vintage)
#   MY2025/26:     0 /  4,000 = 0.0%  (marketYear 2025, Aug-2026 vintage)
# Trailing-3MY average = 3.8%. Target band = average +/- 10 points, lower
# bound clipped at 0. Revisit the average each September when the new MY's
# PSD finalizes (see CALIBRATION.md); the band is deliberately wide because
# the series is volatile (boom-bust in China's buying).
CHINA_LAMBDA = 1.0  # placeholder; overwritten by calibrate_china_lambda()
CHINA_US_SHARE_MID = 0.038
CHINA_US_SHARE_TARGET = (0.00, 0.14)

# --- Simulation ---
N_DRAWS = C.N_DRAWS            # 10,000
# Common random numbers across scenarios (documented variance-reduction
# choice): identical seeds per scenario, so scenario deltas are clean and
# the h2 presets reproduce the +/-500 scenarios exactly. US error/elasticity
# seeds match v2's base scenario, so base_global's U.S.-side draws are the
# same draws as v2 base (only the export demand mechanism changes).
SEED_US_ERR = SC.SEED          # 20260918; prod/eth/feed streams match v2 base
SEED_US_ELAS = SC.ELAS_SEED    # domestic elasticity cols match v2 base
WORLD_SEED = 810001            # separate stream for world draws

# --- Scenarios ---
# dProd: additive competitor-production shift (M bu). Under the timing rule
# the +/-500 M bu Brazil shifts ARE the forward safrinha uncertainty for our
# 2026/27 (the Jun-Aug 2027 safrinha, USDA-filed under BR local MY 2027/28,
# competes with our balance sheet): bumper = big safrinha, drought = failed
# safrinha. dM_CH: additive China import-demand anchor shift (M bu).
SCENARIOS = {
    "base_global":      {"dProd": {},             "dM_CH": 0.0},
    "brazil_bumper":    {"dProd": {"BR": 500.0},  "dM_CH": 0.0},
    "brazil_drought":   {"dProd": {"BR": -500.0}, "dM_CH": 0.0},
    "china_surge":      {"dProd": {},             "dM_CH": 200.0},
    # H2-labeled presets: SAME full-year model and mechanics as the +/-500
    # scenarios (Mindy: no H1/H2 split of the marketing year). The labels are
    # kept for the newsletter's seasonal framing — the safrinha size is what
    # resolves by Jun-Aug — but there is no separate H1/H2 clearing
    # mechanism and none is faked.
    "h2_brazil_bumper": {"dProd": {"BR": 500.0},  "dM_CH": 0.0,
                         "h2_label": True},
    "h2_brazil_drought": {"dProd": {"BR": -500.0}, "dM_CH": 0.0,
                          "h2_label": True},
}
SCENARIO_ORDER = ["base_global", "brazil_bumper", "brazil_drought",
                  "china_surge", "h2_brazil_bumper", "h2_brazil_drought"]

# --- Rest of world (fixed at September-vintage levels; documented) ---
# ROW supply/use/ending are NOT stochastic: only US/BR/AR/UP quantities move.
# ROW ending is defined residually so the ROW identity holds exactly (the
# 0.1 M bu absorbs staged-CSV rounding, e.g. BR's 6125.9 vs 6125.8).
WORLD = {"beg": 11864.8, "prod": 50822.2, "imp": 7995.9,
         "dom": 51700.2, "exp": 8270.6, "end": 10712.1}
_US4 = {"beg": C.BASE["beg_stocks"], "prod": C.BASE["production"],
        "imp": C.BASE["imports"], "dom": 12905.0, "exp": C.BASE["exports"],
        "end": 1567.0}
_ROW4 = {k: sum([_US4[k]] + [COMPETITORS[c][k] for c in COMP_ORDER])
         for k in ("beg", "prod", "imp", "dom", "exp")}
ROW = {k: WORLD[k] - _ROW4[k] for k in ("beg", "prod", "imp", "dom", "exp")}
ROW["supply"] = ROW["beg"] + ROW["prod"] + ROW["imp"]
ROW["end"] = ROW["supply"] - ROW["dom"] - ROW["exp"]

# --- Solver (same bracket conventions as v2) ---
PRICE_FLOOR, PRICE_CAP = SC.PRICE_FLOOR, SC.PRICE_CAP
BISECTION_ITERS = SC.BISECTION_ITERS

# --- Live freight legs (monte_carlo/freight.py monitor) ---
# When True, china_shares() centers the logit on the freight monitor's
# latest staged week instead of the static spreads below. Per-leg
# fallback keeps the model runnable when a leg is missing or stale.
FREIGHT_LIVE = True
FREIGHT_US_PORT = "PNW_EST"  # which US outlet represents "US":
                             # "GULF" | "PNW" | "PNW_EST" (estimated)
# Mindy's 2026-09-18 decision: adopt the ESTIMATED PNW leg as the US basis
# (replacing Gulf). No public PNW->China fixture newer than Aug 4, 2026
# ($35.00/mt, heavy grain, Maritime Research via GTR Table 20) exists — 45
# days stale vs the 35-day gate, all GTRs through Sep 17, 2026 checked —
# so a direct PNW quote cannot go live. The direct Gulf->PNW fixture
# regression was attempted and FAILED (only 2 co-occurring PNW/Gulf->China
# fixture pairs in 5.75 years of GTRs: the fixtures simply don't co-occur).
# Instead the proxy is: live GTR Table 1 PNW->Japan weekly rate ($37.75/mt,
# week ending 2026-09-16) + an empirically estimated China premium of
# -0.96 $/mt (n=8 PNW->China fixtures, Jan 2021-Aug 2026, vs the Table 1
# Japan rate for the fixture week; sd 2.11, no time trend, no level
# dependence; OLS slope 0.98 ~= 1, R^2=0.73; holdout OOS RMSE 0.34 $/mt).
# Current proxy: 36.79 $/mt, prediction SE 2.24 (~$0.06/bu) — inside the
# model's existing per-draw spread noise (sd 0.10 $/bu), so no extra noise
# term. Full methodology: freight_pnw_proxy.md. Honest consequence: the
# leg is flagged "estimated" in the staged CSV, in freight_basis, and in
# every note — it is a modeled number, not a quote. With PNW as the basis
# the US is competitive into China again (landed ~$6.93/bu vs Gulf-basis
# $8.29), which matches the economics: the PNW is the shorter Asia route
# for corn (the Gulf is mainly a soybean-to-China artery).
FREIGHT_ALLOW_ESTIMATED_PNW = True  # allow the flagged US_PNW_EST leg
# (never a silent fallback: it is recorded as "estimated", not live)
FREIGHT_MAX_VINTAGE_DAYS = 35
# Gate rationale (Mindy's decision, 2026-09-18): the monitor's fixture-mean
# legs are 4-week means BY CONSTRUCTION (GTR fixtures cover a 28-day window
# plus reporting lag), so a 14-day gate would keep them on fallback forever
# even with weekly refreshes. 35 days keeps the 4-week means live across
# weekly refreshes — apples-to-apples means vs means. Point-quote legs
# (GTR Table 1 weekly) still age out on their own vintage.
# Static fallbacks = the old v1-world choices, kept verbatim ($/bu).
FREIGHT_FALLBACK_SPREADS = {"US": 0.0, "BR": -0.25, "AR": -0.20, "UP": -0.45}
FREIGHT_FALLBACK_FREIGHT = {"US": 0.55, "BR": 0.45, "AR": 0.50, "UP": 0.65}
