# INTEGRATION SPEC — swap the export-error draw for the demand-curve-consistent module

**Do not edit** `structural.py`, `structural_config.py`, `simulate.py`, or
`world.py` in this step — a separate global build is touching those files.
Apply the diffs below after that build lands, or hand them to whoever owns
those files next.

## What changes and why

`monte_carlo/export_errors.py` replaces `simulate.export_pct_residuals`
(the naive week-w implied-final residual) as the source of export demand
uncertainty in the US-only structural model (`structural.py`).

The old draw was contaminated: regressing it on log season-average price
gives t = +3.7, p = 0.0025, R² = 0.52 — over half its variance was price,
i.e. along-curve movement mislabeled as demand shifts, then priced a
second time by the model's elasticities. The new draw infers the demand
shifter Â (X = Â·P^ε) from week-w commitments through a price-purged
booking-pace benchmark, and bootstraps the empirical purged inference
errors e* (week-2 sd 22% vs old 33%).

`simulate.py` (v1, superseded) keeps the old function untouched — v1 is
frozen for reproducibility. `world.py` (global) needs **no change**: it
already dropped the pace-residual draw because exports are endogenous
there (residual export demand curve). Optional future use: validate
`world.py`'s residual export curve against the historical Â_t series from
`export_errors.demand_shifters`.

## New config keys (add to `structural_config.py`)

```python
EXPORT_EPS_WORK = -1.0   # working export demand elasticity; == export_errors.EPS_WORK
EXPORT_PACE_PURGE = True  # divide out the estimated price->booking-pace channel
EXPORT_ERR_SEED_OFFSET = 1  # added to err_seed for the independent Â bootstrap
```

`CURRENT_WEEK` is reused as-is (the week index for C_w and the error band).

## Diff 1 — `structural.py::load_inputs` (lines ~40-44)

OLD:
```python
    finals = simulate.load_finals()
    corr = simulate.error_correlation(finals)
    export_resid = simulate.export_pct_residuals(SC.CURRENT_WEEK)
    return {"finals": finals, "corr": corr, "export_resid": export_resid}
```

NEW:
```python
    from monte_carlo import export_errors as ee
    finals = simulate.load_finals()
    corr = simulate.error_correlation(finals)
    eh = ee.load_history()
    live = ee.current_week_commitments()
    if SC.CURRENT_WEEK not in live:
        raise KeyError(
            f"No live commitments for week {SC.CURRENT_WEEK}; "
            "update PACE_EXPORT before running.")
    export_shift = dict(hist=eh, week=SC.CURRENT_WEEK,
                        C_w=live[SC.CURRENT_WEEK], P_cur=SC.P0,
                        eps=SC.EXPORT_EPS_WORK, purge=SC.EXPORT_PACE_PURGE)
    return {"finals": finals, "corr": corr, "export_shift": export_shift}
```

## Diff 2 — `structural.py::draw_base_quantities` (lines ~69-73)

OLD:
```python
    errors = simulate.draw_errors(n, err_seed, inputs["corr"],
                                  inputs["export_resid"])
    b = C.BASE
    prod = b["production"] + errors["production"]
    exp = b["exports"] * (1.0 + errors["export_pct"])
```

NEW:
```python
    from monte_carlo import export_errors as ee
    errors = _draw_errors_no_export(n, err_seed, inputs["corr"])
    es = inputs["export_shift"]
    Ahat = ee.draw_export_shifters(n, es["hist"], es["week"], es["C_w"],
                                   es["P_cur"], es["eps"],
                                   seed=err_seed + SC.EXPORT_ERR_SEED_OFFSET,
                                   purge=es["purge"])
    # multiplicative export-base factor, drop-in for (1 + export_pct):
    # Q_exp0 = Ahat * P0^eps_work, so at P0 the curve passes through the
    # inferred demand shifter. eps_work is the triangular mode, so this is
    # median-consistent when the per-draw elasticity differs.
    m_exp = Ahat * SC.P0 ** es["eps"] / C.BASE["exports"]
    b = C.BASE
    prod = b["production"] + errors["production"]
    exp = b["exports"] * m_exp
    errors["export_pct"] = m_exp - 1.0  # keep diagnostics key working
```

## New helper — `_draw_errors_no_export` (add near `draw_base_quantities`)

```python
def _draw_errors_no_export(n, seed, corr):
    """Correlated normals for production/ethanol/feed only (3x3 leading
    block of the v1 first-difference correlation matrix; LINES order is
    [production, ethanol_grind, feed_residual, exports], so exports is
    the dropped 4th row/col). The export draw is now the independent
    purged Â bootstrap -- see INTEGRATION_SPEC.md for why the old
    correlation is not carried over."""
    import numpy as np
    from monte_carlo import config as C
    from monte_carlo import simulate
    rng = np.random.default_rng(seed)
    L = np.linalg.cholesky(np.asarray(corr)[:3, :3])
    z = rng.standard_normal((n, 3)) @ L.T
    return {
        "production": z[:, 0] * C.ERROR_SD["production"],
        "ethanol_grind": z[:, 1] * C.ERROR_SD["ethanol_grind"],
        "feed_residual": z[:, 2] * C.ERROR_SD["feed_residual"],
    }
```

## Deliberate behavior changes (not bugs)

1. **Export errors are now independent of prod/eth/feed errors.** The old
   4x4 correlation came from first-differenced *finals*, which embed price
   responses — carrying it onto purged demand shifters would re-contaminate.
   If a future vintage-error pipeline yields genuine demand-shock
   correlations, reintroduce them then.
2. **The week-2 export band shrinks** (sd 33% → 22%) and now **tightens by
   week** via `export_errors.error_sd_by_week` / `fit_decay`
   (22% → 14% → 10% → ~3% at weeks 2/16/26/53). Re-running with a larger
   `CURRENT_WEEK` automatically uses that week's band. The old code had no
   week-varying option beyond recomputing residuals.
3. **The median export draw moves.** The purged week-2 inference implies
   ~2,707 M bu at $4.80 vs the WASDE 3,275 anchor (the old median implied
   ~3,151). This is the data's verdict after removing the price-driven
   pace effect — report it, don't smooth it away.
4. **2025/26 is excluded** from the estimation history (provisional year);
   estimation uses 15 clean final years, 2010/11–2024/25.
5. **Seed discipline:** one seed for the 3-dim normals, `seed+offset` for
   the Â bootstrap. Reproducibility preserved (both seeded).

## Validation to re-run after applying

- `python3 -m monte_carlo.export_errors` — all 8 checks print; charts land
  in `mc_charts/mc_export_errors_*.png`.
- `run_structural.py` base case: median price should sit near $4.75–4.80
  (the Â inference centers exports at ~2,707, so expect median ending
  stocks *above* the old v2 base — flag the move explicitly in the summary).
- Identity + solver convergence checks unchanged.
