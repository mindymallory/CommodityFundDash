# Monte Carlo v1 — 2026/27 U.S. corn balance sheet

Simulates the distribution of 2026/27 ending stocks, stocks-to-use, and
season-average price from the September 2026 (WASDE #675) starting point.
N = 10,000 draws. Results feed `mc_charts/` (newsletter PNGs) and the
`MC_RESULTS` workbook tab.

## How calibration works

**Full methodology: `monte_carlo/CALIBRATION.md`.** The one-paragraph
version: the model recalibrates **quantities** and holds **parameters**
fixed. Baseline quantities (Q0s) are re-anchored **once per marketing
year** to the September WASDE that opens the year and stay fixed all year
for stability; within the year, new information enters through the weekly
export-commitment demand shifter and the Monte Carlo error draws.
Elasticity priors come from the published literature
(`elasticity-literature-review.md`) and change only when that review is
redone — never on a data refresh. Demand is constant-elasticity,
`Q_i(P) = (Q_i0 + dD_i)·(P/P0)^ε_i`, so a re-anchor moves Q0s without
touching elasticities.

## How to re-run

```bash
cd ~/workspace/your_files/commodity-newsletter-design
python3 -m monte_carlo.run_all
```

`run_all.py` runs the base case plus the −5 bu/acre yield-shock scenario,
writes the four PNGs to `mc_charts/`, prints the summary table, and saves
`mc_results_2026-09-18.json`. The workbook `MC_RESULTS` tab is written by
the same script (values only, labeled, dated).

## Data sources (all from the validated workbook layer — nothing invented)

- `US_Corn_History_and_Pace_v1.xlsx` → `HIST_BALANCE` rows 4–19
  (2010/11–2025/26 finals) and row 20 (2026/27 WASDE #675 projections).
- `fas_corn_weekly_commitment_stage_2007-2026.csv` — 20 years of weekly
  FAS export-commitment history (staged, validated).
- `fas_corn_scurve_windows.csv` — average S-curves; the 20-yr average
  (`avg20_pct`) is the denominator for implied-final residuals.

## Model

**Base case** = WASDE #675 2026/27 Proj: beg. stocks 1,922; production
15,800; imports 25; exports 3,275; ethanol grind 5,600; feed & residual
5,950; non-ethanol FSI 1,355 (held fixed); → ending stocks 1,567;
stocks-to-use 9.69%; price $4.80.

**Per draw:**
1. Draw forecast errors for production, ethanol grind, feed & residual
   (zero-mean normals, stated sds — see below) and exports (empirical
   pace residuals, see below), correlated through the empirical
   correlation matrix.
2. `supply = beg + production + imports`;
   `total_use = exports + ethanol + feed + 1,355`;
   `ending = supply − total_use` (identity asserted per draw);
   `stocks/use = ending / total_use`.
3. Price from the fitted inverse curve `P = a + b/(stocks-to-use)`
   (Westcott-Hoffman form; fitted on 2010/11–2025/26, R² ≈ 0.69).

## Assumptions and known v1 approximations (read before quoting numbers)

1. **No as-published WASDE vintage CSVs yet.** Production, ethanol, and
   feed-&-residual error sds are *stated v1 priors*, not estimated:
   production ±300 M bu (~1.9%), ethanol ±100 (~1.8%), feed & residual
   ±150 (~2.5%). They are placeholders until the vintage pipeline
   (memo §2) exists — the code is structured so real vintage errors drop
   into `ERROR_SD` / `draw_errors` with no other changes.
2. **Export errors are empirical but commitment-based.** Residuals =
   implied-final − actual-final *commitments* at the current FAS week
   (week 2 of 2026/27: only two weeks of live data, so uncertainty is
   honestly huge — sd ≈ 29%). Final commitments ≈ final exports within
   ~±5% (see `fas_scurve_validation.md`), so commitment residuals proxy
   export errors. Residuals are bootstrapped (inverse-CDF), not assumed
   normal.
3. **Correlation matrix is a proxy.** It comes from year-over-year first
   differences of historical *finals*, not from forecast errors (which
   need the vintage CSVs). It captures economic co-movement (big crop →
   bigger use), which is the right sign even if the magnitude is
   approximate.
4. **Beginning stocks (1,922) and imports (25) are fixed.** Beg. stocks
   will be finalized by the Sep 30 Grain Stocks report; v1 does not model
   that revision. Non-ethanol FSI (1,355) is fixed.
5. **Price model is reduced-form, and the left tail is wild.** R² ≈ 0.69 on
   16 observations. The inverse form explodes as stocks-to-use → 0, so
   with week-2 export uncertainty (sd ≈ 29%), ~7% of draws land below 3%
   stocks-to-use and produce absurd prices (single digits negative to
   four figures). These draws are *flagged* (count reported), not
   truncated — but the charts clip display axes and annotate tail mass,
   and the summary leads with P10/P50/P90 (robust) rather than the mean
   (which the tail drags). A real demand-rationing mechanism (price
   chokes off use before stocks hit zero) is the right v2 fix; v1 shows
   you the tail honestly instead.
6. **Median export draw sits ~4% below WASDE — and that's the data
   talking.** Week-2 pace residuals are right-skewed (a few years with
   huge early bookings pull the mean to ~0 while the median is −3.8%),
   so the median draw implies exports ≈ 3,151 vs WASDE 3,275, pushing
   median ending stocks to 1,663 vs WASDE 1,567. This is not a bug: at
   week 2 the pace-implied final *typically* understates the final.
   Lead with the distribution, not the point estimate.
7. **Yield-shock scenario** shifts the production mean by
   −5 bu/ac × 88.5 M harvested ac = −442.5 M bu; error structure
   unchanged.

## Outputs

- `mc_charts/mc_ending_stocks_hist.png` — ending-stocks histogram, P10/P50/P90.
- `mc_charts/mc_price_hist.png` — price histogram, P10/P50/P90.
- `mc_charts/mc_price_vs_stocks.png` — draw cloud + fitted curve + history + WASDE point.
- `mc_charts/mc_scenario_delta.png` — base vs −5 bu/ac shock (P50 price, P50 ending, P(s/u<10%)).
- Workbook tab `MC_RESULTS` — summary stats, labeled, dated.
- `mc_summary_2026-09-18.md` — plain-language results.

## Files

- `config.py` — paths, N, seed, base case, error sds, scenario size.
- `simulate.py` — `run()`: loads inputs, draws errors, propagates identity,
  prices draws, validates, summarizes. `__main__` prints a one-line summary.
- `price_model.py` — fits/applies the stocks-to-use → price curve.
- `charts.py` — the four PNGs.
- `run_all.py` — base + shock runs, charts, JSON, workbook tab.

---

# Monte Carlo v2 — structural supply/demand (2026-09-18)

Re-run: `cd ~/workspace/your_files/commodity-newsletter-design &&
python3 -m monte_carlo.run_structural`. Writes four PNGs
(`mc_charts/mc_structural_*.png`), the `MC_STRUCTURAL` workbook tab, and
`mc_structural_results_2026-09-18.json`.

## The economics, in plain language

Within one marketing year, corn supply is predetermined (the crop is made).
So the season-average price is whatever makes **total demand equal supply**:

> Q_exports(P) + Q_ethanol(P) + Q_feed(P) + Q_food/seed/other(P) + Q_stocks(P) = Supply

Each demand curve has constant-elasticity form
`Q_i(P) = Q_i0 · (P/$4.80)^ε_i`, anchored at WASDE #675's $4.80 price. The
fifth curve, Q_stocks, is the market's *demand to carry grain* — without it,
price clearing would force ending stocks to zero by construction. (The v2
build spec's literal equation summed only the four use categories; that was
corrected here, because ending stocks must remain a positive economic
quantity. The memo's price-flexibility form ΔP/P ≈ (ΔS/S)/Σ(share·ε) is then
exact in the limit, with stocks' share included.)

**What a shock does, step by step** (−5 bu/acre = −442.5 M bu of supply):
1. Supply shifts left by 442.5 M bu. At the old price, demand exceeds supply.
2. Price rises. Every demand curve slides up its schedule; the most
   price-sensitive (exports, ε ≈ −1.0) gives up the most quantity, the least
   sensitive (food/seed/other, ε ≈ −0.175) barely moves.
3. Price stops rising when total demand has fallen by exactly 442.5 M bu.
   Ending stocks — the stock-demand curve's quantity at the new price — falls
   by only ~74 M bu; demand rationing absorbs the rest.
4. A demand shock works the same way in reverse: +200 M bu of export demand
   shifts that curve right; price rises until the other curves (plus a
   smaller net export gain) give back 200 M bu.

## Per-draw mechanics

1. **Elasticities** drawn from triangular literature priors (independent per
   category; all symmetric, so median = mode):
   | Category | lo | mode | hi | source |
   |---|---|---|---|---|
   | Exports | −1.2 | −1.0 | −0.8 | memo §4: short-run ≈ −1.0 (corn/soy) |
   | Feed & residual | −0.5 | −0.35 | −0.2 | memo §4: feed −0.2 to −0.5 |
   | Ethanol grind | −0.5 | −0.375 | −0.25 | **v2 choice** — memo didn't pin ethanol |
   | Food/seed/other | −0.25 | −0.175 | −0.1 | memo §4: wheat food −0.1 to −0.25 (proxy) |
   | Stocks (carry demand) | −1.5 | −1.0 | −0.5 | **v2 choice** — memo silent |
2. **Baseline quantity uncertainty** reuses v1's error machinery unchanged:
   production ±300 / ethanol ±100 / feed ±150 M bu normals, exports from the
   empirical week-2 pace-residual bootstrap, correlated through v1's
   first-difference correlation matrix. Each line's error shifts that line's
   schedule at $4.80 (production → supply; use lines → their demand curves);
   the stock-demand baseline stays fixed at the WASDE 1,567 M bu. These are
   still v1's empirical/stated priors until real WASDE-vintage errors exist.
3. **Shock** applied per scenario preset (`structural_config.py`):
   `base` (none), `yield_minus5` (dS = −442.5 M bu),
   `export_surge` (export demand +200 M bu).
4. **Solve** Σ Q_i0·(P*/4.80)^ε_i = S1 by bisection on log-price, bracket
   [$0.50, $50] with adaptive expansion. Ending stocks = stock demand at P*;
   the identity supply ≡ use + ending holds by construction and is asserted
   per draw.

## v1 vs v2 — honest comparison

**v1** (files `config.py`, `simulate.py`, `price_model.py`, `charts.py`,
`run_all.py` — **superseded but intact, still re-runnable**): drew correlated
forecast-error residuals, pushed them through the balance-sheet identity with
use fixed, and priced each draw off the fitted inverse curve
P = a + b/(stocks-to-use), R² ≈ 0.69 on 16 observations. No shock propagation
through demand — a yield cut came 100% out of ending stocks, and the inverse
curve explodes as stocks-to-use → 0, so ~7% of draws produced absurd prices
(the documented left-tail pathology).

**v2** (files `structural_config.py`, `structural.py`,
`structural_charts.py`, `run_structural.py`): keeps v1's error machinery for
baseline uncertainty but replaces the pricing with structural demand
rationing. Extreme draws now behave economically — price rises, use falls,
stocks stay positive. v1's fitted curve survives only as a diagnostic
overlay (`mc_structural_price_vs_stocks.png`); it is never used for pricing.

Same −5 bu/acre shock: v1 → P50 $5.87 / ending 1,214 / P(s/u<10%) = 72.3%;
v2 → P50 $4.99 / ending 1,509 / P(s/u<10%) = 71.4%. v1 dumps the whole cut
into ending stocks and prices off the curve's steep low-s/u region; v2 rations
demand so ending stocks fall only ~74 M bu and the clearing price rises
~$0.24. Both agree the shock raises sub-10% odds to ~71–72%.

## Validation (run_structural prints all of these)

- **Solver convergence:** 100% of draws, all scenarios (fixed 120 bisection
  iterations/draw; max residual 4.4e-16 of supply).
- **Identity:** max |supply − (use + ending)| = 7.3e-12 M bu across all draws.
- **Flexibility cross-check:** at uniform ε = −0.05 with a −1 bu/acre shock,
  the solver's log-price matches the exact flexibility solution
  z = ln(S1/S0)/ε to 7.6e-16. The memo's first-order ΔP/P form is within ~5%
  (the gap is the e^z−1 vs z second-order term, shrinking for small shocks).
- **Scenario ordering:** bigger cut → higher price (shock curve is monotone
  −10 to +5 bu/ac); waterfall split of the 442.5 M bu cut at median
  elasticities: exports 155, ethanol 101, feed 100, FSI 11, ending stocks 74 —
  exports absorb ~14× food/seed/other, as elasticities predict.

## Known v2 approximations

1. Stock-demand elasticity (−0.5 to −1.5, mode −1.0) and ethanol elasticity
   are v2 choices, not memo literature values — flagged in the priors table.
2. The v2 spec's literal clearing equation was corrected to include stock
   demand (see above); without it ending stocks would be identically zero.
3. Error sds/priors are still v1's (see v1 assumptions); elasticities are
   drawn independently across categories (no cross-category correlation).
4. Base-case P(s/u<10%) = 61.5% is high because week-2 export-demand
   uncertainty (sd ≈ 29%) is honestly huge — large positive export draws
   tighten the sheet hard. It falls as pace data firms up.

---

# Monte Carlo v3-world — global extension (2026-09-18)

Re-run: `cd ~/workspace/your_files/commodity-newsletter-design &&
python3 -m monte_carlo.run_global`. Writes three PNGs
(`mc_charts/mc_global_*_v4.png`), the `MC_GLOBAL` workbook tab (+ CHANGELOG
row), `mc_global_results_2026-09-18_v4.json`, and
`mc_global_summary_2026-09-18_v4.md`. (v3 files kept alongside.)

## The economics, in plain language

The v2 U.S. structural model is kept intact — four domestic demand curves
plus stock demand, all constant-elasticity anchored at $4.80. What changes is
**where the export demand curve comes from**. In v2, U.S. export demand was
a fixed curve (elasticity −1.0) with a big slug of week-2 pace uncertainty.
In v3-world, U.S. exports are the **residual** of the world market:

> The world wants M_ROW(P) + M_CH(P) of imports. Brazil, Argentina, and
> Ukraine supply XS_BR(P) + XS_AR(P) + XS_UP(P) — each upward-sloping in
> price, because a higher price rations their domestic use and frees grain
> for export. About 666 M bu goes to all other exporters (fixed). Whatever
> import demand is left over is U.S. export demand.

A Brazil bumper (+500 M bu of safrinha) shifts Brazil's export supply right;
the U.S. residual export curve shifts *down* by ~500 M bu at every price; the
U.S. price falls until domestic demand plus the smaller residual exports
absorb it. A China import surge (+200 M bu) shifts world import demand
right; the residual curve shifts *up*; the U.S. price rises. The U.S. is the
world's residual supplier in both directions — which is why the drought
scenario hands the U.S. +291 M bu of exports and the bumper takes away 293.

## Data sources

- `psd_corn_world_stage_2026-09-18.csv` — USDA FAS PSD, September 2026
  vintage, staged from frozen raw pulls in `raw/psd_corn_2026-09-18/`
  (one file per country-year, vintage_month=09). All 2026/27 country
  identities verified at staging (supply ≡ use + ending).
- 2026/27 anchors (M bu): BR beg 583 / prod 5472 / imp 71 / dom 4016 /
  end 417; AR 185 / 2165 / 0 / 697 / 158; UP 112 / 1252 / 0 / 283 / 215;
  China imports 197 / domestic use 12755; world imports 7996 / exports
  8271. U.S. side is the v2 config unchanged (WASDE #675: beg 1922, prod
  15800, imp 25, exp 3275, eth 5600, feed 5950, FSI 1355, ending 1567,
  P0 = $4.80).
- Brazil safrinha ≈ 78% of its crop is narrative context only — PSD does
  not split first vs. safrinha crops.

## Competitor-supply timing rule (Mindy, 2026-09-18)

**No H1/H2 split of the marketing year.** For a US marketing year
(Sep–Aug), competitor *production* = the harvests that land/ship during
**our** window, whatever local marketing year USDA files them under.
Full table: `competitor_my_mapping_2026-09-18.csv`; machine-readable map:
`world_config.COMPETITOR_MY_MAP`. For US MY 2026/27 (Sep 2026–Aug 2027):

| Competitor | Local MY used | Harvests in our window | Anchor (M bu) |
|---|---|---|---|
| BR | 2027/28 (Mar–Feb) | first crop Feb–Apr 2027 + safrinha Jun–Aug 2027 | 5472.2 (proxy) |
| AR | 2027/28 (Mar–Feb) | Mar–Jun 2027 | 2165.2 (proxy) |
| UP | 2026/27 (Oct–Sep) | Sep–Nov 2026 | 1251.9 (staged) |

The safrinha harvested Jun–Aug 2027 is USDA-filed under BR local MY
2027/28 but competes with our 2026/27 balance sheet, so it counts here.
USDA had not published BR/AR local-MY 2027/28 estimates in the Sep-2026
vintage, so those anchors are the latest observed productions used as
no-change expectation proxies (flagged, not hidden). beg/imp/dom/end stay
at September-vintage local-MY levels: the competitor block is an annual
exportable-surplus identity, and a true Sep–Aug balance sheet would need
monthly data PSD does not publish. Anchors are numerically unchanged, so
the residual-curve calibration through the WASDE point ($4.80, 3275) holds
exactly as before.

Consequence: BR/AR production competing with our 2026/27 is **entirely
forward** (unplanted in Sep 2026), so baseline sds are forward
uncertainties now — BR 385 / AR 260 M bu (detrended 2018–2026 historical
volatility), UP 80 M bu (its Sep–Nov 2026 harvest is being cut now, nearly
final). The ±500 M bu Brazil scenarios (~1.3 sd) are the named
forward-safrinha scenarios: bumper = big safrinha, drought = failed
safrinha.

## Per-draw mechanics

1. **U.S. side** reuses v2's machinery exactly (same seeds, so
   `base_global`'s U.S.-side draws *are* v2 base's draws): production /
   ethanol / feed errors from v1's correlated priors, domestic elasticities
   from the same triangular draws (the export column is discarded).
   **The export pace-residual draw is dropped** — exports are endogenous
   now, so nothing in the model needs a week-2 export guess.
2. **Competitor production draws**: BR/AR/UP sds 385/260/80 M bu. Under
   the timing rule, BR/AR production competing with our 2026/27 is entirely
   forward (unplanted in Sep 2026), so sds are forward uncertainties =
   detrended 2018–2026 historical volatility (resid sds BR 384, AR 258);
   UP's Sep–Nov 2026 harvest is being cut now, so its sd stays 80. BR–AR
   correlation 0.5 (shared Southern-Hemisphere weather — more defensible
   now that both are forward crops), UP independent, truncated at ±3 sd.
   The ±500 M bu Brazil scenarios (~1.3 sd) are the named forward-safrinha
   scenarios, not the baseline draws.
3. **Competitor export supply**:
   `XS_i(P) = max(0, beg_i + prod_draw_i + imp_i − dom_i(P) − floor_i − kval_i)`,
   `dom_i(P) = dom_i0·(P/P0)^ε`, ε ~ triangular(−0.3,−0.2,−0.1)
   (v1-world choice). `floor_i = 0.05·dom_i0` (pipeline stocks);
   `kval_i = end_i0 − floor_i` is competitor carry demand, held fixed
   across prices — a documented v3-world choice, needed so XS_i(P0)
   equals observed exports and the residual curve passes through the
   WASDE point ($4.80, 3275) exactly.
4. **World import demand** (China broken out):
   `M_ROW(P) = 7799·(P/P0)^ε_ROW`, ε_ROW ~ triangular(−0.6,−0.4,−0.2);
   `M_CH(P) = 197·(P/P0)^ε_CH`, ε_CH ~ triangular(−0.9,−0.6,−0.3)
   (v1-world choices); per-draw multiplicative anchor noise 4% / 15%.
5. **Residual U.S. export demand**:
   `X_US(P) = M_ROW(P) + M_CH(P) − XS_BR − XS_AR − XS_UP − X_OTHER`,
   X_OTHER ≈ 666 M bu calibration constant. The 666-vs-941 gap to implied
   other-exporter exports (8271 − 7329 = 941) is the PSD world
   imports/exports statistical discrepancy (8271 − 7996 = 275, MY/TY
   timing): X_OTHER is anchored to world *imports*, the demand the
   residual curve clears against.
6. **Clear** Σ domestic Q(P) + X_US(P) = S_US by bisection on ln(P/P0)
   (X_US decreasing in P ⇒ unique root). Ending stocks = stock demand at
   P*; U.S. and world identities asserted per draw (world: modeled
   US/BR/AR/UP + rest-of-world fixed at September-vintage levels, ROW
   ending defined residually).

## China allocation rule

Two separate questions, two separate answers:

- **Level** (who sells China its total buys): logit shares on landed cost
  — FOB spread vs US Gulf plus freight to China, per-draw spread noise
  sd 0.10. Spread centers come from the weekly freight monitor
  (`monte_carlo/freight.py`, `INTEGRATION_SPEC_FREIGHT.md`) when
  `FREIGHT_LIVE` is True, with per-leg fallback to the static priors
  (BR −0.25, AR −0.20, UP −0.45, US 0.0; freight US 0.55, BR 0.45,
  AR 0.50, UP 0.65) whenever a leg is stale, a proxy, or missing. This is
  "pool" accounting on top of clearing; it does not feed back into prices.
- **Marginal** (who supplies the +200 M bu surge): structural — compare
  equilibrium exports by origin, surge vs base. No logit involved.

**Calibration finding, reported honestly:** as of the week ending
2026-09-16, the BR leg is LIVE on its 28-day fixture-mean leg
(`FREIGHT_MAX_VINTAGE_DAYS` = 35 — Mindy's 2026-09-18 decision that the
monitor's fixture-mean legs are 4-week means by construction, so 35 days
keeps them live across weekly refreshes, apples-to-apples) and the US leg
runs on the ESTIMATED PNW leg `US_PNW_EST` (Mindy's 2026-09-18 decision:
no public PNW→China fixture newer than Aug 4, 2026 exists — 45 days stale
vs the 35-day gate, all GTRs through 09/17/2026 checked — so a direct
quote cannot go live; the direct Gulf→PNW fixture regression was tried
and failed (only 2 co-occurring pairs in 5.75 years of GTRs). Instead:
live GTR Table 1 PNW→Japan weekly ($37.75/mt) + estimated China premium
−0.96 $/mt from 8 PNW→China fixtures 2021–2026 (sd 2.11, no trend/level
dependence, OLS slope 0.98 ≈ 1, holdout OOS RMSE 0.34) = $36.79/mt,
prediction SE $2.24/mt. Full methodology: `freight_pnw_proxy.md`.).
The leg is a MODELED NUMBER, not a quote: flagged "estimated" in the
staged CSV (origin `US_PNW_EST`), in the results JSON
`freight_basis.estimated_legs`, and in the FREIGHT tab — never presented
silently as live. With PNW as the US basis the US is competitive into
China again (landed ~$6.93/bu vs $8.29 on the old Gulf basis), which
matches the economics: the PNW is the shorter Asia route for corn (the
Gulf is mainly a soybean-to-China artery). **v9 (2026-09-18): China
share target reset to recent actuals.** The old [0.25, 0.45] US-share
band was a 2020/21–2022/23 boom-era number; China's US-corn buying
collapsed after 2023 (Brazil took the trade; China's total imports shrank
to ~4–5 MMT). Reset per Mindy to the trailing-3MY actual US share of
China's corn imports from USDA FAS PSD — MY2023/24: 9.9%, MY2024/25:
1.5%, MY2025/26: 0.0% (avg 3.8%; band (0.00, 0.14) = avg ± 10pts floored
at zero; recomputed each September). `calibrate_china_lambda()` now
targets the new 0.038 midpoint instead of hardcoded 0.35, and the
calibrated lambda is **wired into the simulation** (`WC.CHINA_LAMBDA`) —
previously the calibration was print-only and the model always ran at the
1.0 placeholder (found and fixed in v9). Lambda now calibrates to the
**4.0 upper grid boundary** (baseline shares US 13.5 / BR 2.6 / AR 33.7 /
UP 50.2; per-draw means 14.2 / 2.7 / 33.8 / 49.3): inside the wide
0–14% band, but pinned at the grid edge — extending the grid is an open
follow-up. Scenario P50s are bit-identical to v8 (allocation is level
accounting; clearing untouched); marginal +200 M bu surge capture
unchanged (US 57.9%). Full methodology: `monte_carlo/CALIBRATION.md`.

## Seasonality treatment

This is a **full-year clearing model** — Mindy explicitly ruled out an
H1/H2 split of the marketing year (2026-09-18). Instead, the timing rule
above assigns each competitor's *harvests* to our Sep–Aug window: the
Jun–Aug 2027 safrinha (USDA-filed under BR local MY 2027/28) competes with
our 2026/27 balance sheet, so it counts in our 2026/27. The
`h2_brazil_bumper` / `h2_brazil_drought` presets use the *same* ±500 M bu
mechanics as `brazil_bumper` / `brazil_drought` (verified bit-identical);
the h2 labels are kept only for the newsletter's seasonal framing. No
separate mechanism exists and none is faked.

## Named scenarios (10,000 draws each, seeded/deterministic)

v8 = US leg on ESTIMATED PNW basis (2026-09-18): `FREIGHT_US_PORT` GULF →
PNW_EST per Mindy's decision — adopt the estimated PNW leg (flagged
"estimated" everywhere, never a quote). Proxy = live GTR Table 1
PNW→Japan $37.75/mt (wk ending 2026-09-16) + estimated China premium
−$0.96/mt (n=8 fixtures 2021–2026, sd 2.11, no trend/level dependence,
OOS RMSE 0.34; see freight_pnw_proxy.md) = $36.79/mt, SE $2.24
(~$0.06/bu — inside the existing per-draw spread noise sd 0.10 $/bu, so
no extra noise term). `FREIGHT_ALLOW_ESTIMATED_PNW` = True gates the leg;
`_live_legs` now uses the true PNW FOB spread (−0.41 $/bu vs Gulf) instead
of forcing US = 0.0 (that forcing was a no-op on the Gulf basis but would
have biased the PNW basis by the full FOB discount — removed). Live legs:
BR; estimated: US; fallback: AR, UP. China's level allocation: US 23.3% /
BR 15.3% / AR 29.1% / UP 32.3% (was v7: 7.2 / 18.5 / 35.3 / 39.0) — the
US recovers from 7.2% to 23.3% because the PNW is the shorter Asia route.
Marginal surge capture unchanged (US 57.9 / BR 7.8 / AR 1.4 / UP 0.6 —
structural market clearing, not the logit). P50 scenario
prices/exports/ending stocks are IDENTICAL to v7 (allocation is level
accounting; clearing unchanged). Workbook: MC_GLOBAL tab + FREIGHT tab
(placeholder filled in) + CHANGELOG row; JSON `freight_basis` now carries
`estimated_legs`. Chart: `mc_charts/mc_freight_pnw_premium.png`.

v7 = US leg on live Gulf basis (2026-09-18): `FREIGHT_US_PORT` PNW → GULF
per Mindy's decision — no public PNW→China fixture newer than Aug 4, 2026
exists (45d stale vs the 35d gate; GTRs through 09/17/2026 checked), so
PNW cannot go live; Gulf→China IS live weekly ($74.5/mt fixture mean).
Live legs: US, BR; AR/UP on static fallback. China's level allocation:
US 7.2% / BR 18.5% / AR 35.3% / UP 39.0% (was v6: 22.9 / 15.4 / 29.3 /
32.4) — the Gulf basis makes the US the priciest origin into China
($8.29/bu landed), honest for Gulf corn but flattering competitors vs a
PNW basis (the Gulf is mainly a soybean-to-China artery; PNW is the
shorter Asia route for corn). Marginal surge capture unchanged (US 57.9 /
BR 7.8 / AR 1.4 / UP 0.6 — marginal capture is structural market clearing,
not the logit). P50 scenario prices/exports/ending stocks are IDENTICAL
to v6 (allocation is level accounting; clearing unchanged).

v6 = BR freight leg live (2026-09-18): `FREIGHT_MAX_VINTAGE_DAYS` 14 → 35
per Mindy's decision that 4-week fixture means count as live data
(apples-to-apples). Week ending 2026-09-16: BR live on its 28-day fixture
mean; US/AR/UP on static fallback. China's level allocation shifts to
US 22.9% / BR 15.4% / AR 29.3% / UP 32.4% (was 19.6 / 27.7 / 25.0 / 27.7);
marginal surge capture unchanged (US 57.9 / BR 7.8 / AR 1.4 / UP 0.6 —
marginal capture is structural market clearing, not the logit). P50
scenario prices/exports/ending stocks are IDENTICAL to v5 (allocation is
level accounting; clearing unchanged).

v5 = live-freight wiring (2026-09-18): the China/ROW logit now reads the
weekly freight monitor's landed-cost legs with per-leg static fallback
(`INTEGRATION_SPEC_FREIGHT.md`). Week ending 2026-09-16: all four legs on
fallback (BR fixture-mean leg 28d old vs the 14d max-vintage gate; US_PNW
stale assumption; AR proxy; UP no freight leg) — so v5 scenario numbers
are IDENTICAL to v4 (verified: all P50s and tail odds match to the last
decimal). The hook is live; fresh fixture weeks will move the allocation.
Each run's `freight_basis` (live vs fallback legs) is recorded in the
results JSON.

v4 = timing-rule update (2026-09-18): BR/AR competitor production is now the
forward harvests landing in our Sep–Aug window, with forward-uncertainty
sds (385/260 M bu). P50s are essentially unchanged (same median anchors);
tails widen; P(s/u<10%) falls in most scenarios — with constant-elasticity
demands, a bearish competitor draw loosens U.S. stocks *more* than a
symmetric bullish draw tightens them (quantity responses are convex in
price), so extra competitor variance fattens the loose tail more than the
tight one. The bumper exception (+6.9 pp): there the competitor export
floor never binds, so the extra variance is symmetric and adds tight-US
tail mass.

| Scenario | Shock | P50 price | P50 US exports | P50 ending | P(s/u<10%) | Δ vs v3 P(s/u<10%) |
|---|---|---|---|---|---|---|
| base_global | none | $4.80 | 3,277 | 1,567 | 68.4% | −9.9 pp |
| brazil_bumper | BR prod +500 | $4.57 | 2,986 | 1,642 | 38.8% | +6.9 pp |
| brazil_drought | BR prod −500 | $5.04 | 3,567 | 1,494 | 89.2% | −9.0 pp |
| china_surge | China imports +200 | $4.89 | 3,392 | 1,538 | 78.0% | −12.5 pp |
| h2_brazil_bumper / h2_brazil_drought | same ±500, H2 label | identical to above | | | | |

(v3 numbers for reference: base 78.3%, bumper 31.9%, drought 98.2%,
surge 90.5%; P50s unchanged to within 1¢ / 3 M bu.)

China surge marginal capture (Δ equilibrium exports / 200): US 57.9%
(116 M bu), BR 7.8% (16), AR 1.4% (3), UP 0.6% (1). Sums to ~68%, not
100%: the higher clearing price rations ~60 M bu of rest-of-world import
demand, so only ~140 M bu of extra exports are needed. The U.S., as
residual supplier, absorbs most of the remainder; competitor export supply
is price-inelastic here (crops fixed — only domestic rationing responds).

## v2-vs-global comparison (base)

Same U.S.-side draws (identical seeds); only the export demand mechanism
changes, so deltas isolate curve-shape effects:

| | v2 base | global base | Δ (global − v2) |
|---|---|---|---|
| P50 price | $4.75 | $4.80 | +$0.05 |
| P50 US exports | 3,203 | 3,276 | +73 M bu |
| P(s/u<10%) | 61.5% | 78.3% | +16.9 pp |

P(s/u<10%) **rises**, contrary to the naive expectation: dropping the
±29% export pace-residual draw removes variance, but the residual curve is
anchored at the WASDE 3275 export level while v2's median week-2 pace draw
sat ~4% below it (~3,203) — week-2 pace typically understates final
exports. The level effect dominates: the global distribution is tighter
but centered on a tighter sheet. The residual curve is also slightly more
elastic than v2's fixed −1.0 curve (effective ≈ −1.3 at P0: import-demand
elasticity *plus* competitor export-supply response).

