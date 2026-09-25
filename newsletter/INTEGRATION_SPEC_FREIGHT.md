# INTEGRATION_SPEC_FREIGHT — feed live landed costs into world.py

**Do NOT edit `world.py` / `world_config.py` directly from this spec.**
Another agent owns those files. Apply the diffs below there.

## What the freight monitor provides

`monte_carlo/freight.py::get_landed_costs(dest="CN")` reads the latest
`freight_landed_stage_<date>.csv` (auto-discovered; no filename hard-code)
and returns, per origin (`US_GULF`, `US_PNW`, `BR`, `AR`, `UP`):

```python
{
  "fob_bu":        float | None,   # FOB in $/bu (mt value / 39.368)
  "freight_bu":    float | None,   # ocean freight in $/bu
  "landed_bu":     float | None,   # fob + freight, $/bu
  "fob_spread_bu": float | None,   # (fob - US_GULF fob) in $/bu
  "vintage_days":  int | None,     # age of the older of FOB/freight legs
  "stale":         bool,           # ANY flag set (proxy/assumption/n/a/age)
  "flag":          str,            # e.g. "proxy", "assumption;stale", ""
  "week_ending":   "2026-09-16",
}
```

Current values (week ending 2026-09-16), for reference:

| origin  | fob $/bu | freight $/bu | landed $/bu | flag |
|---------|-----------|--------------|-------------|------|
| US_GULF | 6.40      | 1.89         | 8.29        | (live) |
| US_PNW  | 5.99      | 0.89         | 6.88        | assumption;stale |
| BR      | 6.05      | 1.30         | 7.34        | (live) |
| AR      | 5.56      | 1.30         | 6.86        | proxy |
| UP      | 5.66      | n/a          | n/a         | n/a (no freight leg) |

Note the old static config (`CHINA_FREIGHT US 0.55 $/bu`) is ~3.4x stale
vs the live Gulf→China fixture mean ($74.5/mt = $1.89/bu). This is the
calibration miss.

## Diffs

### 1. `world_config.py` — append after the China allocation block

```python
# --- Live freight legs (monte_carlo/freight.py monitor) ---
# When True, china_shares() centers the logit on the freight monitor's
# latest staged week instead of the static spreads below. Per-leg
# fallback keeps the model runnable when a leg is missing or stale.
FREIGHT_LIVE = True
FREIGHT_US_PORT = "PNW"      # which US outlet represents "US": "GULF" | "PNW"
FREIGHT_MAX_VINTAGE_DAYS = 14
# Static fallbacks = the old v1-world choices, kept verbatim ($/bu).
FREIGHT_FALLBACK_SPREADS = {"US": 0.0, "BR": -0.25, "AR": -0.20, "UP": -0.45}
FREIGHT_FALLBACK_FREIGHT = {"US": 0.55, "BR": 0.45, "AR": 0.50, "UP": 0.65}
```

### 2. `world.py` — imports (top of file)

```python
from monte_carlo import freight as _FREIGHT  # live landed-cost monitor
```

### 3. `world.py` — `draw_world_quantities()`, replacing lines ~115-119

Replace:

```python
    # China FOB spread draws per origin (sd 0.10), ORIGINS order.
    spreads = np.column_stack([
        np.full(n, WC.CHINA_FOB_SPREADS[o])
        + rng.standard_normal(n) * WC.CHINA_SPREAD_SD
        for o in ORIGINS])
```

with:

```python
    # China FOB spread draws per origin (sd 0.10), ORIGINS order.
    # Centered on the freight monitor's live week when available;
    # per-leg fallback to the static priors when a leg is missing/stale.
    _legs, _fb = _live_legs()
    spreads = np.column_stack([
        np.full(n, _legs["spreads"][o])
        + rng.standard_normal(n) * WC.CHINA_SPREAD_SD
        for o in ORIGINS])
```

and add `"freight": _legs["freight"]` to the returned dict (next to
`"spreads": spreads`).

### 4. `world.py` — new helper (place above `draw_world_quantities`)

