# Marketing-Year Audit — US Corn History & Pace Forecaster v1
**Date:** 2026-09-18 · **File:** `US_Corn_History_and_Pace_v1.xlsx`
**Trigger:** Mindy caught that the September WASDE production cut to 15,800 M bu belongs to the **new crop (2026/27)**, not 2025/26. This audit checks every pipeline, connector mapping, and formula for marketing-year correctness, and — per Mindy's follow-up — replaces all hardcoded year references with dynamic, rollover-proof logic.

## Verdict on the flagged "discrepancy"
**Not a discrepancy.** Verified against the live WASDE #675 text (`wasde0926.txt`, "U.S. Feed Grain and Corn Supply and Use"):
- 2025/26 Est. column: production **17,021** ✓, exports **3,425** ✓, ending stocks 1,922 ✓ — matches HIST_BALANCE row 19 exactly.
- 2026/27 Proj (Sep) column: production **15,800** ✓, exports **3,275** ✓, yield 178.5 ✓, ending 1,567 ✓, price $4.80 ✓ — matches HIST_BALANCE row 20 exactly.

So: 17,020.5 = 2025/26 (nearly complete year), 15,800 = 2026/27 (new crop). Both correct, both stay.

## 1. Column map — HIST_BALANCE (A1:R20)

| Row | A: Marketing year | Source / vintage | Role |
|---|---|---|---|
| 3 | header | — | col R added: "MY key" (`=LEFT(A,7)`) for exact year matching |
| 4–18 | 2010/11 – 2024/25 | ERS Feed Grains Database yearbook tables (downloaded 2026-09-18; `src/feed-grains-yearbook-tables-all-years.csv`) | finalized history |
| 19 | **2025/26** | ERS yearbook, cross-checked = WASDE #675 "2025/26 Est." column | **prior completed MY** (MY ended 2026-08-31; Sep WASDE is its last estimate) |
| 20 | **2026/27 Proj (Sep WASDE)** (blue fill) | WASDE #675 Sep 2026/27 Proj column, typed from the report text (`src/build_v1.py:106`) | **current / new-crop MY** (began 2026-09-01) |

Columns: B planted, C harvested, D yield, E beg. stocks, F production, G imports, H total supply, I feed & residual, J FSI, K ethanol grind, L exports, M total use, N ending stocks, O stocks/use, P price, Q identity check (=H−M−N, all resolve 0), **R MY key (new)**.

## 2. Checks — pass / fail

