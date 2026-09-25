# Monte Carlo v2 (structural) — 2026/27 U.S. corn — 2026-09-18

**What changed:** v1 priced every draw off a fitted curve (price = a + b ÷
stocks-to-use) with use held fixed. v2 models the demand side structurally:
each use category — exports, ethanol grind, feed & residual, food/seed/other,
plus the demand to *carry stocks* — gets its own constant-elasticity demand
curve, and the season-average price is whatever clears supply = demand. A
−5 bu/acre yield cut no longer dumps entirely into ending stocks; instead the
price rises until demand falls by the full 443 M bu, and the cut is shared
across uses according to how price-sensitive each one is.

## Headline numbers (n = 10,000 draws per scenario, seeded/deterministic)

| Scenario | P50 price | P10–P90 price | P50 ending stocks | P50 s/u | P(s/u < 10%) |
|---|---|---|---|---|---|
| Base (WASDE #675) | **$4.75** | $4.30–$5.21 | **1,583 M bu** | 10.4% | **61.5%** |
| Yield shock −5 bu/ac (−443 M bu) | **$4.99** | $4.53–$5.48 | **1,509 M bu** | 9.7% | **71.4%** |
| Export surge (+200 M bu demand) | **$4.85** | $4.41–$5.31 | **1,550 M bu** | 10.0% | **70.9%** |

WASDE #675 point for reference: $4.80, 1,567 M bu ending, 9.69% s/u.

**Reading it:** the yield shock lifts the median price by about **+$0.24/bu**
($4.75 → $4.99) and trims median ending stocks by ~74 M bu — not 443 M bu,
because price rationing does most of the work. The export-surge scenario
(+200 M bu of export demand) lifts the median price ~+$0.10 and costs ~33 M bu
of ending stocks; note exports themselves rise by *less* than 200 M bu
because the higher price rations some of it back.

**Why is P(s/u < 10%) so high even in the base case (61.5%)?** At week 2 of
the marketing year, export demand is genuinely the big unknown — the FAS
pace residuals have a ~29% standard deviation. Large positive export-demand
draws tighten the balance sheet hard. That uncertainty is real (it's the
data talking, same as v1), and it shrinks as the export pace firms up
through the fall.

## Where does the 443 M bu cut go? (deterministic, median elasticities)

Price rises to $5.04 (+$0.24) until demand falls by the full cut:

- Exports: **−155 M bu** (most price-sensitive demand absorbs the most)
- Ethanol grind: **−101 M bu**
- Feed & residual: **−100 M bu**
- Food/seed/other: **−11 M bu** (least elastic — barely moves)
- Ending stocks: **−74 M bu**

Sums to 442.5 M bu. Exports absorb ~14× what food/seed/other does — exactly
the economics you'd expect.

## v1 vs v2 on the same −5 bu/acre shock

| | v1 | v2 |
|---|---|---|
| P50 price | $5.87 | $4.99 |
| P50 ending | 1,214 M bu | 1,509 M bu |
| P(s/u < 10%) | 72.3% | 71.4% |

**Why the difference, in one paragraph:** v1 held all uses fixed, so the
entire 443 M bu cut came out of ending stocks (1,567 → 1,214), and then the
fitted inverse price curve — which is very steep down at ~7.5% stocks-to-use
— priced that at $5.87. v2 lets the price ration demand instead: only ~74 M bu
comes out of ending stocks while lower use absorbs the rest, so
stocks-to-use falls much less and the clearing price rises only ~$0.24.
Both models agree the shock materially raises the odds of sub-10%
stocks-to-use (~71–72%); they disagree on *how* the market gets there, and
v2's mechanism (demand rationing) is the economically coherent one.

## How to re-run

```bash
cd ~/workspace/your_files/commodity-newsletter-design
python3 -m monte_carlo.run_structural
```

Writes `mc_charts/mc_structural_*.png` (4 charts), the `MC_STRUCTURAL`
workbook tab, and `mc_structural_results_2026-09-18.json`. All v1 files are
untouched. Full method, priors, and validation: `monte_carlo/README.md`
(v2 section).
