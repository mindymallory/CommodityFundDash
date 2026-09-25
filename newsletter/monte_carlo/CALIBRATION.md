# Calibration methodology — corn Monte Carlo (structural + global)

*2026-09-18. Companion to `monte_carlo/README.md`.*

## The governing principle

Recalibration moves **quantities** and holds **parameters** fixed:

- **Quantities** (baseline use levels, error bands, freight quotes, trade
  shares, competitor crops) are perishable — they describe *this* marketing
  year. They get re-anchored on schedule.
- **Elasticities** are the model's durable beliefs about how the world
  responds to price. They come from the published literature, change only
  when the literature review is redone, and are never touched by a data
  refresh.

When in doubt about whether something should move: quantities move,
elasticities don't.

## Functional form

Demand is **constant-elasticity** (log-linear), not linear. Each demand
category *i* (exports, ethanol grind, feed/residual, food/seed/industrial,
desired ending stocks) is:

```
Q_i(P) = (Q_i0 + dD_i) · (P / P0)^ε_i
```

Parameters per category: **Q_i0** (baseline quantity), **dD_i** (baseline
demand shifter — currently nonzero only for exports, via the purged
week-conditioned read described below), **ε_i** (price elasticity, drawn
from its triangular prior each Monte Carlo draw). **P0 = $4.80/bu** is the
single common price anchor: the season-average price consistent with the
unperturbed base quantities. The solver finds the price P where total
demand equals predetermined within-year supply.

## Calibration cadence

| What | Moves when |
|---|---|
| Q0 baselines + P0 | **Once per marketing year**, re-anchored to the **September** WASDE that opens the new MY. Fixed all year for stability. |
| Elasticity priors | Only when the literature review is redone. Never on a data refresh. |
| Export demand shifter (dD) | **Weekly** — each week's FAS export-commitment read updates the current-week demand-shift estimate through the fixed purged-error schedule. |
| Monte Carlo error draws | Every run (seeded); the error *schedules* are fixed estimates, the *draws* are fresh each run. |
| Freight legs | **Weekly** — the freight monitor refreshes quotes each week; legs go live/fallback through the 35-day freshness gate. |
| China share target | **Each September** — trailing-3MY actual US share of China's imports, recomputed when the new MY's PSD finalizes. |
| Competitor anchors | **Each September** — new PSD vintage + Mindy's timing rule. Brazil/Argentina no-change proxies stand (flagged) until USDA publishes actual forecasts. |
| PNW freight premium | Re-estimated whenever a new PNW→China fixture is published; a within-gate fixture retires the proxy entirely. |

Within the marketing year, new information enters through the **weekly
export-commitment demand shifter** and the **Monte Carlo error draws** —
the Q0 baselines stay fixed all year. This is deliberate: it keeps the
model's "what we believed in September" separate from "what we've learned
since," which is exactly what the newsletter needs to narrate.

## Parameter groups

### 1. Elasticity priors — triangular (lo, mode, hi) per category

| Category | Prior (lo, mode, hi) | Source |
|---|---|---|
| Exports | (−1.20, −1.00, −0.80) | Literature-anchored: Reimer, Zheng & Gehlhar (2012) short-run ≈ −1.04 to −1.11; Abbott, Boussios & Lowenberg-DeBoer (2016) review centers ≈ −1.0. Cross-checked by supply-shock IV on historical data: −1.27 ± 0.49 (first-stage F = 13.3). |
| Feed/residual | (−0.50, −0.35, −0.20) | Literature-supported range (see review). |
| Ethanol grind | (−0.50, −0.375, −0.25) | Working choice; **flagged**: the literature review suggests re-centering to (−0.45, −0.30, −0.15). Not yet approved/applied — pending Mindy's decision. |
| Food/seed/industrial | (−0.25, −0.175, −0.10) | Literature-supported. |
| Desired ending stocks | (−1.50, −1.00, −0.50) | **No direct literature basis** — a modeling convenience. The storage literature treats inventory demand as nonlinear; this constant-elasticity curve must be labeled an assumption, sensitivity-tested, and is a candidate for replacement by a Working-style storage curve. |

Full paper-level citations: `elasticity-literature-review.md`. Several
older estimates in that review are verified secondhand via Abbott et al.
(2016); the review flags which. Priors are symmetric triangulars, so the
median draw equals the mode — the "median elasticities" deterministic run
uses the modes.

**Recalibration:** only when the literature review is redone. A new WASDE,
a new freight quote, or a new trade print never moves these.

### 2. Baseline quantities Q0 (+ P0)

