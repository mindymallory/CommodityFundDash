# Commodity Balance-Sheet Newsletter — Design Memo
*Prepared for Mindy Mallory · 18 September 2026*

**The idea:** a newsletter built on corn/soybean/wheat balance-sheet analysis — tracking and forecasting WASDE and its supply/demand components, modeling how shocks (yield cuts, export surges) flow through the global balance sheet into ending stocks and price, with Monte Carlo over the real uncertainties. Your situational judgment provides the color; the machinery provides the discipline.

**The core tension you named:** data gathering/updating is nearly a full-time job, and you don't trust automated pipelines you can't see. This design resolves both: automate the fetching, but put a human validation checkpoint between every number and every chart.

---

## 1. The report universe (what feeds the balance sheet)

Every line of a WASDE balance sheet — beginning stocks, production, imports, exports, domestic use, ending stocks — traces back to a specific report. The must-follow set:

**USDA core**
- **WASDE** (monthly, noon ET): the balance sheet itself, U.S. + world. Key months: **May** (first new-crop), **Aug** (first survey yields), **Jan** (final production + Dec stocks), **Sep** (final old-crop stocks).
- **NASS Crop Production** (monthly, same dates): area/yield/production. **Aug 12** is the year's biggest single supply event (first objective corn/soy yields).
- **NASS Grain Stocks** (quarterly): the anchor that forces WASDE revisions. Sep 30 sets final marketing-year ending stocks. Historically the most *surprising* report — biggest price reactions.
- **Prospective Plantings** (Mar 31) → **Acreage** (Jun 30, released with Jun 1 stocks — a double-barreled day) → **Winter Wheat Seedings** (Jan 12).
- **Crop Progress & Condition** (weekly, Mon 4pm): the market's weekly yield proxy between monthlies.
- **FAS Export Sales** (weekly Thu 8:30am + daily flashes): the weekly pulse on the export line.
- **ERS Outlooks** (monthly, days after WASDE): Feed, Oil Crops, Wheat — the analyst narrative behind the numbers.
- **Grain Crushings / Fats & Oils / Flour Milling**: monthly/quarterly reads on ethanol grind, soybean crush, wheat food use. (Note: the crush series was suspended in 2025 — verify it's fully restored before depending on it.)

**Non-USDA (the divergence detectors)**
- **CONAB Brazil** (monthly): authoritative Brazil soy/corn/wheat — routinely moves world production before USDA catches up.
- **Buenos Aires / Rosario exchanges** (weekly/monthly): Argentina planting, harvest, production, vessel lineups.
- **IGC Grain Market Report** (monthly): independent world S&D, the non-USDA counterweight. Full database is paid (~£1,440/yr); summaries free.
- **FAO AMIS** (monthly): compares FAO/IGC/USDA world numbers side by side. Free.
- **EU Commission + JRC MARS** (monthly): EU production and yield forecasts.
- **Black Sea** (SovEcon paid, APK-Inform freemium): matters most for wheat when they diverge from USDA.

**Seasonal rhythm:** Mar–Jun is acreage season (intentions → actual). Jul–Nov is yield season (condition → objective surveys → final). Dec–Feb is demand season (stocks reports + export pace reveal use). Your newsletter calendar should follow this, not the calendar month.

## 2. Getting the data (without it becoming a full-time job)

The good news: nearly everything is free and machine-readable.

- **NASS Quick Stats API** — free key, all area/yield/production/stocks back to 1866. (50k records/request cap; chunk queries.)
- **FAS Open Data API** — free key; global PSD balances + export sales endpoints.
- **WASDE as XML/Excel with every release**, plus the single best backtesting asset in existence: **consolidated historical WASDE CSVs, 2010–2025, as-published vintages** — true forecast vintages, updated the day after each release. This is your forecast-error distribution, ready-made.
- **FRED** (free key) for price series; **FAOSTAT** for global production.

**The pipeline — validation-first, in four layers:**

1. **RAW (frozen).** Every pull lands timestamped and untouched — one file per report-vintage. Never edited. This is your audit trail *and* your backtest dataset.
2. **STAGE (mapped).** Scripts map raw fields to one canonical schema (commodity × country × marketing year × line item × vintage). Units harmonized here (bushels↔tonnes, marketing-year alignment).
3. **VALIDATE (the human checkpoint).** An auto-generated sheet you read *before* anything flows downstream:
   - **Prior-vintage diff**: every changed cell vs. last month, flagged past thresholds.
   - **Identity checks**: supply ≡ demand + ending stocks, every sheet; world trade sums to ~zero.
   - **Range checks**: yields within agronomic bounds, stocks-to-use within 3–40%, harvested ≤ planted.
   - **Cross-source flags**: CONAB Brazil vs. USDA Brazil, IGC world stocks vs. WASDE — divergences highlighted, because divergence is often the story.
   - **Changelog tab**: date, report, what moved, your sign-off note — this becomes the first draft of the newsletter's "what moved and why."
4. **MODEL/CHARTS.** Only validated vintages promote here.

**Operating cadence:** a WASDE-day checklist — pull → stage → read validation sheet → sign off → charts update. Roughly 1–2 hours per cycle once built, concentrated on release days. Start fully manual (download + paste into RAW); script only the most repetitive pulls once the validation sheet proves its worth. **Build validation first, automation second** — automation without the validation layer is exactly what you distrust.

## 3. Form factor: spreadsheet as the system of record

Your instinct is right. Recommendation:

- **Spreadsheet (Excel or Google Sheets) holds RAW/STAGE/VALIDATE/MODEL** — the validation sheet is the product's trust anchor. Every ingested number visible, diffable, hand-checkable.
- **Python as the compute engine** — small scripts do the API pulls and the Monte Carlo, writing results (medians, percentile bands) back into the workbook. Monte Carlo in native Excel is painful; in Python it's trivial.
- **Static charts (matplotlib → PNG) for the newsletter** — interactive dashboards don't survive email anyway.
- Add a web dashboard later *only* if readers want interactivity — never as the validation layer.

This gives you the eyeball-check you require, keeps the heavy math where it belongs, and holds maintenance near zero beyond release-day checklists.

## 4. The model: from shock to stocks to price

**Structure:** identity-based partial equilibrium, one per commodity, linked across commodities.

- Within a marketing year, supply is predetermined → **price clears the identity**. The textbook price-flexibility form: **ΔP/P ≈ (ΔS/S) ÷ (Σ share-weighted demand elasticities)**. A 2% supply shock against weighted demand elasticity of −0.4 → ≈ +5% price, with ending stocks absorbing the residual.
- **Cross-commodity links:** corn/soy acreage competition (spring planting), wheat-corn feed substitution, soybean meal/oil joint products.
- **Reduced-form price equation:** the Westcott-Hoffman framework — price as an inverse nonlinear function of the **stocks-to-use ratio**, estimated on WASDE history. This is the basis of USDA's own price forecasting (farmdoc's version recently implied $3.71 corn / $10.31 soybeans from prevailing ratios).

