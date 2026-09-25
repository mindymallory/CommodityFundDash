"""One-command entry for Monte Carlo v3-world (global extension):

    cd ~/workspace/your_files/commodity-newsletter-design && python3 -m monte_carlo.run_global

Runs the six scenario presets (n=10,000, seeded/deterministic), prints
headline numbers + all validation checks (fails loudly on any violation),
writes the three charts to mc_charts/, the JSON results file, the MC_GLOBAL
workbook tab (+ CHANGELOG row), and the plain-language summary markdown.
"""
import json
from datetime import date

import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill

from . import config as C
from . import structural as S
from . import structural_config as SC
from . import world as W
from . import world_config as WC
from . import world_charts as wch

DATE = "2026-09-18"
MAIN_SCENARIOS = ["base_global", "brazil_bumper", "brazil_drought",
                  "china_surge"]
SCENARIO_LABELS = {
    "base_global": "Base (global)",
    "brazil_bumper": "Brazil bumper (+500 M bu)",
    "brazil_drought": "Brazil drought (-500 M bu)",
    "china_surge": "China surge (+200 M bu)",
    "h2_brazil_bumper": "H2 Brazil bumper (+500 M bu)",
    "h2_brazil_drought": "H2 Brazil drought (-500 M bu)",
}


def check(cond, msg):
    if not cond:
        raise AssertionError("VALIDATION FAILED: " + msg)
    print("  PASS: " + msg)