## Validation (run_global prints all; fails loudly otherwise)

- Solver convergence 100% of draws, all scenarios (120 bisection
  iters/draw; max residual ~4e-16 of supply).
- U.S. identity max |S−(use+ending)| ~7e-12 M bu; world identity
  ~1.5e-11 M bu, all draws.
- U.S. exports ≤ world imports on every draw (holds by construction:
  X_US = M − XS − X_OTHER, XS ≥ 0, X_OTHER > 0).
- Ordering: bumper → lower P50 price *and* lower P50 US exports than base;
  drought → higher price; china_surge → higher price.
- Calibration: residual curve hits ($4.80, 3275) at median parameters
  exactly; competitor XS_i verified increasing in P numerically.

## Known v3-world approximations

1. Foreign elasticities (domestic −0.3..−0.1, ROW import −0.6..−0.4,
   China import −0.9..−0.6) are v1-world choices, not memo literature.
2. Competitor carry demand fixed at September-vintage ending stocks (the
   `kval` term); competitor ending stocks therefore don't respond to
   price — only domestic rationing slopes their export supply.
3. Rest-of-world (all countries beyond US/BR/AR/UP) is fixed at
   September-vintage levels; only the four modeled countries are
   stochastic.
4. China logit shares are level accounting with a pool assumption — no
   bilateral contract structure, no policy wedges (tariffs/quotas).