Anchored to the **September WASDE that opens the marketing year**
(currently #675, 2026/27). P0 = $4.80 is that WASDE's season-average
price. A new marketing year moves the Q0s (and P0); **nothing within the
year does** — see the cadence table. Because the functional form is
constant-elasticity, re-anchoring only moves Q0s; elasticities are
untouched by construction.

### 3. Error standard deviations

Each stochastic input (yield/supply, ethanol, feed, export demand shift)
carries an error schedule. **Current state: stated priors** (documented in
`README.md`), which are provisional. The plan is to replace them with
**as-published WASDE vintage errors** once that pipeline is staged
(outstanding work — see project notes). When the vintage-error staging
lands, the schedules become estimated quantities; until then, treat
results as conditional on the stated priors.

### 4. Export demand shifter — the purged method (`export_errors.py`)

The old method compared weekly export commitments to a historical-average
pace curve — which misread movement *along* the price-responsive export
demand curve as a demand *shift* and priced it twice. The corrected (v3)
method:

1. Measures the week-2 commitment residual **against the model's own
   export demand curve** at the current price, not against a historical
   average.
2. Purges the price→booking-pace channel (the old residual regressed on
   log price with coefficient +0.95, R² = 0.52 — over half the "error"
   was price movement, now removed).
3. Applies a **week-conditioned error schedule** that tightens through
   the season: sd(w) = 0.252 · exp(−0.041w) — 22.2% at week 2, 9.8% at
   week 26, 2.8% at week 53.

The *schedule* is a fixed estimated quantity (re-estimated only if the
methodology changes). The *current-week read* updates **weekly** from FAS
export-sales data (corn code 401) — this is the model's within-year
learning channel. Validation: a synthetic +50% price-spike/no-demand-shift
test recovers a demand-shift ratio of exactly 1.0000.

### 5. Freight legs

- **35-day freshness gate** (`FREIGHT_MAX_VINTAGE_DAYS = 35`) — Mindy's
  2026-09-18 "apples to apples" decision: the monitor's fixture-mean legs
  are 4-week means by construction, so 35 days keeps them live across
  weekly refreshes.
- **Live sources:** USDA AMS Grain Transportation Report Table 1 (weekly
  rates, e.g. PNW→Japan) and Table 20 fixture means (Maritime Research),
  plus IGC FOB quotes via FAS.
- **PNW→China proxy** (`freight_pnw_proxy.md`): no public PNW→China
  fixture newer than 2026-08-04 exists (all GTRs through 09/17/2026
  checked), and a direct Gulf→PNW fixture regression failed (only 2
  co-occurring pairs in 5.75 years — honestly abandoned). Adopted proxy:
  live GTR Table 1 PNW→Japan rate + estimated China premium **−$0.96/mt**
  (n=8 fixtures 2021–2026, sd 2.11, no trend/level dependence, OLS slope
  ≈ 1 → parsimonious constant premium; holdout OOS RMSE $0.34/mt).
  Current estimate $36.79/mt, SE $2.24 (~$0.06/bu — inside the model's
  existing per-draw spread noise, so no extra noise term). Flagged
  **"estimated"** everywhere (staged CSV origin `US_PNW_EST`, JSON
  `freight_basis`, workbook); gated by `FREIGHT_ALLOW_ESTIMATED_PNW`
  (never a silent fallback). **Retires on a real within-gate fixture**
  via a one-line `FREIGHT_US_PORT` flip.
- AR (proxy fixture) and UP (no freight leg) remain on static fallback;
  their China shares are basis-weak and labeled as such.

### 6. China allocation — lambda calibration

China's import demand is split across US/Brazil/Argentina/Ukraine by a
logit on landed cost. The sensitivity parameter **lambda** is grid-searched
over [1, 4] to minimize |US share − target midpoint|.

- **Target (reset 2026-09-18 per Mindy):** trailing-3MY actual US share of
  China's corn imports, from USDA FAS PSD ("TY Imp. from U.S." /
  "TY Imports"), frozen in `raw/psd_corn_2026-09-18/`:
  MY2023/24 **9.9%**, MY2024/25 **1.5%**, MY2025/26 **0.0%** →
  average **3.8%**, band **(0.00, 0.14)** (average ± 10 points, floored
  at zero). Recomputed each September.
- **History:** the old (0.25, 0.45) band with midpoint 0.35 was a
  2020/21–2022/23 boom-era number from the original build brief. China's
  US-corn buying collapsed after 2023 (Brazil took the trade; China's
  total imports shrank to ~4–5 MMT), so the old target became
  unreachable — lambda pinned at the 1.0 grid boundary trying.
- **Wiring fix (v9):** the calibrated lambda is now written into the
  simulation (`WC.CHINA_LAMBDA`). Previously the calibration was
  print-only and the model always ran at the 1.0 placeholder — found and
  fixed during the v9 reset.
- **Current state:** lambda calibrates to the **4.0 upper grid boundary**
  (US baseline share 13.5%, inside the wide 0–14% band — target "met,"
  but only via the band's width). The grid range is now the binding
  constraint on the high side; extending it is an open follow-up, not
  yet approved.

### 7. Competitor supply anchors

FAS PSD **September vintage** + **Mindy's timing rule**: no H1/H2 split —
competitor supply counts as whatever harvests/ships inside the US
Sep–Aug marketing year, regardless of which local MY USDA files it under
(`competitor_my_mapping_2026-09-18.csv`). For US MY 2026/27: Ukraine's
fall-2026 crop, Brazil's early-2027 first crop and mid-2027 safrinha,
Argentina's 2027 crop. Brazil/Argentina 2027/28 forecasts were not yet
published in the September 2026 vintage, so previous local-year values
stand as **explicitly flagged no-change proxies** — replaced when USDA
publishes actual forecasts.

## What "recalibrated" means in the workbook

The workbook's `MC_GLOBAL` tab is values-only and dated per run (v4, v5,
…); the `CHANGELOG` records every calibration decision with its date and
rationale. Staged CSVs are authoritative; archive tabs are frozen
view-only copies. Nothing in the workbook is a live formula pointing at
the Python model — the handoff is values + dated method notes, so Mindy
can always see exactly what the model believed on any given date.