def main():
    C.CHART_DIR.mkdir(exist_ok=True)
    inputs = S.load_inputs()

    # --- China logit calibration (level allocation) ---
    cal = W.calibrate_china_lambda()
    print("China logit calibration: lambda=%.2f, US share=%.1f%% "
          "(target band 25-45%%)%s" % (
              cal["lambda"], cal["shares"]["US"] * 100,
              "" if cal["target_met"] else
              "  <-- TARGET NOT MET (see README/world.py note)"))
    print("  baseline shares: " + ", ".join(
        f"{o}={cal['shares'][o]*100:.1f}%" for o in W.ORIGINS))

    # --- Model-level checks (no randomness) ---
    vc = W.validation_checks()
    check(vc["calibration_ok"],
          f"residual export curve hits (P0, 3275): X_US($4.80)={vc['calibration_X_US_at_P0']:.1f}")
    check(vc["xs_increasing"],
          "competitor export supply increasing in P at median draws")
    check(vc["x_us_decreasing"],
          "residual US export demand decreasing in P (unique root)")

    # --- Scenarios ---
    results = {}
    for name in WC.SCENARIO_ORDER:
        results[name] = W.run_scenario(name, inputs=inputs)

    # --- v2 base for comparison (same U.S.-side seeds as base_global) ---
    v2base = S.run_scenario("base", inputs=inputs, verbose=False)
    v2s = v2base["summary"]
    gs = results["base_global"]["summary"]
    v2_exp_p50 = float(np.median(v2base["draws"]["q1"][:, 0]))
    print("\n[v2 base for comparison]")
    print("  v2  P50 price=$%.2f  P50 exports=%.0f  P(s/u<10%%)=%.1f%%" % (
        v2s["price"]["p50"], v2_exp_p50, v2s["p_su_lt_10"] * 100))
    print("  glo P50 price=$%.2f  P50 exports=%.0f  P(s/u<10%%)=%.1f%%" % (
        gs["price"]["p50"], gs["us_exports"]["p50"],
        gs["p_su_lt_10"] * 100))
    d_price = gs["price"]["p50"] - v2s["price"]["p50"]
    d_exp = gs["us_exports"]["p50"] - v2_exp_p50
    d_psu = (gs["p_su_lt_10"] - v2s["p_su_lt_10"]) * 100
    print("  delta (global - v2): price %+.2f $/bu, exports %+.0f M bu, "
          "P(s/u<10%%) %+.1f pp" % (d_price, d_exp, d_psu))

    # --- Validation: per-draw asserts already ran inside run_scenario; ---
    # --- scenario ordering on medians (fail loudly) ---
    print("\nValidation:")
    for name in WC.SCENARIO_ORDER:
        d = results[name]["draws"]
        check(d["max_solver_resid_frac"] < 1e-6,
              f"{name}: solver converged 100% (max resid {d['max_solver_resid_frac']:.1e})")
        check(d["max_identity_resid_mbu"] < 1e-3,
              f"{name}: U.S. identity holds (max {d['max_identity_resid_mbu']:.1e} M bu)")
        check(d["max_world_identity_resid_mbu"] < 1e-3,
              f"{name}: world identity holds (max {d['max_world_identity_resid_mbu']:.1e} M bu)")
        check(bool((d["us_exports"] <= d["world_imports"] + 1e-9).all()),
              f"{name}: U.S. exports <= world imports on all draws")
        if d["n_neg_us_exports"]:
            print(f"  NOTE: {name}: {d['n_neg_us_exports']} draws with "
                  "negative residual US exports (extreme high-price tail)")
        if d["n_neg_comp_ending"]:
            print(f"  NOTE: {name}: {d['n_neg_comp_ending']} draws with "
                  "negative competitor ending stocks")
    b, bu, dr, cs = (results[n]["summary"]
                     for n in MAIN_SCENARIOS)
    check(bu["price"]["p50"] < b["price"]["p50"],
          "bumper P50 price (%.2f) < base P50 (%.2f)"
          % (bu["price"]["p50"], b["price"]["p50"]))
    check(bu["us_exports"]["p50"] < b["us_exports"]["p50"],
          "bumper P50 US exports (%.0f) < base P50 (%.0f)"
          % (bu["us_exports"]["p50"], b["us_exports"]["p50"]))
    check(dr["price"]["p50"] > b["price"]["p50"],
          "drought P50 price (%.2f) > base P50 (%.2f)"
          % (dr["price"]["p50"], b["price"]["p50"]))
    check(cs["price"]["p50"] > b["price"]["p50"],
          "china_surge P50 price (%.2f) > base P50 (%.2f)"
          % (cs["price"]["p50"], b["price"]["p50"]))
    # h2 presets reproduce the +/-500 scenarios exactly (same model+seeds).
    for h2, twin in (("h2_brazil_bumper", "brazil_bumper"),
                    ("h2_brazil_drought", "brazil_drought")):
        same = np.array_equal(results[h2]["draws"]["price"],
                              results[twin]["draws"]["price"])
        check(same, f"{h2} reproduces {twin} exactly (same full-year model)")

    # --- China surge marginal capture (structural) ---
    db, ds = results["base_global"]["draws"], results["china_surge"]["draws"]
    capture = {"US": float(ds["us_exports"].mean() - db["us_exports"].mean()) / 200.0}
    for j, c in enumerate(W.COMP_ORDER):
        capture[c] = float(ds["comp"][c]["xs"].mean()
                           - db["comp"][c]["xs"].mean()) / 200.0
    print("\nChina +200 M bu surge: marginal capture by origin "
          "(Δ equilibrium exports / 200):")
    for o in ["US", "BR", "AR", "UP"]:
        print("  %s: %.1f%% (%.0f M bu)" % (o, capture[o] * 100,
                                            capture[o] * 200))
    print("  (sums to %.1f%%: the higher clearing price rations ~60 M bu of "
          "rest-of-world import demand, so only ~140 M bu of extra exports "
          "are needed)" % (sum(capture.values()) * 100))

    # --- Charts ---
    wch.price_scenarios(results, C.CHART_DIR / "mc_global_price_scenarios_v6.png")
    wch.china_capture(capture, results["china_surge"]["summary"]["china_level_shares"],
                      C.CHART_DIR / "mc_global_china_capture_v6.png")
    wch.export_curve(C.CHART_DIR / "mc_global_export_curve_v6.png")
    print("\ncharts written to", C.CHART_DIR)

    # --- Freight basis actually used (per-leg live vs fallback) ---
    freight_basis = results["base_global"]["wq"]["freight_basis"]
    legs_live, _fb2 = W._live_legs()
    fb_note = ("week ending %s; US port=%s; FREIGHT_MAX_VINTAGE_DAYS=35 "
               "(Mindy's 2026-09-18 decision: the monitor's fixture-mean legs "
               "are 4-week means by construction, so 35d keeps them live "
               "across weekly refreshes — apples to apples); live legs: %s; "
               "static-fallback legs: %s (US_PNW stale assumption; AR proxy "
               "fixture; UP no freight leg)" % (
                   freight_basis["week_ending"], freight_basis["us_port"],
                   ", ".join(o for o in W.ORIGINS
                             if o not in freight_basis["fallback_legs"])
                   or "none",
                   ", ".join(freight_basis["fallback_legs"]) or "none"))
    print("freight basis:", fb_note)

    # --- JSON ---
    out = {
        "generated": DATE,
        "model": "v3 world: global residual US export demand (v2 US model intact)",
        "n_draws": WC.N_DRAWS,
        "seeds": {"us_errors": WC.SEED_US_ERR, "us_elasticities": WC.SEED_US_ELAS,
                  "world": WC.WORLD_SEED},
        "p0": WC.P0,
        "anchors_mbu": {
            "competitors": {c: {k: WC.COMPETITORS[c][k]
                                for k in ("beg", "prod", "imp", "dom", "end",
                                          "prod_sd")}
                            for c in W.COMP_ORDER},
            "M_ROW0": WC.M_ROW0, "M_CH0": WC.M_CH0,
            "world_imports": WC.WORLD["imp"], "world_exports": WC.WORLD["exp"]},
        "timing_rule": ("Mindy's rule 2026-09-18: no H1/H2 split; competitor "
                        "production for US MY 2026/27 = harvests landing "
                        "Sep 2026-Aug 2027 (BR/AR local MY 2027/28, UP local "
                        "MY 2026/27). BR/AR anchors are local-2026/27 "
                        "productions as no-change expectation proxies "
                        "(2027/28 not published in Sep-2026 vintage); BR/AR "
                        "baseline sds are forward uncertainties (385/260 M "
                        "bu, detrended 2018-2026 volatility). Full table: "
                        "competitor_my_mapping_2026-09-18.csv"),
        "x_other_mbu": WC.X_OTHER,
        "x_other_note": ("calibration constant so X_US(P0)=3275 at median "
                         "params; ~666 M bu; the 666-vs-941 gap to implied "
                         "other-exporter exports is the PSD world "
                         "imports/exports statistical discrepancy (MY/TY)"),
        "china_lambda": cal["lambda"],
        "china_baseline_shares": cal["shares"],
        "china_landed_costs": cal["landed_costs"],
        "china_calibration_note": (
            "Logit centered on the weekly freight monitor (see freight_basis); "
            "target US share band [0.25,0.45] met=%s. As of week ending "
            "2026-09-16 the BR leg is LIVE on its 28-day fixture-mean "
            "(FREIGHT_MAX_VINTAGE_DAYS=35 per Mindy's 2026-09-18 decision "
            "that 4-week means count as live, apples-to-apples); US/AR/UP "
            "remain on static fallback (US_PNW stale assumption; AR proxy "
            "fixture; UP no freight leg). The live BR fixture mean "
            "($1.30/bu) replaces the stale static $0.45/bu, making Brazil "
            "the priciest origin in the logit — this shifts China's level "
            "allocation toward the US vs the static baseline. Level "
            "accounting only; does not affect price clearing."
            % cal["target_met"]),
        "freight_basis": {
            "live": WC.FREIGHT_LIVE,
            "us_port": freight_basis["us_port"],
            "week_ending": freight_basis["week_ending"],
            "fallback_legs": freight_basis["fallback_legs"],
            "note": fb_note,
        },
        "elasticity_priors": {
            "competitor_domestic": list(WC.DOM_ELAS_PRIOR),
            "row_import_demand": list(WC.ROW_ELAS_PRIOR),
            "china_import_demand": list(WC.CH_ELAS_PRIOR)},
        "scenarios": {n: {"spec": {k: v for k, v in WC.SCENARIOS[n].items()
                                   if k != "h2_label"},
                          "summary": results[n]["summary"]}
                      for n in WC.SCENARIO_ORDER},
        "china_surge_capture": capture,
        "v2_comparison": {
            "v2_base": {"price_p50": v2s["price"]["p50"],
                        "exports_p50": v2_exp_p50,
                        "p_su_lt_10": v2s["p_su_lt_10"]},
            "global_base": {"price_p50": gs["price"]["p50"],
                             "exports_p50": gs["us_exports"]["p50"],
                             "p_su_lt_10": gs["p_su_lt_10"]},
            "delta_global_minus_v2": {"price_p50": d_price,
                                      "exports_p50": d_exp,
                                      "p_su_lt_10_pp": d_psu}},
        "validation": {
            "solver": "100% converged all scenarios (120 bisection iters/draw)",
            "us_identity": "max |S1-(use+ending)| < 1e-3 M bu all draws",
            "world_identity": "max < 1e-3 M bu all draws",
            "exports_le_imports": "asserted per draw",
            "scenario_ordering": "bumper<base price & exports; drought>base price; surge>base price",
            "xs_increasing": vc["xs_increasing"],
            "calibration_X_US_at_P0": vc["calibration_X_US_at_P0"]},
    }
    json_path = C.BASE_DIR / ("mc_global_results_%s_v6.json" % DATE)
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2)
    print("JSON written:", json_path)

    write_workbook_tab(results, capture, cal, v2s, v2_exp_p50,
                       {"d_price": d_price, "d_exp": d_exp, "d_psu": d_psu})
    write_summary_md(results, capture, cal, v2s, v2_exp_p50,
                     {"d_price": d_price, "d_exp": d_exp, "d_psu": d_psu})
    return results


