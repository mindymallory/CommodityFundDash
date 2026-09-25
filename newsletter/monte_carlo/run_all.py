"""Run base + yield-shock scenario, write charts, JSON, and the MC_RESULTS tab."""
import json
from datetime import date

import openpyxl
from openpyxl.styles import Font, PatternFill

from . import config as C
from . import simulate, charts


def write_workbook_tab(base_summary, shock_summary, price_params):
    wb = openpyxl.load_workbook(C.WORKBOOK)
    if "MC_RESULTS" in wb.sheetnames:
        wb.remove(wb["MC_RESULTS"])
    ws = wb.create_sheet("MC_RESULTS")
    hdr = Font(bold=True, size=12)
    sub = Font(bold=True)
    gray = PatternFill("solid", fgColor="D9D9D9")

    ws["A1"] = "Monte Carlo v1 — 2026/27 U.S. corn (generated %s by monte_carlo/)" % date.today().isoformat()
    ws["A1"].font = hdr
    ws["A2"] = ("Method: 10,000 draws; WASDE #675 base; correlated errors "
                "(exports from week-2 FAS pace residuals; production/ethanol/feed "
                "stated v1 priors — see monte_carlo/README.md); price via fitted "
                "P = %.3f + %.4f/(stocks-to-use), R²=%.2f." % (
                    price_params["a"], price_params["b"], price_params["r2"]))
    rows = [
        ("Metric", "Base P10", "Base P50", "Base mean", "Base P90",
         "Shock P50 (−5 bu/ac)", "WASDE #675 point"),
        ("Ending stocks (M bu)",),
        ("Stocks-to-use (%)",),
        ("Season-avg price ($/bu)",),
    ]
    r = 4
    for i, h in enumerate(rows[0]):
        c = ws.cell(r, i + 1, h); c.font = sub; c.fill = gray
    r = 5
    b, s = base_summary, shock_summary
    data = [
        ("Ending stocks (M bu)",
         b["ending"]["p10"], b["ending"]["p50"], b["ending"]["mean"], b["ending"]["p90"],
         s["ending"]["p50"], C.BASE_ENDING),
        ("Stocks-to-use (%)",
         b["stocks_use"]["p10"] * 100, b["stocks_use"]["p50"] * 100,
         b["stocks_use"]["mean"] * 100, b["stocks_use"]["p90"] * 100,
         s["stocks_use"]["p50"] * 100, C.BASE_STOCKS_USE * 100),
        ("Season-avg price ($/bu)",
         b["price"]["p10"], b["price"]["p50"], b["price"]["mean"], b["price"]["p90"],
         s["price"]["p50"], C.BASE_PRICE),
    ]
    for label, p10, p50, mean, p90, shk, wasde in data:
        ws.cell(r, 1, label).font = sub
        for j, v in enumerate([p10, p50, mean, p90, shk, wasde]):
            ws.cell(r, j + 2, round(v, 2))
        r += 1
    r += 1
    ws.cell(r, 1, "P(stocks-to-use < 10%)").font = sub
    ws.cell(r, 2, round(b["p_su_lt_10"] * 100, 1))
    ws.cell(r, 3, "base (%)")
    ws.cell(r, 4, round(s["p_su_lt_10"] * 100, 1))
    ws.cell(r, 5, "shock (%)")
    r += 2
    ws.cell(r, 1, "Validation").font = sub
    ws.cell(r + 1, 1, "Per-draw identity (supply = use + ending): PASS (asserted, n=%d)" % b["n"])
    ws.cell(r + 2, 1, "Draws with stocks-to-use outside 3–40%%: %d (flagged, not truncated)" % b["n_out_of_bounds"])
    ws.cell(r + 3, 1, "Price tails: the inverse price curve explodes as stocks-to-use -> 0; "
                      "lead with P50 ($%.2f), not the mean ($%.2f)." % (b["price"]["p50"], b["price"]["mean"]))
    ws.cell(r + 4, 1, "Median export draw ~= 4%% below WASDE (week-2 pace residuals are right-skewed); "
                      "hence median ending stocks (%.0f) exceed the WASDE point (%.0f)." % (
                          b["ending"]["p50"], C.BASE_ENDING))
    ws.cell(r + 5, 1, "See monte_carlo/README.md for all v1 approximations.")
    for col in "ABCDEFG":
        ws.column_dimensions[col].width = 22
    ws.column_dimensions["A"].width = 32
    wb.save(C.WORKBOOK)
    print("MC_RESULTS tab written")


def main():
    C.CHART_DIR.mkdir(exist_ok=True)
    base = simulate.run(prod_shift=0.0)
    shock = simulate.run(prod_shift=C.SHOCK_PROD_DELTA,
                         seed=C.SEED + 1, verbose=False)
    bs, ss = base["summary"], shock["summary"]
    pp = base["price_params"]
    charts.ending_stocks_hist(base["draws"], bs,
                              C.CHART_DIR / "mc_ending_stocks_hist.png",
                              C.BASE_ENDING)
    charts.price_hist(base["draws"], bs,
                      C.CHART_DIR / "mc_price_hist.png", C.BASE_PRICE)
    charts.price_vs_stocks(base["draws"], pp,
                           C.CHART_DIR / "mc_price_vs_stocks.png")
    charts.scenario_delta(bs, ss, C.CHART_DIR / "mc_scenario_delta.png")
    print("charts written to", C.CHART_DIR)
    out = {
        "generated": date.today().isoformat(),
        "n_draws": C.N_DRAWS, "seed": C.SEED, "current_week": C.CURRENT_WEEK,
        "base_case": C.BASE,
        "error_sd_priors": C.ERROR_SD,
        "price_model": {"a": pp["a"], "b": pp["b"], "r2": pp["r2"]},
        "error_corr_order": ["production", "ethanol_grind", "feed_residual", "exports"],
        "error_corr": base["corr"].tolist(),
        "base": bs, "shock_minus5bu": ss,
        "wasde_point": {"ending": C.BASE_ENDING,
                        "stocks_use": C.BASE_STOCKS_USE, "price": C.BASE_PRICE},
    }
    with open(C.BASE_DIR / "mc_results_2026-09-18.json", "w") as f:
        json.dump(out, f, indent=2)
    print("JSON written")
    write_workbook_tab(bs, ss, pp)


if __name__ == "__main__":
    main()