| # | Check | Result |
|---|---|---|
| 1 | FAS file→MY mapping: `corn_my{N}.json` covers Sep(N−1)–Sep(N) = MY (N−1)/N | **PASS** — all 20 files verified from raw `weekEndingDate`s; MY2007=2006/07 … MY2026=2025/26 |
| 2 | FAS week sequences complete, no negatives | **PASS** — 53 weeks each (MY2012 has a 54th re-report week, 2012-09-06, +958 MT, already documented as dropped) |
| 3 | Multi-window CSV (`fas_corn_scurve_windows.csv`) recomputed independently from staged weekly CSV | **PASS** — avg5/10/15/20 wk1 (26.78/25.37/27.36/27.00) and min10/max10 wk1 (16.15/40.01) all reproduce exactly; all windows converge to 100.0 at wk53 (self-normalized denominators ✓) |
| 4 | 10-yr staged curve (K:N) denominators = HIST_BALANCE col L for 2016/17–2025/26 | **PASS** — converges ~97.5% at wk53 as documented |
| 5 | Old V2/V3 `MATCH("*Proj*",A:A,0)-1` resolves to 2025/26 today | **PASS today, FAIL on robustness** — first "*Proj*" hit is row 20 → −1 → row 19 (2025/26: 3,425 / 17,020.5). But after a 2027/28 proj row is appended, it still resolves to row 19 (2025/26) — silently stale. Also fuzzy text matching. **Replaced** (see fixes) |
| 6 | Manual input block A:G (weeks ending 2026-09-03, 2026-09-10; "carryover" note) — which MY? | **2026/27** (week #1–2 of the new MY). It was benchmarked against 2025/26's 3,425 — **FAIL, fixed**: now benchmarks against Current-MY 2026/27 (3,275). Note the original v1 builder's method text said "vs WASDE 3,275" — this fix *restores* that design intent |
| 7 | Staged 2025/26 series (P:T) vs its benchmark | **PASS after fix** — now pinned to its own staged-MY benchmarks (V6/V7 → 3,425 / 17,020.5), independent of Current MY |
| 8 | Chart 1 (A78) series: R (2025/26 actuals) + W (forecast) + H (implied from 2026/27 manual inputs) | **FAIL — year-mixed, fixed**: now plots live Current-MY commitments (G) + Current-MY forecast (W) + implied (H) |
| 9 | Main S-curve chart 4th series: T = staged % of WASDE forecast plotted alongside self-normalized %‑of‑final bands | **FAIL (label/denominator mismatch), fixed**: now plots new col Y = staged % of own final — denominator-consistent with the bands (numerically ~identical for 2025/26 since final = 100.0% of WASDE, but now honest) |
| 10 | PACE_ETHANOL E5 = hardcoded 5600, label "2026/27" | **PASS today, FAIL on rollover** — **fixed**: now `INDEX/MATCH` on Current MY (still 5,600 today) |
| 11 | PACE_ETHANOL weekly seeds (2026-08-28 = "prior-MY reference week", 2026-09-04/11 = MY weeks 1–2) | **PASS** — 2026/27 weeks correctly identified |
| 12 | PACE_FEED template pinned to 2025/26 (Q1 Sep–Nov 2025 … Q4 Jun–Aug 2026; F&R 6,350 = HIST_BALANCE I19) | **PASS** — explicitly a completed-year template; intentionally not dynamic (see ambiguities) |
| 13 | VALIDATE §1 identity rows cover 2010/11–2025/26; 2026/27 Proj row missing | **FAIL (omission), fixed** — added 2026/27 Proj row (Q20 resolves 0 ✓) |
| 14 | VALIDATE §2 vintage check (production 16,013→15,800) — which MY? | **2026/27** — was unlabeled; **fixed**: header now reads "2026/27 new crop". Values cross-check to HIST_BALANCE row 20 ✓ |
| 15 | ERS pipeline provenance (`src/`: yearbook CSV + `build_v1.py` + `corn_history.json`) | **PASS** — reproducible; 2025/26 row = ERS yearbook = WASDE #675 Est. column exactly |
| 16 | Chart-2 (A99): X = staged % of production | **PASS after fix** — X now ÷ staged benchmark V7 (17,020.5), title cell-linked to staged MY |
| 17 | H-column blanks for future weeks showed 0 (would draw false zero-line on chart) | **FAIL, fixed** — F now returns `NA()` on blank weeks (charts gap honestly); H wrapped in `IFERROR` |

## 3. Fixes made (cell, before → after)

**README**
- B20–B27 *(new)*: MARKETING-YEAR CONTROL — B22 Current MY auto from date (`Sep 1–Aug 31` → "2026/27" today); B23 manual override (blank); B24 effective (`=IF(B23="",B22,B23)`); B25 prior MY (derived: "2025/26"); B26 staged FAS series MY (**manual**, "2025/26" — must match the staged data); B27 WASDE vintage ("Sep #675 (2026-09-11)"); C26 guardrail flag if staged MY ≠ prior MY.
- A2: "16-year history (2010/11–2025/26)" → notes the 2026/27 Proj row. A13: S-curve status (export FITTED, ethanol TO FIT). A18: honest gaps updated (export history done).

**HIST_BALANCE**
- A1: title → "…History 2010/11–2025/26 + 2026/27 Proj (Sep WASDE #675)".
- R3:R20 *(new)*: `MY key =LEFT(A,7)` → "2010/11"…"2026/27" — the exact-match column every lookup uses.

**PACE_EXPORT**
- V2: `INDEX(L:L,MATCH("*Proj*",A:A,0)-1)` → `IFERROR(INDEX(L:L,MATCH(README!$B$24,R:R,0)),"MY not in HIST_BALANCE")` — **3,425 → 3,275** (Current MY 2026/27).
- V3: same pattern on col F — **17,020.5 → 15,800**.
- V5:V7 *(new)*: staged-series benchmarks pinned to README B26 → 2025/26: 3,425 / 17,020.5.
- R4/S4/T4/X4/Y4 headers: now formulas appending the staged MY (`=$V$5&" commitment (M bu)"` etc.) — never stale.
- T5:T57 → `=IFERROR(R5/$V$6*100,"")`; X5:X57 → `=IFERROR(R5/$V$7*100,"")` (were ÷ V2/V3).
- Y4:Y57 *(new)*: staged % of own final `=IFERROR(R5/$R$57*100,"")` for the S-curve chart.
- F5:F57: `=C5+D5` → `=IF(AND(C5="",D5=""),NA(),C5+D5)`; H5:H57 wrapped in `IFERROR(...,"")`.
- A3 *(new)*: dynamic label — "Live weekly inputs — 2026/27 (Current MY, auto). Staged reference series (P:Y) = 2025/26 (completed MY)."
- A2 method text, A77/A98 how-to: rewritten around the dynamic MY model.
- Charts: all three titles now cell-linked (A59/A75/A96, formula-driven); chart-1 series R→G (live commitments); main-chart 4th series T→Y.
- I4: "vs USDA forecast" → "vs Current-MY USDA forecast (H − V2)". W4 similarly clarified.

**PACE_ETHANOL** — A5 → dynamic year label; E5: hardcoded `5600` → `INDEX(K:K,MATCH(Current MY,R:R,0))` (still 5,600 today); H7 → dynamic "vs 2026/27 WASDE".

**VALIDATE** — A22:C22 *(new)*: 2026/27 Proj identity row; A24: vintage check labeled "2026/27 new crop".

**CHANGELOG** — row 13 (2026-09-18) documents the audit; notes the "15,800 vs 17,020.5" non-conflict and supersedes row 12's manual-update instructions (changelog is append-only; row 12 left intact).

No data values were changed — only references, labels, and formulas. Workbook reopens cleanly; no `*Proj*` fuzzy matches remain.

## 4. Unresolved ambiguities & recommendations
1. **PACE_FEED is pinned to 2025/26 by design** (completed-year template). Each new MY needs a fresh quarterly template — recommend adding it as a release-day checklist item rather than automating.
2. **Manual block (A:G) rollover workflow:** at each Sep 1, Mindy overwrites A5:A57/C:D with the new MY's weeks (B week numbers 1–53 stay). The old year's inputs are lost unless archived — recommend copying the block to a new "ARCHIVE_2026/27" sheet each August, or restaging the year into the FAS staged series (the permanent record).
3. **Lookback windows freeze at restage time.** "Last 5/10/15/20 years" = 5/10/15/20 years ending 2025/26 until the FAS pull is refreshed. After restaging with 2026/27, a human also updates README B26 — C26 flags any mismatch.
4. **Implied-final (H) still uses the 10-yr WASDE-denominated curve** converging to ~97.5% at wk53 — late-season implied finals read ~2–3% high vs a year that finishes at 100% of WASDE. Known, documented, unchanged.
5. **Chart titles are cell-linked**, so they update with the control block — but anyone viewing a *printed/PDF* snapshot sees the frozen year, as expected.

## 5. Rollover robustness — what happens on Sep 1, 2027
- **Automatic:** README B22 flips to "2027/28" → B24/B25 follow → V2/V3/E5 re-resolve via exact MATCH; chart titles, headers, and labels update; the live block (A:G) is already week-number-based so it just keeps working as Mindy enters 2027/28 weeks.
- **Human must do:** (1) add the 2027/28 row to HIST_BALANCE (from the Sep 2027 WASDE) — until then V2/V3/E5 show the visible text flag "MY not in HIST_BALANCE" instead of silently pointing at the wrong year; (2) add a VALIDATE §1 row for the new MY (hardcoded year list — not automatic, flagged here); (3) after 2026/27 ends, pull FAS MY2027, restage, update README B26 (C26 flags mismatch until then).
- **Would NOT silently break:** every year lookup is exact-match against the control block with `IFERROR` fallbacks; no fuzzy text; no hardcoded years in any benchmark formula. The failure mode for a missed step is a visible flag, never a wrong number.