**Elasticity parameters** (use as Monte Carlo priors, not point truths):
- Export demand: short-run ≈ **−1.0 corn/soy, −0.5 wheat**; long-run −1.64/−1.45/−1.25.
- Domestic: feed −0.2 to −0.5; wheat food −0.1 to −0.25; crush −0.3 to −0.6; short-run acreage response +0.1 to +0.3.

**The blueprint already exists:** Abbott, Boussios & Lowenberg-DeBoer (Purdue, 2016) built *exactly this* — a dynamic U.S. corn model on USDA data with **Monte Carlo over correlated WASDE forecast-error distributions** (area, yield, export, stocks errors drawn from historical revisions, variances shrinking as information improves through the season), price via stocks-to-use logic, and sensitivity analysis over elasticities. Their honest finding: results are "strongly dependent on supply parameter assumptions" — which is the case for putting elasticities inside the Monte Carlo too.

**Your Monte Carlo, concretely:**
- Draw correlated forecast errors for each balance-sheet line from the 2010–2025 WASDE vintage history (error variances narrow Aug→Jan as surveys resolve).
- Draw elasticities from literature-range distributions.
- Propagate: shock → revised supply → price clears via flexibility form → ending stocks residual → stocks-to-use → price distribution.
- Output: fan charts of price and ending stocks, probability of stocks-to-use below 10% (the historical rally zone), scenario deltas ("−5 bu/acre yield = +$X, P(stocks/use < 10%) = Y%").

## 5. Where your judgment lives (the part no one can copy)

The machinery above is replicable. Your edge — the newsletter's actual value over glorified news services — sits in four places:

1. **The validation sign-off.** You reading the diff sheet each month and writing the changelog is already editorial judgment: *what moved, what matters, what's noise.*
2. **Divergence calls.** When CONAB says Brazil soy is 5 MMT below USDA, or Black Sea wheat diverges — the model flags it; you decide who's right and why.
3. **Scenario design.** The Monte Carlo answers any shock you pose. Choosing *which* shocks to run — drought in Mato Grosso, a Black Sea corridor closure, an ethanol mandate change — is situational knowledge no pipeline has.
4. **The narrative.** Numbers say stocks-to-use is 9.7%; you say what that meant the last three times it happened and what's different now.

## 6. Phased build (don't boil the ocean)

- **Phase 0 — one commodity, manual.** U.S. corn balance sheet in a spreadsheet, hand-updated through one WASDE cycle. Proves the validation workflow.
- **Phase 1 — validation layer + first Monte Carlo.** RAW/STAGE/VALIDATE tabs, vintage diff sheet, Python MC for corn price/stocks. First fan charts.
- **Phase 2 — three commodities + cross links.** Soy, wheat, acreage competition, feed substitution. World sheets for the big exporters (Brazil, Argentina, Black Sea, EU).
- **Phase 3 — publish cadence.** Monthly post-WASDE issue + flash notes on big reports (Aug yields, Jan stocks). The changelog tab becomes your first draft.

**Honest gaps in the research:** ERS outlook release *times*, IGC/CONAB official release calendars, FAS "Oilseeds: World Markets and Trade" circular cadence, whether the NASS crush series fully resumed, and EU data APIs could not be verified against primary sources — flagged, not assumed.

---

**Bottom line:** the data burden that scared you off is solvable — the APIs and vintage datasets exist, and a validation-first pipeline keeps the workload to hours per month, not a full-time job. The modeling is textbook economics plus one Purdue paper's blueprint. What's *not* commoditized is the judgment layer — and that's the part you already have.