```python
def _live_legs():
    """Return ({'spreads': {o: $/bu}, 'freight': {o: $/bu}}, [fallback legs]).

    Falls back per-leg to FREIGHT_FALLBACK_* when the monitor is off, the
    staged CSV is missing, a leg value is None, or the leg vintage exceeds
    FREIGHT_MAX_VINTAGE_DAYS. Never raises: the model must stay runnable.
    """
    fb_spreads = dict(WC.FREIGHT_FALLBACK_SPREADS)
    fb_freight = dict(WC.FREIGHT_FALLBACK_FREIGHT)
    if not WC.FREIGHT_LIVE:
        return {"spreads": fb_spreads, "freight": fb_freight}, list(ORIGINS)
    try:
        legs = _FREIGHT.get_landed_costs("CN")
    except (FileNotFoundError, OSError):
        print("freight monitor: no staged CSV; using static spreads")
        return {"spreads": fb_spreads, "freight": fb_freight}, list(ORIGINS)
    us_key = "US_" + WC.FREIGHT_US_PORT          # "US_GULF" | "US_PNW"
    fmap = {"US": us_key, "BR": "BR", "AR": "AR", "UP": "UP"}
    out_sp, out_fr, fell_back = {}, {}, []
    for o in ORIGINS:
        lg = legs.get(fmap[o], {})
        sp = lg.get("fob_spread_bu")
        fr = lg.get("freight_bu")
        ok = (sp is not None and fr is not None
              and not lg.get("stale", True)
              and (lg.get("vintage_days") or 10**9)
              <= WC.FREIGHT_MAX_VINTAGE_DAYS)
        if o == "US":
            sp = 0.0 if ok else fb_spreads[o]   # US spread is 0 by defn
        out_sp[o] = sp if (ok or o == "US" and sp == 0.0) else fb_spreads[o]
        out_fr[o] = fr if ok else fb_freight[o]
        if not ok:
            fell_back.append(o)
    if fell_back:
        print("freight monitor: static fallback for legs: %s"
              % ",".join(fell_back))
    return {"spreads": out_sp, "freight": out_fr}, fell_back
```

Note: `fob_spread_bu` from the monitor is vs US_GULF; when
`FREIGHT_US_PORT="PNW"`, the US spread is 0.0 by definition and the
competitor spreads stay vs Gulf — document this basis choice in the
run log (it only shifts the logit intercept, which λ absorbs).

### 5. `world.py` — `china_shares()` (line ~216)

Replace:

```python
    landed = np.column_stack([
        wq["spreads"][:, j] + WC.CHINA_FREIGHT[o]
        for j, o in enumerate(ORIGINS)])
```

with:

```python
    landed = np.column_stack([
        wq["spreads"][:, j] + wq["freight"][o]
        for j, o in enumerate(ORIGINS)])
```

### 6. Results JSON — record what was used

In `run_global.py` (or wherever the results dict is built), add:

```python
results["freight_basis"] = {
    "live": WC.FREIGHT_LIVE,
    "us_port": WC.FREIGHT_US_PORT,
    "week_ending": <from _live_legs / get_landed_costs>,
    "fallback_legs": _fb,   # returned by _live_legs; [] = all live
}
```

## Calibration note for the integrator

With live legs the US_GULF landed cost ($8.29/bu) is the highest origin
by ~$0.95/bu — the old README calibration note ("US share at most 25%,
target band unreachable") gets *more* stark via Gulf. Via PNW
(`FREIGHT_US_PORT="PNW"`, US landed $6.88/bu) the US is the *cheapest*
origin. Re-run the λ calibration check after wiring and update the
README's China-allocation section with the new finding; do not silently
keep the old note.

## What this does NOT change

- The logit noise structure (`CHINA_SPREAD_SD = 0.10`, `CHINA_LAMBDA`).
- Market clearing: the allocation is still level accounting on top of
  the residual-export-demand clearing, per the v3-world README.
- `simulate.py` (v1) — untouched.