5. Full-year clearing; no H1/H2 split (Mindy's rule) — competitor harvests
   are assigned to our Sep–Aug window instead. H2 preset labels are
   seasonal framing only.
6. U.S.-side error sds are still v1's stated priors (no WASDE vintage
   CSVs yet); residual U.S. exports can in principle go negative in
   extreme high-price draws (none observed — 0 of 60,000 draws).

---

# Export error v3 — demand-curve-consistent (2026-09-18)

Module: `monte_carlo/export_errors.py`. Re-run / validate:
`python3 -m monte_carlo.export_errors` (prints 8 checks, saves 3 charts to
`mc_charts/mc_export_errors_*.png`). **Not yet wired into
`structural.py`** — see `INTEGRATION_SPEC.md` for the exact diffs (a
separate build is touching those files).

## The economics, in plain language

The old export error compared this year's bookings to the
historical-average booking pace and called the difference "demand
surprise." But booking pace itself responds to price: when prices are high,
importers panic-book early (2012/13); when prices are low, they dawdle.
So the old "error" was half price signal — regressing it on the
season-average price gives t = +3.7, p = 0.0025, R² = 0.52. It was reading
movement *along* the demand curve as *shifts of* the curve, and then the
structural model applied the price elasticity a second time.

The fix measures the error against the model's own demand curve:

