# Monte Carlo v3-world (global) — results summary, live-freight update (2026-09-18)

The v2 U.S. structural model is kept intact; v2's fixed export demand curve is replaced by a **residual export demand curve** built from a world module: the world wants `M_ROW(P) + M_CH(P)` of imports, Brazil / Argentina / Ukraine supply `XS_i(P)` (upward-sloping in price through domestic demand rationing), a fixed ~666 M bu goes to other exporters, and the U.S. gets the residual. 10,000 draws per scenario, seeded and deterministic.

## Headline numbers (P50)

| Scenario | U.S. price ($/bu) | U.S. exports (M bu) | Ending stocks (M bu) | P(s/u<10%) |
|---|---|---|---|---|
| Base (global) | 4.80 | 3277 | 1567 | 68.4% |
| Brazil bumper (+500 M bu) | 4.57 | 2986 | 1642 | 38.8% |
| Brazil drought (-500 M bu) | 5.04 | 3567 | 1494 | 89.2% |
| China surge (+200 M bu) | 4.89 | 3392 | 1538 | 78.0% |
| H2 Brazil bumper (+500 M bu) | 4.57 | 2986 | 1642 | 38.8% |
| H2 Brazil drought (-500 M bu) | 5.04 | 3567 | 1494 | 89.2% |

## China +200 M bu surge: who supplies the marginal bushels?

Structural marginal capture (Δ equilibrium exports ÷ 200):
- US: 57.9% (116 M bu)
- BR: 7.8% (16 M bu)
- AR: 1.4% (3 M bu)
- UP: 0.6% (1 M bu)

Level allocation of China's total buys (logit on landed cost, lambda=1.00): US 19.5%, BR 27.7%, AR 25.1%, UP 27.7%.
Note: the logit now reads the weekly freight monitor's legs (week ending 2026-09-16), with per-leg fallback to the static priors: this week ALL four legs are on fallback — BR's fixture-mean leg is 28 days old vs the 14-day FREIGHT_MAX_VINTAGE_DAYS gate (GTR fixtures cover a 28-day window plus reporting lag), the US_PNW leg is a stale assumption, AR is a proxy fixture, UP has no freight leg. So this run's allocation equals the static baseline; the hook is live and the first weekly refresh with fresh fixtures will flip qualifying legs automatically. Fallback legs are recorded per run in the JSON freight_basis. This affects only the level accounting, not price clearing.

## v2-vs-global validation (base)

Same U.S.-side draws as v2 base (identical seeds); only the export demand mechanism changes, so deltas isolate curve-shape effects:
- P50 price: v2 $4.47 → global $4.80 (Δ +0.33)
- P50 U.S. exports: v2 2838 → global 3277 (Δ +439 M bu)
- P(s/u<10%): v2 26.7% → global 68.4% (Δ +41.7 pp). It RISES, not falls: the week-2 export pace-residual draw (sd ~29%) is dropped, but the residual curve is anchored at the WASDE 3275 export level while v2's median pace draw sat ~4% below it (~3,151) — week-2 pace typically understates final exports. The level effect dominates the variance effect: the global distribution is tighter but centered on a tighter sheet.

## Key assumptions and data gaps

- Anchors: USDA FAS PSD September 2026 vintage (staged `psd_corn_world_stage_2026-09-18.csv`); all 2026/27 country identities verified at staging.
- Competitor export supply slopes up in price ONLY through domestic demand rationing; competitor carry demand is fixed at September-vintage ending stocks (the `kval` term — needed so the residual curve passes through the WASDE point).
- Competitor timing (Mindy's rule, 2026-09-18): no H1/H2 split — competitor production = harvests landing in OUR Sep-Aug window: BR local MY 2027/28 (first crop Feb-Apr 2027 + safrinha Jun-Aug 2027), AR local MY 2027/28 (Mar-Jun 2027), UP local MY 2026/27 (Sep-Nov 2026). Full table: competitor_my_mapping_2026-09-18.csv. BR/AR baseline sds are FORWARD uncertainties (385/260 M bu, detrended historical volatility — the competing crops are unplanted in Sep 2026); the ±500 scenarios ARE the named forward-safrinha scenarios. PSD does not split first/safrinha crops (Brazil safrinha ≈78% is narrative only).
- Full-year clearing model (Mindy: no H1/H2 split of the marketing year). The h2_ presets are the same full-year model as the ±500 scenarios; the labels are kept only for the newsletter's seasonal framing — no separate mechanism, none faked.
- Rest-of-world held fixed at September-vintage levels; X_OTHER's 666-vs-941 gap is the PSD world imports/exports statistical discrepancy (MY/TY timing).
- No as-published WASDE vintage CSVs yet: U.S.-side error sds are still v1's stated priors; elasticities are literature-range triangular priors (foreign elasticities are v1-world choices).