def write_workbook_tab(results, capture, cal, v2s, v2_exp_p50, deltas):
    wb = openpyxl.load_workbook(C.WORKBOOK)
    if "MC_GLOBAL" in wb.sheetnames:
        wb.remove(wb["MC_GLOBAL"])
    ws = wb.create_sheet("MC_GLOBAL")
    hdr = Font(bold=True, size=12)
    sub = Font(bold=True)
    gray = PatternFill("solid", fgColor="D9D9D9")

    ws["A1"] = ("Monte Carlo v3-world (global) — 2026/27 U.S. corn "
                "(generated %s by monte_carlo/world.py)" % DATE)
    ws["A1"].font = hdr
    ws["A2"] = ("Method: 10,000 draws/scenario; v2 U.S. structural model "
                "intact (4 domestic demand curves + stock demand, P0=$4.80); "
                "US-side export error v3 (monte_carlo/export_errors.py: "
                "purged Ahat inference, week-conditioned bands); "
                "v2's fixed export curve REPLACED by a residual export demand "
                "curve X_US(P) = M_ROW(P)+M_CH(P)-XS_BR-XS_AR-XS_UP-X_OTHER "
                "(X_OTHER~666 M bu calibration constant; competitor export "
                "supply slopes up in P via domestic demand rationing; "
                "USDA FAS PSD September 2026 vintage anchors; competitor "
                "production follows Mindy's MY-timing rule (harvests landing "
                "in our Sep-Aug window: BR/AR local MY 2027/28, UP local MY "
                "2026/27 — see competitor_my_mapping_2026-09-18.csv; BR/AR "
                "baseline sds are forward uncertainties: 385/260 M bu). "
                "China/ROW allocation uses the weekly freight monitor "
                "(monte_carlo/freight.py, INTEGRATION_SPEC_FREIGHT.md); "
                "week ending 2026-09-16 the BR leg is LIVE on its 28-day "
                "fixture-mean (FREIGHT_MAX_VINTAGE_DAYS=35 — Mindy's "
                "2026-09-18 decision that 4-week means count as live, "
                "apples-to-apples); US/AR/UP on static fallback (US_PNW "
                "stale; AR proxy; UP no freight leg) — see freight_basis "
                "in JSON. "
                "See monte_carlo/README.md (v3-world section) + "
                "INTEGRATION_SPEC.md + INTEGRATION_SPEC_FREIGHT.md.")

    r = 4
    heads = ["Scenario", "Price P10 ($/bu)", "Price P50 ($/bu)",
             "Price P90 ($/bu)", "US exports P10 (M bu)",
             "US exports P50 (M bu)", "US exports P90 (M bu)",
             "Ending P10 (M bu)", "Ending P50 (M bu)",
             "Ending P90 (M bu)", "P(s/u<10%) (%)"]
    for i, h in enumerate(heads):
        c = ws.cell(r, i + 1, h); c.font = sub; c.fill = gray
    r = 5
    for n in WC.SCENARIO_ORDER:
        s = results[n]["summary"]
        ws.cell(r, 1, SCENARIO_LABELS[n] +
                (" — same full-year model as " +
                 ("brazil_bumper" if "bumper" in n else "brazil_drought")
                 if n.startswith("h2_") else ""))
        vals = [s["price"]["p10"], s["price"]["p50"], s["price"]["p90"],
                s["us_exports"]["p10"], s["us_exports"]["p50"],
                s["us_exports"]["p90"],
                s["ending"]["p10"], s["ending"]["p50"], s["ending"]["p90"],
                s["p_su_lt_10"] * 100]
        for j, v in enumerate(vals):
            ws.cell(r, j + 2, round(v, 2 if j < 3 else (1 if j == 9 else 0)))
        r += 1

    r += 1
    ws.cell(r, 1, "China: level allocation of China's buys (logit on landed "
                  "cost, mean shares) + surge marginal capture").font = sub
    r += 1
    for i, h in enumerate(["Scenario", "US share", "BR share", "AR share",
                           "UP share", "Note"]):
        c = ws.cell(r, i + 1, h); c.font = sub; c.fill = gray
    r += 1
    for n in WC.SCENARIO_ORDER:
        sh = results[n]["summary"]["china_level_shares"]
        ws.cell(r, 1, SCENARIO_LABELS[n])
        for j, o in enumerate(["US", "BR", "AR", "UP"]):
            ws.cell(r, j + 2, round(sh[o] * 100, 1))
        ws.cell(r, 6, "lambda=%.2f; freight monitor wk ending 2026-09-16: "
                      "BR LIVE (28d fixture mean, 35d gate — Mindy's 2026-09-18 "
                      "decision); US/AR/UP static fallback (US_PNW stale; AR "
                      "proxy; UP no leg); target US-share band 25-45%% %s" % (
                          cal["lambda"],
                          "MET" if cal["target_met"] else "not met"))
        r += 1
    ws.cell(r, 1, "China +200 surge: MARGINAL capture (structural, "
                  "Δ equilibrium exports / 200)")
    for j, o in enumerate(["US", "BR", "AR", "UP"]):
        ws.cell(r, j + 2, round(capture[o] * 100, 1))
    ws.cell(r, 6, "% of the +200 M bu supplied by each origin")
    r += 2

    ws.cell(r, 1, "v2-vs-global base comparison (same U.S.-side draws; only "
                  "the export demand mechanism changes)").font = sub
    r += 1
    for i, h in enumerate(["", "v2 base", "global base", "delta (global-v2)"]):
        c = ws.cell(r, i + 1, h); c.font = sub; c.fill = gray
    r += 1
    g = results["base_global"]["summary"]
    for label, vv, gv, dv, fmt in [
            ("P50 price ($/bu)", v2s["price"]["p50"], g["price"]["p50"],
             deltas["d_price"], "%.2f"),
            ("P50 US exports (M bu)", v2_exp_p50, g["us_exports"]["p50"],
             deltas["d_exp"], "%.0f"),
            ("P(s/u<10%) (%)", v2s["p_su_lt_10"] * 100,
             g["p_su_lt_10"] * 100, deltas["d_psu"], "%.1f")]:
        ws.cell(r, 1, label)
        ws.cell(r, 2, fmt % vv); ws.cell(r, 3, fmt % gv)
        ws.cell(r, 4, fmt % dv if "pp" not in label else "%+.1f pp" % dv)
        r += 1
    ws.cell(r, 1, "On P(s/u<10%) vs v2's 61.5%: the export pace-residual draw "
                  "(sd ~29%) is dropped since exports are endogenous, but the "
                  "residual curve is anchored at the WASDE 3275 export level "
                  "while v2's median week-2 pace draw sat ~4% below it "
                  "(~3,151) — the level effect dominates. See README.")

    r += 2
    ws.cell(r, 1, "Validation").font = sub
    r += 1
    vlines = [
        "Solver: 100% of draws converged, all scenarios (120 bisection "
        "iterations/draw).",
        "U.S. identity: max |supply-(use+ending)| < 1e-3 M bu, all draws.",
        "World identity: max < 1e-3 M bu, all draws (US/BR/AR/UP modeled; "
        "rest-of-world fixed at Sep-2026 vintage, ending defined residually).",
        "U.S. exports <= world imports on every draw (holds by construction).",
        "Ordering: bumper lowers P50 price AND P50 US exports vs base; "
        "drought raises P50 price; china_surge raises P50 price.",
        "Residual export curve passes through the WASDE point ($4.80, 3275) "
        "at median parameters by construction (X_OTHER calibration).",
        "Competitor export supply verified increasing in P at median draws.",
    ]
    for v in vlines:
        ws.cell(r, 1, v); r += 1
    r += 1
    ws.cell(r, 1, "See monte_carlo/README.md (v3-world section) for data "
                  "sources, the China allocation rule, seasonality "
                  "treatment, and all documented assumptions.")
    for col in "ABCDEFGHIJK":
        ws.column_dimensions[col].width = 22
    ws.column_dimensions["A"].width = 46
    wb.save(C.WORKBOOK)
    print("MC_GLOBAL tab written")

    # CHANGELOG row (append-only; no other tab touched). Idempotent: skip if
    # the last row already records this run.
    ws = wb["CHANGELOG"]
    if not (str(ws.cell(ws.max_row, 2).value).startswith("MC world module (v6")
            and str(ws.cell(ws.max_row, 1).value) == DATE):
        nr = ws.max_row + 1
        ws.cell(nr, 1, DATE)
        ws.cell(nr, 2, "MC world module (v6: BR freight leg live)")
        ws.cell(nr, 3, "FREIGHT_MAX_VINTAGE_DAYS 14 -> 35 per Mindy's "
                       "2026-09-18 decision: the freight monitor's fixture-mean "
                       "legs are 4-week means by construction, so 35d keeps "
                       "them live across weekly refreshes (apples to apples). "
                       "Week ending 2026-09-16: BR leg is LIVE on its 28-day "
                       "fixture mean (spread -0.36 $/bu vs Gulf, freight "
                       "$1.30/bu — replacing the stale static $0.45/bu, which "
                       "makes Brazil the priciest origin in the China logit); "
                       "US/AR/UP remain on static fallback (US_PNW stale "
                       "assumption; AR proxy fixture; UP no freight leg). "
                       "China/ROW logit centers on live legs "
                       "(monte_carlo/freight.py; INTEGRATION_SPEC_FREIGHT.md). "
                       "Fallback legs recorded per run in JSON freight_basis. "
                       "MC_GLOBAL tab + charts regenerated as v6.")
        ws.cell(nr, 4, "China level allocation shifts toward the US vs the "
                       "static baseline (live BR freight is ~3x the stale "
                       "static value). Price clearing unchanged (allocation "
                       "is level accounting). No changes to other tabs.")
        print("CHANGELOG row appended")
    else:
        print("CHANGELOG row already present; skipped")
    wb.save(C.WORKBOOK)


