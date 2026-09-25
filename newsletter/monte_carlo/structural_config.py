"""Configuration for Monte Carlo v2 (structural supply/demand, September 2026).

Reuses v1's input conventions: base case, error sds, seeds, and workbook
paths come from monte_carlo/config.py (v1), which reads the validated
workbook layer (HIST_BALANCE row 20 = WASDE #675 2026/27).
"""
from . import config as C

# --- Demand system ---
# P0 anchors every demand curve: Q_i(P) = (Q_i0 + dD_i) * (P/P0)^eps_i.
# $4.80 is WASDE #675's season-average price, the price consistent with the
# unperturbed base quantities.
P0 = 4.80

# Demand categories in solver order. "stocks" is the 5th demand: the market's
# demand to carry grain out of the year. Without it, price clearing
# (sum of use = supply) would force ending stocks to zero by construction.
CATEGORIES = ["exports", "ethanol_grind", "feed_residual", "fsi", "stocks"]

# Triangular elasticity priors: (lo, mode, hi). All are symmetric, so the
# median draw equals the mode — the "median elasticities" deterministic run
# uses the modes. Sources documented per line; "memo" = the project design
# memo section 4 literature ranges; "v2 choice" = set for v2 (memo silent).
ELASTICITY_PRIORS = {
    # memo: export demand short-run ~= -1.0 (corn/soy)
    "exports":       (-1.20, -1.00,  -0.80),
    # memo: feed -0.2 to -0.5
    "feed_residual": (-0.50, -0.35,  -0.20),
    # v2 choice: memo didn't pin ethanol; centered between feed and exports
    "ethanol_grind": (-0.50, -0.375, -0.25),
    # memo: wheat food -0.1 to -0.25 (used as the food/seed/other proxy)
    "fsi":           (-0.25, -0.175, -0.10),
    # v2 choice: stockholding demand; moderately elastic carry demand
    "stocks":        (-1.50, -1.00,  -0.50),
}

# --- Simulation ---
N_DRAWS = C.N_DRAWS            # 10,000
SEED = C.SEED                  # 20260918; error stream matches v1 exactly
ELAS_SEED = 710001             # separate stream for elasticity draws
CURRENT_WEEK = C.CURRENT_WEEK  # week-2 FAS pace residuals, as in v1

# --- Export error v3 (demand-curve-consistent; see INTEGRATION_SPEC.md) ---
# Working export demand elasticity for the Ahat inference; must equal
# monte_carlo.export_errors.EPS_WORK (the literature mode, IV-validated).
EXPORT_EPS_WORK = -1.0
# Divide out the estimated price->booking-pace channel (gamma_w) when
# inferring the demand shifter from week-w commitments.
EXPORT_PACE_PURGE = True
# Added to err_seed for the independent Ahat bootstrap (seed discipline:
# one stream for the 3-dim prod/eth/feed normals, seed+offset for exports).
EXPORT_ERR_SEED_OFFSET = 1

# --- Scenarios ---
# dS: additive supply shift (M bu). dD: additive demand-curve shifts (M bu).
SCENARIOS = {
    "base":         {"dS": 0.0,   "dD": {}},
    "yield_minus5": {"dS": C.SHOCK_PROD_DELTA, "dD": {}},  # -442.5 M bu
    "export_surge": {"dS": 0.0,   "dD": {"exports": 200.0}},
}
SCENARIO_ORDER = ["base", "yield_minus5", "export_surge"]

# --- Solver ---
PRICE_FLOOR, PRICE_CAP = 0.50, 50.0   # bisection bracket on price ($/bu)
BISECTION_ITERS = 120                 # fixed; 2^-120 << any needed tolerance