1. **Estimate the curve honestly.** Log exports on log price is biased
   (demand shocks push both up), so price is instrumented with supply
   shocks — yield deviation from trend × harvested acres, i.e. weather.
   First stage F = 13.3 (strong). OLS says elasticity −0.68 (biased toward
   zero, as theory predicts); IV says −1.27 ± 0.49 — right on top of the
   literature mode −1.0, which stays the working value with IV as the
   cross-check.
2. **Recover genuine demand shifters** Â_t = X_t / P_t^ε. Dividing out the
   price effect leaves pure demand-curve shifting.
3. **Purge the pace-price channel from the week-w inference.** Booking pace
   follows s_{y,w} = sbar_w · (P/Pbar)^γ_w, with γ_2 = +0.87 (t = 3.6,
   significant; fading to insignificance by week 26). The inference is
   Â̂ = C_w / [sbar_w · φ_w(P_cur)] / P_cur^ε, and the error distribution
   is the empirical purged log inference errors e* across 15 clean final
   years (2010/11–2024/25; 2025/26 excluded as provisional).

## What changed numerically

- Week-2 error sd: **33% → 22%** (purging price removes spurious variance).
- Bands tighten by week: 22% → 19% → 14% → 10% → ~3% at weeks
  2/8/16/26/53 (fitted decay sd(w) = 0.252·exp(−0.041·w)), so re-running
  with a larger `CURRENT_WEEK` automatically narrows the bands.