def write_summary_md(results, capture, cal, v2s, v2_exp_p50, deltas):
    L = []
    A = L.append
    A("# Monte Carlo v3-world (global) — results summary, BR freight leg live (2026-09-18)\n")
    A("The v2 U.S. structural model is kept intact; v2's fixed export demand "
      "curve is replaced by a **residual export demand curve** built from a "
      "world module: the world wants `M_ROW(P) + M_CH(P)` of imports, Brazil / "
      "Argentina / Ukraine supply `XS_i(P)` (upward-sloping in price through "
      "domestic demand rationing), a fixed ~666 M bu goes to other exporters, "
      "and the U.S. gets the residual. 10,000 draws per scenario, seeded and "
      "deterministic.\n")
    A("## Headline numbers (P50)\n")
    A("| Scenario | U.S. price ($/bu) | U.S. exports (M bu) | Ending stocks (M bu) | P(s/u<10%) |")
    A("|---|---|---|---|---|")
    for n in WC.SCENARIO_ORDER:
        s = results[n]["summary"]
        A("| %s | %.2f | %.0f | %.0f | %.1f%% |" % (
            SCENARIO_LABELS[n], s["price"]["p50"], s["us_exports"]["p50"],
            s["ending"]["p50"], s["p_su_lt_10"] * 100))
    A("")
    A("## China +200 M bu surge: who supplies the marginal bushels?\n")
    A("Structural marginal capture (Δ equilibrium exports ÷ 200):")
    for o in ["US", "BR", "AR", "UP"]:
        A(f"- {o}: {capture[o]*100:.1f}% ({capture[o]*200:.0f} M bu)")
    A("")
    A("Level allocation of China's total buys (logit on landed cost, "
      "lambda=%.2f): " % cal["lambda"] + ", ".join(
          f"{o} {cal['shares'][o]*100:.1f}%" for o in W.ORIGINS) + ".")
    A("Note: the logit now reads the weekly freight monitor's legs "
      "(week ending 2026-09-16), with per-leg fallback to the static "
      "priors. FREIGHT_MAX_VINTAGE_DAYS is 35 (Mindy's 2026-09-18 decision: "
      "the monitor's fixture-mean legs are 4-week means by construction, so "
      "35 days keeps them live across weekly refreshes — apples to apples). "
      "This week the BR leg is LIVE on its 28-day fixture mean (spread "
      "-0.36 $/bu vs Gulf, freight $1.30/bu — replacing the stale static "
      "$0.45/bu); US/AR/UP remain on static fallback (US_PNW stale "
      "assumption, AR proxy fixture, UP no freight leg). The live BR "
      "fixture makes Brazil the priciest origin in the logit, shifting "
      "China's level allocation toward the US vs the static baseline. "
      "Fallback legs are recorded per run in the JSON freight_basis. This "
      "affects only the level accounting, not price clearing.\n")
    A("## v2-vs-global validation (base)\n")
    A("Same U.S.-side draws as v2 base (identical seeds); only the export "
      "demand mechanism changes, so deltas isolate curve-shape effects:")
    A(f"- P50 price: v2 ${v2s['price']['p50']:.2f} → global "
      f"${results['base_global']['summary']['price']['p50']:.2f} "
      f"(Δ {deltas['d_price']:+.2f})")
    A(f"- P50 U.S. exports: v2 {v2_exp_p50:.0f} → global "
      f"{results['base_global']['summary']['us_exports']['p50']:.0f} "
      f"(Δ {deltas['d_exp']:+.0f} M bu)")
    A(f"- P(s/u<10%): v2 {v2s['p_su_lt_10']*100:.1f}% → global "
      f"{results['base_global']['summary']['p_su_lt_10']*100:.1f}% "
      f"(Δ {deltas['d_psu']:+.1f} pp). It RISES, not falls: the week-2 export "
      "pace-residual draw (sd ~29%) is dropped, but the residual curve is "
      "anchored at the WASDE 3275 export level while v2's median pace draw "
      "sat ~4% below it (~3,151) — week-2 pace typically understates final "
      "exports. The level effect dominates the variance effect: the global "
      "distribution is tighter but centered on a tighter sheet.\n")
    A("## Key assumptions and data gaps\n")
    A("- Anchors: USDA FAS PSD September 2026 vintage (staged "
      "`psd_corn_world_stage_2026-09-18.csv`); all 2026/27 country identities "
      "verified at staging.")
    A("- Competitor export supply slopes up in price ONLY through domestic "
      "demand rationing; competitor carry demand is fixed at September-vintage "
      "ending stocks (the `kval` term — needed so the residual curve passes "
      "through the WASDE point).")
    A("- Competitor timing (Mindy's rule, 2026-09-18): no H1/H2 split — "
      "competitor production = harvests landing in OUR Sep-Aug window: BR "
      "local MY 2027/28 (first crop Feb-Apr 2027 + safrinha Jun-Aug 2027), "
      "AR local MY 2027/28 (Mar-Jun 2027), UP local MY 2026/27 (Sep-Nov "
      "2026). Full table: competitor_my_mapping_2026-09-18.csv. BR/AR "
      "baseline sds are FORWARD uncertainties (385/260 M bu, detrended "
      "historical volatility — the competing crops are unplanted in Sep "
      "2026); the ±500 scenarios ARE the named forward-safrinha scenarios. "
      "PSD does not split first/safrinha crops (Brazil safrinha ≈78% is "
      "narrative only).")
    A("- Full-year clearing model (Mindy: no H1/H2 split of the marketing "
      "year). The h2_ presets are the same full-year model as the ±500 "
      "scenarios; the labels are kept only for the newsletter's seasonal "
      "framing — no separate mechanism, none faked.")
    A("- Rest-of-world held fixed at September-vintage levels; X_OTHER's "
      "666-vs-941 gap is the PSD world imports/exports statistical "
      "discrepancy (MY/TY timing).")
    A("- No as-published WASDE vintage CSVs yet: U.S.-side error sds are "
      "still v1's stated priors; elasticities are literature-range "
      "triangular priors (foreign elasticities are v1-world choices).")
    with open(C.BASE_DIR / ("mc_global_summary_%s_v6.md" % DATE), "w") as f:
        f.write("\n".join(L) + "\n")
    print("summary markdown written")


if __name__ == "__main__":
    main()
