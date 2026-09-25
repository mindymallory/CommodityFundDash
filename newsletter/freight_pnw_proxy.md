# Estimating PNW→China ocean freight: methodology note

**Decision:** Mindy, 2026-09-18 — adopt the estimated PNW leg as the US basis
for the China/ROW logit (replacing Gulf), flagged "estimated" everywhere.

**Problem:** No public PNW→China ocean fixture newer than Aug 4, 2026
($35.00/mt, heavy grain, Maritime Research via GTR Table 20) exists — 45
days stale vs the 35-day gate, all GTRs through Sep 17, 2026 checked.
A direct PNW quote therefore cannot go live.

## What was tried first (and failed)

The direct approach — regress PNW→China fixtures on Gulf→China fixtures —
was attempted on 5.75 years of GTR Table 20 fixtures (287 weekly GTR PDFs,
Jan 2021–Sep 2026, parsed with `monte_carlo/freight.py::parse_fixtures`
plus an old-format parser for the pre-2024 Table 17/18 layout). Result:
**only 2 co-occurring PNW/Gulf→China fixture pairs** in the entire archive
(Nov 2025: Gulf 56.00 / PNW 29.25; Aug 2026: Gulf 69.25 / PNW 35.00).
The fixtures simply don't co-occur — PNW→China fixtures are rare because
China's US-corn buying collapsed after 2023. A 2-point "regression" is not
an estimate. This route was abandoned, honestly.

## What was adopted instead

**PNW→China = live GTR Table 1 PNW→Japan weekly rate + estimated China premium.**

The Table 1 PNW→Japan rate is fresh every week ($37.75/mt, week ending
2026-09-16, AMS dataset, within the gate). The premium (China minus Japan,
same origin) is a short-haul differential — a few hundred extra nautical
miles, ~2 days' steaming — that should be small and stable. Estimated from
**8 PNW→China fixtures** (Jan 2021–Aug 2026; 6 heavy grain + 2 soybeans —
vessel economics are grain-agnostic), each compared against the Table 1
PNW→Japan rate for its week:

| Fixture date | Grain | PNW→China ($/mt) | PNW→Japan ($/mt) | Premium |
|---|---|---|---|---|
| 2021-01-02 | Soybeans | 22.10 | 23.75 | −1.65 |
| 2023-03-25 | Heavy grain | 28.00 | 30.50 | −2.50 |
| 2023-03-25 | Heavy grain | 29.00 | 30.50 | −1.50 |
| 2025-02-12 | Heavy grain | 27.50 | 26.75 | +0.75 |
| 2025-11-28 | Heavy grain | 29.25 | 29.75 | −0.50 |
| 2025-11-28 | Soybeans | 32.75 | 29.75 | +3.00 |
| 2026-02-05 | Heavy grain | 25.00 | 29.00 | −4.00 |
| 2026-08-04 | Heavy grain | 35.00 | 36.25 | −1.25 |

**Premium = −0.96 $/mt, sd 2.11 $/mt** (se of mean 0.75; heavy-grain-only
sensitivity: −1.50 ± 1.62 — same answer).

## Specification tests

- **Constant premium** (adopted): c = −0.96 ± 0.75.
- **OLS** PNW_CN = a + b·PNW_JP: b = 0.98 (se 0.24 — indistinguishable from
  1), a = −0.24 (se 7.20 — indistinguishable from 0), R² = 0.73.
  The data cannot distinguish this from the constant-premium form, so the
  parsimonious constant premium is used.
- **Ratio** PNW_CN/PNW_JP: 0.967 ± 0.073 → at $37.75 gives $36.50, vs
  $36.79 from the premium form. Immaterial difference.

## Stability tests

- Premium trend: **+0.26 $/mt/yr (se 0.43)** — not significant; corr with
  time 0.24.
- Level dependence: corr(premium, PNW→Japan level) = **−0.04** — none.
  The sample spans a full freight cycle (2021 boom, 2023–25 soft, 2026 hot)
  with no drift.
- Structural-break watch: the 2023–24 Panama Canal drought widened the
  *Gulf–PNW spread*, but the *China–Japan premium from the same origin*
  is a different, much shorter differential and shows no break.

## Out-of-sample validation

Hold out the last 3 months (fit on 7 fixtures through Feb 2026, predict the
Aug-2026 fixture at the highest market level in the sample):
predicted $35.34/mt vs actual $35.00/mt → **error −0.34 $/mt (OOS RMSE 0.34)**.

## Cross-check against the Gulf quote

Implied Gulf–PNW spread to China: 74.50 − 36.79 = **37.71 $/mt**.
The GTR's own published Gulf-vs-PNW spread to Japan for Aug 2026 is 36.19
(Table 1 weekly: 39.00 for Sep 16); the Aug-2026 fixture pair spread to
China was 34.25. The implied 37.71 sits inside that envelope — consistent.

## Current estimate (week ending 2026-09-16)

**PNW→China = 37.75 + (−0.96) = 36.79 $/mt = $0.9345/bu**,
prediction SE 2.24 $/mt (~$0.06/bu), 95% band $32.40–$41.19/mt.
Landed US corn into China via PNW: (236.00 + 36.79)/39.368 = **$6.93/bu**.

The prediction SE sits inside the world model's existing per-draw FOB-spread
noise (sd $0.10/bu), so no extra noise term was added.

## Honesty plumbing

- The leg lives in the staged CSV as origin **`US_PNW_EST`**, flagged
  **`assumption;estimated`**, method `proxy:premium_regression`, with the
  Table 1 week as its vintage (recomputed every weekly refresh from that
  week's Table 1 rate — see `build_week` in freight.py).
- `world.py::_live_legs` uses it **only** when
  `FREIGHT_ALLOW_ESTIMATED_PNW` is True, and records it in
  `freight_basis["estimated_legs"]` — never in `fallback_legs`, never
  silently.
- If a real PNW→China fixture ever goes live within the gate, flip
  `FREIGHT_US_PORT` back to `"PNW"` (one line) and the estimate retires.

## Data artifacts

- `raw/gtr_history/` — 287 GTR PDFs, Jan 2021–Sep 2026 (frozen).
- `/tmp` (build-time): `fixtures_raw.json`, `fixtures_old_format.csv`,
  `ocean_rates_monthly.csv`, `pnw_china_premium.csv`, `table1_series.pkl`,
  `gtr_dates*.txt`, analysis scripts `pnw_proxy_analysis.py`,
  `parse_old_fixtures.py`, `scrape_ocean_rates.py`.
- Chart: `mc_charts/mc_freight_pnw_premium.png`.