- Worst-contaminated year, 2012/13: old method read a **+87%** demand
  shock; purged method says **+28%** (real fear-buying, not a phantom).
- Synthetic check: a pure +50% price spike with no demand shift leaves
  inferred Â'/Â = **1.0000** under the new method; the old method invents
  a demand shock ranging **−27% to +38%** across years.
- Current read (2026/27, week 2): purged inference implies **~2,707 M bu**
  of exports at $4.80 vs the WASDE 3,275 anchor — the pace data says export
  demand is running softer than WASDE. Report the divergence; don't smooth
  it away.

## Known approximations

- n = 15: the IV standard error (±0.49) is wide; the literature mode is the
  working elasticity, not the IV point estimate.
- γ_w is estimated per week from the same 15 years; insignificant from
  week 26 on (the purge then does nothing — correct behavior).
- The purged errors are bootstrapped raw (mean −3.3% at week 2 preserved,
  not recentered) — same convention as the old code; the bias is reported,
  not hidden.
- Export demand shifts are drawn independently of prod/ethanol/feed errors
  (the old first-difference correlation matrix embedded price responses and
  is deliberately not carried over).

---

# Freight monitor — weekly landed costs (2026-09-18)

Module: `monte_carlo/freight.py`. Refresh (one command):

```bash
cd ~/workspace/your_files/commodity-newsletter-design
python3 -m monte_carlo.freight
```

