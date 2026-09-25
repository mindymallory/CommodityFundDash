# Corn Demand Elasticity — Literature Review
*Prepared 2026-09-18 for the commodity newsletter structural Monte Carlo*
*Purpose: verify the elasticity priors used in `monte_carlo/structural.py` against published estimates.*

Our current priors (triangular min/mode/max, all own-price demand elasticities):
exports (−1.2, −1.0, −0.8) · feed (−0.5, −0.35, −0.2) · ethanol (−0.5, −0.375, −0.25) ·
food/seed/other (−0.25, −0.175, −0.1) · stocks (−1.5, −1.0, −0.5)

---

## 1. U.S. corn export demand elasticity

**Reimer, J.J., Zheng, X., & Gehlhar, M.J. (2012). "Export Demand Elasticity Estimation for Major U.S. Crops." *Journal of Agricultural and Applied Economics*, 44(4), 501–515.**
- Corn: short-run −1.04 (1976–2011 mean), −1.09 (1991–2011), −1.11 (2001–2011); long-run −1.53, −1.62, −1.64 respectively (Table 6).
- This is the source of the memo's "long-run −1.64" figure. Verified via the published PDF (ageconsearch record 137120).
- Verdict: our mode of −1.0 sits almost exactly on their short-run estimate (−1.04 to −1.11). ✓

**Bredahl, M.E., Meyers, W.H., & Collins, K.J. (1979). "The Elasticity of Foreign Demand for U.S. Agricultural Products: The Importance of the Price Transmission Elasticity." *American Journal of Agricultural Economics*, 61(1), 58–63.**
- Corn export demand elasticity: −1.31 (as tabulated in Abbott et al. 2016, Table 4).
- Verdict: slightly more elastic than our max (−1.2); supports keeping −1.2 at the elastic edge. ✓

**Gardiner, W.H., & Dixit, P.M. (1987). *Price Elasticity of Export Demand: Concepts and Estimates.* Foreign Agricultural Economic Report No. 228, USDA Economic Research Service, February.**
- Literature review finding corn export elasticities in the range −0.3 to −0.6 (as tabulated in Abbott et al. 2016, Table 4).
- Verdict: notably *less* elastic than our range — a reminder that older estimates cluster lower. Our range does not cover this cluster; acceptable if we treat −0.8 as a firm inelastic bound, but flag it.

**Chambers, R.G., & Just, R.E. (1981). "Effects of Exchange Rate Changes on U.S. Agriculture: A Dynamic Analysis." *American Journal of Agricultural Economics*, 63(1), 32–46.**
- Corn export demand: range −0.47 to −0.63 (as tabulated in Abbott et al. 2016, Table 4).
- Verdict: same note as Gardiner & Dixit — below our inelastic bound.

**Fortenbery, T.R., & Park, H. (2008). "The Effect of Ethanol Production on the U.S. National Corn Price." Staff Paper No. 523, Department of Agricultural & Applied Economics, University of Wisconsin-Madison, April 2008. DOI: 10.22004/ag.econ.92200**
- Export demand elasticity: range −0.26 to −0.32 (as tabulated in Abbott et al. 2016, Table 4). (Paper verified via RePEc/IDEAS; elasticity values per Abbott Table 4.)
- Verdict: well below our range; same caveat as above.

**Haniotis, Baffes & Ames (1988)** — export demand −1.727, a *relative-price* elasticity (U.S. price vs. trade-weighted competitor prices), as noted in Abbott et al. (2016), Table 4 footnote. Full reference not independently verified; cited here only as reported in Abbott et al.

**Babcock (2008)** — export demand −1.2, flagged by Abbott et al. (2016), Table 4 as "estimated to fit model, as opposed to derived." Underlying source document not independently verified; treat as a modeling assumption, not an econometric estimate.

