# FAS Corn Export-Sales S-Curve — Validation Report

Date: 2026-09-18. Source: USDA FAS Export Sales Reporting API (`/api/esr/exports/commodityCode/401/allCountries/marketYear/{N}`), accessed via the `custom.fas` connector. unitId = 1 (metric tons) for all records. Bushels = MT × 39.368.

## Pull summary

10 marketing years pulled, one JSON file each, in `fas_esr_corn_my2017-2026/`:

| Market year (file) | Marketing year | Records | Weeks | First week | Last week |
|---|---|---|---|---|---|
| MY2017 | 2016/17 | 2,852 | 53 | 2016-09-01 | 2017-08-31 |
| MY2018 | 2017/18 | 2,549 | 53 | 2017-09-07 | 2018-09-06 |
| MY2019 | 2018/19 | 2,456 | 53 | 2018-09-06 | 2019-09-05 |
| MY2020 | 2019/20 | 2,226 | 53 | 2019-09-05 | 2020-09-03 |
| MY2021 | 2020/21 | 2,360 | 53 | 2020-09-03 | 2021-09-02 |
| MY2022 | 2021/22 | 2,060 | 53 | 2021-09-02 | 2022-09-01 |
| MY2023 | 2022/23 | 1,931 | 53 | 2022-09-01 | 2023-08-31 |
| MY2024 | 2023/24 | 1,944 | 53 | 2023-09-07 | 2024-09-05 |
| MY2025 | 2024/25 | 2,518 | 53 | 2024-09-05 | 2025-09-04 |
| MY2026 | 2025/26 | 2,542 | 53 | 2025-09-04 | 2026-09-03 |

**Total: 23,438 country-week records, 530 year-weeks.** Record count differences across years reflect country coverage (reporting countries grew/fell), not missing weeks — every year has a complete, gap-free 53-week sequence (verified: no gaps, no duplicates).

## Final-week commitment vs WASDE final exports