Discovers the latest GTR issue from the AMS landing page, downloads the
frozen raws into `raw/freight_<date>/`, parses fixtures + FOB, and appends
one staged week to `freight_landed_stage_<date>.csv`. Re-run weekly;
Thursday (GTR release day) is the natural slot.

## Why it exists

`world.py`'s China/ROW logit ran on static FOB spreads and freight
(`CHINA_FREIGHT US 0.55 $/bu`) — about 3.4x stale vs the current
Gulf→China fixture mean ($74.5/mt = $1.89/bu). That staleness is the
documented China-calibration miss. The monitor replaces the guess with a
weekly feed; see `INTEGRATION_SPEC_FREIGHT.md` for the exact wiring diffs
(another agent owns `world.py`).

## Sources (all verified live 2026-09-18; nothing faked)

**Weekly, automated:**
- USDA AMS Grain Transportation Report, Table 20 "Ocean freight rates for
  selected shipments" (source: Maritime Research, Inc.) — per-fixture
  rates incl. **Brazil→China** and US Gulf/PNW→China heavy-grain fixtures.
  Parsed from the weekly GTR PDF (latest issue auto-discovered from
  https://www.ams.usda.gov/services/transportation-analysis/gtr).
- USDA AMS GTR Table 1 dataset (`GTRTable1.xlsx`, same page) — weekly
  US Gulf / PNW ocean rates to Japan, full history back to 2002. Used for
  the Japan legs directly.
- USDA FAS "Grain: World Markets and Trade" monthly circular
  (https://apps.fas.usda.gov/psdonline/circulars/grain.pdf) — IGC export
  FOB bids: US 3YC Gulf, Brazil Paranaguá, Argentina Up River, Ukraine.

**Slower / manual (vintages recorded, staleness flagged, never shown live):**
- Argentina→China ocean: no public fixture feed; proxied from the
  Brazil→China fixture mean, flagged `proxy`.
- Ukraine→China ocean: no public feed and no defensible proxy — staged as
  n/a until a human enters a leg in
  `raw/freight_<date>/freight_manual_legs.csv`.
- Ukraine FOB: IGC stopped quoting 2026-09-01; last quote (2026-08-07,
  $223/mt) carried and flagged stale.
- PNW corn FOB is not quoted by IGC: estimated as Gulf FOB − $16/mt,
  flagged `assumption` (ranking robust to ±$10/mt — see below).
- Baltic Panamax index (daily, time-charter basis): subscription-only at
  source; recorded as a manual cross-check input, not an automated feed.
  Latest noted: 2,251 on 2026-09-18 (Reuters). Directional check only —
  a Baltic spike should show up in fixtures 2–4 weeks later.
- Mexico (Veracruz): no ocean fixtures published; US→Mexico corn moves
  largely by rail (GTR Table 8 tariffs — a future upgrade, not wired).

## Current read (week ending 2026-09-16)

Landed cost into China, $/mt (FOB + freight):

| origin | landed | FOB | freight | status |
|---|---|---|---|---|
| Argentina (proxy frt) | 270 | 219 | ~51 | proxy |
| US PNW | 271 | ~236 | 35 | assumption + stale fixture |
| Brazil | 289 | 238 | 51 | live |
| US Gulf | 327 | 252 | 75 | live |
| Ukraine | n/a | 223 (stale) | n/a | data gap |

**The US Gulf is the most expensive origin into China by ~$38/mt**; the
US PNW is at the cheap end, effectively tied with Argentina. Whether "the
US" is least- or most-cost depends on the coast — the monitor therefore
tracks both, and the integration spec exposes `FREIGHT_US_PORT` so the
logit can use either. Ukraine has no computable landed cost until its
freight leg exists; that gap is shown, not filled.

**v7 basis choice (Mindy, 2026-09-18):** the model now uses the GULF leg
for "US" (`FREIGHT_US_PORT="GULF"`). PNW was preferred (shorter Asia
route for corn), but the freshest public PNW→China fixture is Aug 4, 2026
($35.00/mt, heavy grain, GTR Table 20) — 45 days stale vs the 35-day
gate, and no newer PNW→China fixture appears in any GTR through
09/17/2026 (checked all four latest issues fixture-by-fixture). PNW→Japan
IS fresh weekly ($37.75/mt, Table 1) but is a different destination and
cannot proxy China without an invented adjustment. Baltic Panamax at
2,251 (Sep 18, Reuters) is softening — no tightness to explain the gap;
Maritime Research simply hasn't reported a newer PNW→China fixture.
Revisit PNW if a fresh fixture appears.

## Outputs

- `freight_landed_stage_<date>.csv` — staged weekly rows: week_ending,
  origin, destination (CN/JP/MX), FOB + vintage + source, freight +
  vintage + source + method, landed $/mt and $/bu, flag column
  (`proxy`/`assumption`/`stale`/`n/a`).
- `mc_charts/mc_freight_landed_china.png` — current ranking, FOB vs
  freight stacked, flags annotated.
- `mc_charts/mc_freight_ocean_history.png` — Gulf/PNW→Japan weekly rates
  since 2020 (Table 1 history).
- `raw/freight_<date>/` — frozen inputs (GTR PDFs, Table 1 xlsx, FAS
  circular, manual legs template), per the archive rule.
- `get_landed_costs(dest)` — API for `world.py`; returns $/bu legs with
  vintage/staleness metadata (see integration spec).

## Known approximations

1. Fixture means are trailing-28-day entry-date averages; thin weeks
   (e.g. one Brazil→China fixture) are still reported, with n shown.
2. "Heavy grain" fixtures proxy corn freight (standard GTR convention).
3. PNW FOB = Gulf − $16/mt assumption; sensitivity ±$10/mt does not change
   the ranking (PNW still beats/ties Brazil; Gulf still most expensive).
4. Argentina freight proxy = Brazil→China mean (similar voyage length);
   replace with a GAIN/Conab figure when one is in hand.
