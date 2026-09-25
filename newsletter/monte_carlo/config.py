"""Configuration for the corn Monte Carlo v1 (September 2026 vintage)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # commodity-newsletter-design/
WORKBOOK = BASE_DIR / "US_Corn_History_and_Pace_v1.xlsx"
STAGED_WEEKLY = BASE_DIR / "fas_corn_weekly_commitment_stage_2007-2026.csv"
SCURVE_WINDOWS = BASE_DIR / "fas_corn_scurve_windows.csv"
CHART_DIR = BASE_DIR / "mc_charts"

# Simulation
N_DRAWS = 10_000
SEED = 20260918

# Latest week of live 2026/27 FAS export-sales data entered in the workbook
# (PACE_EXPORT live block). Export pace residuals are conditioned on this week.
CURRENT_WEEK = 2

# --- Base case: WASDE #675, September 2026, 2026/27 Proj column (M bu) ---
# Source: HIST_BALANCE row 20 of the workbook (typed from wasde0926.txt,
# verified in marketing-year-audit-2026-09-18.md).
BASE = {
    "beg_stocks": 1922.0,
    "production": 15800.0,
    "imports": 25.0,
    "exports": 3275.0,
    "ethanol_grind": 5600.0,
    "feed_residual": 5950.0,
    # FSI (food/seed/industrial) = 6955 in WASDE; ethanol is a memo subset of it.
    # Non-ethanol FSI is held fixed in v1.
    "fsi_non_ethanol": 1355.0,  # 6955 - 5600
    "harvested_ac_m": 88.5,     # for the yield-shock scenario
}
# Derived WASDE point estimates (for validation comparisons)
BASE_TOTAL_SUPPLY = BASE["beg_stocks"] + BASE["production"] + BASE["imports"]  # 17,747
BASE_TOTAL_USE = (BASE["exports"] + BASE["ethanol_grind"]
                  + BASE["feed_residual"] + BASE["fsi_non_ethanol"])            # 16,180
BASE_ENDING = BASE_TOTAL_SUPPLY - BASE_TOTAL_USE                                # 1,567
BASE_STOCKS_USE = BASE_ENDING / BASE_TOTAL_USE                                 # 0.0969
BASE_PRICE = 4.80

# --- Forecast-error standard deviations (M bu), v1 ---
# We do NOT have as-published September-WASDE vintage CSVs, so production /
# ethanol / feed errors are stated v1 priors (see monte_carlo/README.md).
# Export errors come from the empirical pace residuals (no prior needed).
ERROR_SD = {
    "production": 300.0,   # ~1.9% of base; September production forecasts miss by a few %
    "ethanol_grind": 100.0,  # ~1.8% of base
    "feed_residual": 150.0,  # ~2.5% of base; F&R is the noisiest balance-sheet line
}

# Scenario: -5 bu/acre yield shock
YIELD_SHOCK_BU_AC = -5.0
SHOCK_PROD_DELTA = YIELD_SHOCK_BU_AC * BASE["harvested_ac_m"]  # -442.5 M bu

# Plausibility bounds (flag, don't truncate)
SU_LO, SU_HI = 0.03, 0.40