Final annual exports read from `HIST_BALANCE` col L of `US_Corn_History_and_Pace_v1.xlsx` (2025/26 = Sep WASDE #675 estimate, 3,425 M bu — not final yet).

| Marketing year | Final-week commitment (M bu) | WASDE final exports (M bu) | Commitment ÷ final |
|---|---|---|---|
| 2016/17 | 2,220.6 | 2,295.7 | 96.7% |
| 2017/18 | 2,377.8 | 2,437.1 | 97.6% |
| 2018/19 | 1,965.9 | 2,068.3 | 95.0% |
| 2019/20 | 1,752.8 | 1,778.5 | 98.6% |
| 2020/21 | 2,753.2 | 2,746.9 | 100.2% |
| 2021/22 | 2,393.6 | 2,472.4 | 96.8% |
| 2022/23 | 1,597.7 | 1,661.9 | 96.1% |
| 2023/24 | 2,194.0 | 2,254.8 | 97.3% |
| 2024/25 | 2,765.6 | 2,872.5 | 96.3% |
| 2025/26 | 3,425.3 | 3,425.0 | 100.0% |

Range: **95.0%–100.2%**. Outstanding sales are mostly shipped by year-end, so final commitment lands within ~5% of final exports — close enough to use as a final-export proxy in the PACE_EXPORT tab, with the avg curve converging to ~97.5% at week 53.

## Anomalies / data-quality flags

- **None material.** No missing weeks, no negative accumulated exports, no week-over-week commitment drops larger than 5% (no mass-cancellation events), no mid-year commitment spikes above 105% of final, all records metric tons.
- **Week-alignment note:** FAS week-ending dates are calendar-fixed (Thursdays), so the first week of each marketing year lands on a different Sep date (Sep 1 vs Sep 7). `week_of_marketing_year` is therefore numbered by **calendar position** — days from Sep 1, integer-divided by 7 — not by ordinal position in the file, so the same week number always means the same point in the marketing year across all 10 years.
- **Week 1 already books ~25% of the year's sales** (avg 24.7%, range 15.9% for 2019/20 to 38.7% for 2021/22): commitments for the new marketing year are routinely made months before Sep 1. This is a feature of the data, not an error.
- **2025/26 caveat:** final commitment = 100.0% only because both the FAS commitment and the WASDE figure are measuring the same nearly-complete marketing year; the 3,425 M bu WASDE number is still an estimate and may revise.

## Where the cross-year spread is widest

Spread (max − min commitment %) peaks in **weeks 22–26 (late January through early March), ~30 percentage points wide**, narrowing steadily toward year-end. Drivers:

| Week | Min | Max | Avg |
|---|---|---|---|
| 22 | MY2020 50.4% | MY2021 80.4% | 63.9% |
| 23 | MY2020 52.6% | MY2021 82.5% | 65.8% |
| 24 | MY2020 55.4% | MY2021 83.9% | 68.7% |
| 25 | MY2020 57.3% | MY2021 84.6% | 70.3% |
| 26 | MY2020 59.0% | MY2021 84.7% | 71.9% |

The min leg is 2019/20 (slow early bookings, then a late surge to 98.6% by year-end); the max leg is 2020/21 (record Chinese buying front-loaded the year). Practical takeaway: implied-final estimates made in Jan–Mar carry ±15 pp bands; the band halves by week ~40.

## The average curve (endpoints)

First 5 weeks (avg % of final exports): wk1 24.7, wk2 26.3, wk3 27.8, wk4 29.6, wk5 31.4.
Last 5 weeks: wk49 97.4, wk50 97.7, wk51 97.8, wk52 97.6, wk53 97.5.

## Files produced (staged for Mindy's review — NOT yet loaded into the workbook)

- `fas_esr_corn_my2017-2026/corn_my{2017..2026}.json` — raw FAS pulls
- `fas_corn_weekly_commitment_stage.csv` — 530 rows: market_year, week_ending, week_of_marketing_year, commitment_mil_bu, accumulated_exports_mil_bu
- `fas_corn_scurve_avgminmax.csv` — 53 rows: week_of_marketing_year, avg_pct, min_pct, max_pct, n_years (n=10 for all weeks)

---

## Addendum — 20-year extension (MY2007–MY2016), 2026-09-18

Pulled FAS ESR corn (commodityCode 401) for marketYear 2007–2016 (marketing years
2006/07–2015/16), 2,288–2,955 country-week records each, all unitId=1 (metric tons).
Combined with the earlier MY2017–MY2026 pull: **20 marketing years, 1,060 year-weeks.**

**Validation: all 20 years clean.** Every year has a complete, gap-free 53-week sequence
(same week-numbering convention as the 10-yr stage: week = (weekEndingDate − Sep 1 of MY−1) // 7 + 1).
No negative commitments; no mid-year commitment drops > 5%.

**One data-quality flag:** MY2012 (2011/12) included a 54th week (2012-09-06, 46 country records).
It is the FAS re-issued final weekly report for that marketing year — total commitment
39,581,977 MT vs 39,581,019 MT in week 53 (2012-08-30), i.e. a +958 MT re-report, not new sales.
**Week 54 was dropped; week 53 stands as the final.**

**Sanity checks (final-week commitments vs known finals):** MY2013 (2012/13 drought) = 744.9 M bu
(WASDE final 730.1 — 102%); MY2012 (2011/12) = 1,558.2 M bu (WASDE final 1,539.2 — 101%);
MY2008 (2007/08) = 2,462.3 M bu. All plausible.

**Multi-window staging** (`fas_corn_scurve_avgminmax.csv` unchanged; new files below). Per-year
weekly commitments are expressed as % of **that year's own final-week commitment**
(self-normalized — every curve converges to 100% at week 53). This differs deliberately from
the 10-yr WASDE-denominated curve in `fas_corn_scurve_avgminmax.csv`, which is kept for the
implied-final column H. Windows: avg5 = MY2022–MY2026, avg10 = MY2017–MY2026,
avg15 = MY2012–MY2026, avg20 = MY2007–MY2026; min/max band from the 10-yr window.
Widest spread: ~29 pp near week 22 (matches the 10-yr finding).

**New staged files:**
- `fas_esr_corn_my2007-2011/corn_my{2007..2011}.json` and
  `fas_esr_corn_my2012-2016/corn_my{2012..2016}.json` — raw pulls
- `fas_corn_weekly_commitment_stage_2007-2026.csv` — 1,060 rows
- `fas_corn_scurve_windows.csv` — 53 rows: avg5/avg10/avg15/avg20, min10, max10, n's
