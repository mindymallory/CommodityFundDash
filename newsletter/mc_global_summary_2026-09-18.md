# Monte Carlo v3-world (global) — results summary (2026-09-18)

The v2 U.S. structural model is kept intact; v2's fixed export demand curve is replaced by a **residual export demand curve** built from a world module: the world wants `M_ROW(P) + M_CH(P)` of imports, Brazil / Argentina / Ukraine supply `XS_i(P)` (upward-sloping in price through domestic demand rationing), a fixed ~666 M bu goes to other exporters, and the U.S. gets the residual. 10,000 draws per scenario, seeded and deterministic.

## Headline numbers (P50)

| Scenario | U.S. price ($/bu) | U.S. exports (M bu) | Ending stocks (M bu) | P(s/u<10%) |
|---|---|---|---|---|
| Base (global) | 4.80 | 3276 | 1567 | 78.3% |
| Brazil bumper (+500 M bu) | 4.57 | 2983 | 1642 | 31.9% |
| Brazil drought (-500 M bu) | 5.04 | 3567 | 1495 | 98.3% |
| China surge (+200 M bu) | 4.89 | 3391 | 1538 | 90.0% |
| H2 Brazil bumper (+500 M bu) | 4.57 | 2983 | 1642 | 31.9% |
| H2 Brazil drought (-500 M bu) | 5.04 | 3567 | 1495 | 98.3% |

## What the scenarios say

- **Brazil bumper (+500 M bu, the forward safrinha):** U.S. price −$0.23 to
  $4.57, U.S. exports −293 M bu to 2,983. Brazil's extra bushels mostly
  displace U.S. exports rather than collapsing the price — the residual
  demand curve is fairly elastic (~−1.3), so a 500 M bu rival-supply shock
  costs the U.S. about 60% of it in lost exports. P(s/u<10%) collapses from
  78% to 32%.
- **Brazil drought (−500 M bu):** near-mirror image — $5.04 (+$0.24), U.S.
  exports +291 M bu to 3,567, P(s/u<10%) = 98%. The U.S. is the world's
  shock absorber: when Brazil fails, the bushels come from here.
- **China surge (+200 M bu import demand):** U.S. price +$0.09 to $4.89,
  U.S. exports +115 M bu. A demand shock is kinder to the U.S. than a rival
  supply shock is cruel — the U.S. captures 58% of the marginal bushels.

## China +200 M bu surge: who supplies the marginal bushels?

Structural marginal capture (Δ equilibrium exports ÷ 200):
- US: 57.9% (116 M bu)
- BR: 7.8% (16 M bu)
- AR: 1.4% (3 M bu)
- UP: 0.6% (1 M bu)

The captures sum to ~68%, not 100% — and that is the economics working, not
an error. The +200 M bu of extra China demand raises the world clearing
price (~+$0.09), which rations about 60 M bu of rest-of-world import demand
and slightly damps China's own realized imports, so only ~140 M bu of extra
exports are actually needed. The U.S., as the residual supplier, absorbs most
of what remains (116 M bu); competitors' export supply is price-inelastic in
this model (their crops are fixed — only domestic demand rationing responds),
so Brazil picks up just 16 M bu despite being the shock's origin in the
bumper/drought scenarios.

Level allocation of China's total buys (logit on landed cost, lambda=1.0): US 19.5%, BR 27.7%, AR 25.1%, UP 27.7%.
Note: with the specified FOB spreads + freight, the U.S. is the highest-landed-cost origin, so its logit share (~19.5%) sits below the 25-45% calibration target band — reported honestly; this affects only the level accounting, not price clearing.

## v2-vs-global validation (base)

Same U.S.-side draws as v2 base (identical seeds); only the export demand mechanism changes, so deltas isolate curve-shape effects:
- P50 price: v2 $4.75 → global $4.80 (Δ +0.05)
- P50 U.S. exports: v2 3203 → global 3276 (Δ +73 M bu)
- P(s/u<10%): v2 61.5% → global 78.3% (Δ +16.9 pp). It RISES, not falls: the week-2 export pace-residual draw (sd ~29%) is dropped, but the residual curve is anchored at the WASDE 3275 export level while v2's median pace draw sat ~4% below it (~3,151) — week-2 pace typically understates final exports. The level effect dominates the variance effect: the global distribution is tighter but centered on a tighter sheet.

## Key assumptions and data gaps

- Anchors: USDA FAS PSD September 2026 vintage (staged `psd_corn_world_stage_2026-09-18.csv`); all 2026/27 country identities verified at staging.
- Competitor export supply slopes up in price ONLY through domestic demand rationing; competitor carry demand is fixed at September-vintage ending stocks (the `kval` term — needed so the residual curve passes through the WASDE point).
- September vintage is ~final for BR/AR/UP crops, so baseline production sds are small (100/100/80 M bu); the big forward safrinha uncertainty lives in the ±500 scenarios. PSD does not split first/safrinha crops (Brazil safrinha ≈78% is narrative only).
- Full-year clearing model; the h2_ presets are the same model with H2 labels for the newsletter's seasonal framing — no separate H1/H2 mechanism (future upgrade).
- Rest-of-world held fixed at September-vintage levels; X_OTHER's 666-vs-941 gap is the PSD world imports/exports statistical discrepancy (MY/TY timing).
- No as-published WASDE vintage CSVs yet: U.S.-side error sds are still v1's stated priors; elasticities are literature-range triangular priors (foreign elasticities are v1-world choices).
