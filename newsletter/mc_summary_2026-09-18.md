# Monte Carlo v1 results — 2026/27 U.S. corn (generated 2026-09-18)

10,000 simulated marketing years, starting from the September WASDE #675
balance sheet (production 15,800 · exports 3,275 · ending stocks 1,567 ·
stocks-to-use 9.7% · price $4.80). Each draw perturbs the uncertain lines
with historically-grounded errors and re-solves the balance sheet.

## Headlines

- **Median ending stocks: 1,663 M bu** (WASDE point: 1,567). 80% interval: **760 – 2,487**.
- **Median season-average price: $4.61** (WASDE point: $4.80). 80% interval: **$3.11 – $7.88**.
- **Probability stocks-to-use falls below 10%: 46%** — essentially a coin flip from here.

## Why the median sits above the WASDE point

At only week 2 of export-sales data, pace-implied finals *typically*
understate where the year finishes (median residual −3.8% across 20 years
of history). So the median draw implies exports ≈ 3,151 vs WASDE's 3,275,
leaving ~100 M bu more in ending stocks. This is the data talking, not a
modeling choice — and it's exactly why the distribution matters more than
the point estimate this early in the year.

## The left tail is real but wild

About 7% of draws push stocks-to-use below 3%, where the historical
price curve blows up (it was never estimated down there). Those draws
produce absurd prices — they're flagged in the output, not hidden, and
the charts clip the display while annotating how much mass sits in the
tails. Read the **P10/P50/P90**, not the mean. A proper demand-rationing
mechanism (high prices choke off use before stocks hit zero) is the
honest v2 improvement.

## Scenario: −5 bu/acre yield shock (−443 M bu of production)

- Median ending stocks: 1,663 → **1,214** (−449)
- Median price: $4.61 → **$5.87** (+$1.27)
- P(stocks-to-use < 10%): 46% → **72%** (+26 points)

In words: losing 5 bushels an acre turns the sub-10% stocks outcome from
a coin flip into the house favorite, and adds about $1.25 to the median
price.

## What would tighten this up

1. **More weeks of export data.** The ±29% week-2 export uncertainty
   dominates everything; it collapses as the sales pace reveals itself.
2. **As-published WASDE vintage CSVs** to replace the stated production /
   ethanol / feed error priors with estimated ones.
3. **Demand rationing** so the left tail behaves economically.

Charts: `mc_charts/` (4 PNGs). Full method and assumptions:
`monte_carlo/README.md`. Numbers also in the workbook's `MC_RESULTS` tab.