**Category verdict: CONSISTENT for short-run use.** Our (−1.2, −1.0, −0.8) brackets the modern short-run estimates (Reimer et al. −1.04/−1.11; Babcock −1.2) almost exactly. Two cautions: (a) long-run elasticities run higher (−1.5 to −1.7), so if any scenario is meant as multi-year, shift up; (b) several older/structural estimates (−0.26 to −0.63) sit below our inelastic bound — our range implicitly takes the elastic side of the literature.

---

## 2. Corn feed demand elasticity

**Babcock (2008)** — feed & residual −0.4 (model-fit value; same verification caveat as above, via Abbott et al. 2016, Table 4).

**Fortenbery & Park (2008)** (full citation above) — feed demand: range −0.3 to −0.4 (via Abbott et al. 2016, Table 4).

**Womack (1976)** — feed demand: range −0.4 to −0.9 (via Abbott et al. 2016, Table 4; underlying source not independently verified).

**Taylor, R.D., Mattson, J.W., Andino, J., & Koo, W.W. (2006)** — feed demand −0.11 (via Abbott et al. 2016, Table 4; underlying NDSU CAPTS paper's full reference not independently verified — a related publication is Koo, W.W. & Taylor, R.D. (2008), "An Economic Analysis of Corn-based Ethanol Production," Agribusiness & Applied Economics Report No. 626, North Dakota State University).

**Category verdict: CONSISTENT.** Our (−0.5, −0.35, −0.2) centers on the Babcock/Fortenbery cluster (−0.3 to −0.4). The literature span is wider (−0.11 to −0.9) than our triangle; if we want the Monte Carlo to reflect full literature uncertainty, consider widening to (−0.7, −0.35, −0.15). As-is, the prior is defensible and centered.

---

## 3. Corn-for-ethanol (derived) demand elasticity

**Taylor, Mattson, Andino & Koo (2006)** — "Ethanol Demand" (corn used for ethanol): −0.33 (via Abbott et al. 2016, Table 4, footnote **). This is the only direct econometric-style estimate of the corn-for-ethanol demand elasticity found.

**Westcott, P.C. (2007). "U.S. Ethanol Expansion Driving Changes Throughout the Agricultural Sector." *Amber Waves*, September 2007, USDA Economic Research Service.** https://ers.usda.gov/amber-waves/2007/september/u-s-ethanol-expansion-driving-changes-throughout-the-agricultural-sector
- Qualitative but authoritative: "ethanol demand is very inelastic (unresponsive to price changes) in the range of prices expected over the next decade and relative to other major demands for corn, such as feed use and exports."
- Verdict: argues for the inelastic end — our −0.5 elastic bound is likely too high.

**Category verdict: ROUGHLY CONSISTENT, consider re-centering.** The single empirical estimate (−0.33) sits just inside our range but below our mode (−0.375), and ERS's qualitative read ("very inelastic") points the same way. Recommended: (−0.45, −0.30, −0.15). Current prior is not wrong, but leans elastic relative to the evidence.

---

## 4. Corn food / seed / industrial demand elasticity

**Babcock (2008)** — FSI −0.1 (model-fit; caveat as above, via Abbott et al. 2016, Table 4).

**Fortenbery & Park (2008)** — FSI: range −0.075 to −0.064 (via Abbott et al. 2016, Table 4).

**Womack (1976)** — FSI: range −0.08 to −0.14 (via Abbott et al. 2016, Table 4; not independently verified).

**Taylor, Mattson, Andino & Koo (2006)** — "other Industrial Use": −0.22 (via Abbott et al. 2016, Table 4, footnote **).

**Category verdict: CONSISTENT.** Our (−0.25, −0.175, −0.1) brackets the literature (−0.064 to −0.22) with the mode sensibly between the food/seed estimates and the industrial estimate. No change recommended. Note: with the RFS, the ethanol portion is now broken out separately, so this category is genuinely the inelastic remainder — the low estimates fit.

---

## 5. Demand for stocks (inventory demand) elasticity

**Finding: no standard constant-elasticity estimate exists in the literature.** Grain stockholding is modeled via the theory of storage, in which the demand for stocks is *highly nonlinear* — very elastic at high stock levels, nearly vertical approaching stockout — so a single elasticity number is not a natural object in this literature. References (as cited in Abbott et al. 2016):
- Wright, B.D. & Williams, J.C. (1982), theory of storage (cited in Abbott et al. 2016, §Model).
- The modern empirical storage literature (e.g., Gouel's indirect-inference storage model) estimates structural parameters, not a constant stock-demand elasticity; no single number could be extracted.

**Category verdict: UNVERIFIED — judgment call.** Our (−1.5, −1.0, −0.5) has no paper behind it. It is a modeling convenience to close the model. Recommend: (a) document it explicitly as an assumption in the README (done — keep it labeled), (b) run the existing elasticity sensitivity (the v2 build already varies it) and report how much headline results move, (c) consider replacing it in a future version with a proper Working-curve / stockout-nonlinear specification rather than a constant elasticity.

---

## 6. Verification of cited framework papers

**Abbott, Boussios & Lowenberg-DeBoer — CONFIRMED, exists as described.**
- Abbott, P., Boussios, D., & Lowenberg-DeBoer, J. (2016). "Valuing Public Information in Agricultural Commodity Markets: WASDE Corn Reports." *Proceedings of the NCCC-134 Conference on Applied Commodity Price Analysis, Forecasting, and Market Risk Management*, St. Louis, MO, April 18–19, 2016. Authors: Department of Agricultural Economics, Purdue University. http://www.farmdoc.illinois.edu/nccc134 (PDF verified: https://farmdoc.illinois.edu/assets/meetings/nccc134/conf_2016/pdf/Abbott_Boussios_LowenbergDeboer_NCC-134_2016.pdf)
- Matches the memo's description exactly: dynamic quarterly U.S. corn model, Monte Carlo over correlated WASDE forecast-error distributions (area, yield, exports, stocks; variances shrinking as information improves), sensitivity over elasticities. Their Table 4 is itself a literature review of demand/supply elasticities and is the source of most estimates above. Their base-case demand elasticities (Table 7): exports −1.0, feed −0.4, FSI −0.2 — notably close to our modes.

**Westcott & Hoffman — CONFIRMED.**
- Westcott, P.C., & Hoffman, L.A. (1999). *Price Determination for Corn and Wheat: The Role of Market Factors and Government Programs.* Technical Bulletin No. 1878, Market and Trade Economics Division, Economic Research Service, U.S. Department of Agriculture. DOI: 10.22004/AG.ECON.33581. PDF: https://ageconsearch.umn.edu/record/33581/files/tb991878.pdf
- Annual U.S. farm-price models on a stocks-to-use framework, implemented in USDA short-term market analysis and long-term baseline projections — i.e., the basis of USDA's own price forecasting, as the memo states. (The reciprocal specification P = a + b/(stocks-to-use) used in our v1 diagnostic comes via the Irwin & Good farmdoc lineage: e.g., farmdoc daily, April 6, 2016, "New Corn and Soybean Pricing Models.")

---

## Summary of recommended prior changes

| Category | Current (min, mode, max) | Verdict | Suggested |
|---|---|---|---|
| Exports | (−1.2, −1.0, −0.8) | Consistent (short-run) | No change |
| Feed | (−0.5, −0.35, −0.2) | Consistent, slightly narrow | Optional widen to (−0.7, −0.35, −0.15) |
| Ethanol | (−0.5, −0.375, −0.25) | Leans elastic vs evidence | Re-center to (−0.45, −0.30, −0.15) |
| Food/seed/other | (−0.25, −0.175, −0.1) | Consistent | No change |
| Stocks | (−1.5, −1.0, −0.5) | No literature basis | Keep as labeled assumption; sensitivity-test; consider Working-curve replacement later |

**Not independently verified** (cited via Abbott et al. 2016, Table 4 — flagged in the file, not presented as primary): Haniotis, Baffes & Ames (1988); Womack (1976); Babcock (2008) (noted by Abbott as model-fit, not estimated); Taylor, Mattson, Andino & Koo (2006) (underlying NDSU paper title unconfirmed).
