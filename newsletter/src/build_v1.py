#!/usr/bin/env python3
"""Build US_Corn_History_and_Pace_v1.xlsx — analyst-grade history + pace-forecasting workbook."""
import json
from copy import copy
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import CellIsRule

SRC = '/home/hatch/workspace/your_files/commodity-newsletter-design/src/'
OUT = '/home/hatch/workspace/your_files/commodity-newsletter-design/US_Corn_History_and_Pace_v1.xlsx'

rows = json.load(open(SRC + 'corn_history.json'))

wb = Workbook()

HDR_FILL = PatternFill('solid', fgColor='1F4E5F')
HDR_FONT = Font(bold=True, color='FFFFFF', size=10)
TITLE_FONT = Font(bold=True, size=13, color='1F4E5F')
NOTE_FONT = Font(italic=True, size=9, color='555555')
FLAG_FILL = PatternFill('solid', fgColor='F4CCCC')
INPUT_FILL = PatternFill('solid', fgColor='FFF2CC')
GAP_FILL = PatternFill('solid', fgColor='E8E8E8')
GAP_FONT = Font(italic=True, color='888888', size=9)
PROJ_FILL = PatternFill('solid', fgColor='D9E2F3')
thin = Side(style='thin', color='BFBFBF')
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical='top')
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)

def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HDR_FILL; cell.font = HDR_FONT; cell.alignment = CENTER
        cell.border = BORDER

def title_block(ws, title, note, ncols):
    ws['A1'] = title; ws['A1'].font = TITLE_FONT
    ws['A2'] = note; ws['A2'].font = NOTE_FONT; ws['A2'].alignment = WRAP
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    ws.row_dimensions[2].height = 30

def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[get_column_letter(col)].width = w

# ================================================================= TAB 1: README
ws = wb.active; ws.title = 'README'
ws.sheet_properties.tabColor = '1F4E5F'
lines = [
 ("US Corn History & Pace Forecaster — v1", TITLE_FONT),
 ("What v1 adds over Phase 0: (1) FULL 16-year U.S. corn balance-sheet history (2010/11–2025/26) from the ERS Feed Grains Database — every cell sourced, identity-checked; (2) PACE_EXPORT — weekly export-commitment S-curve forecaster; (3) PACE_ETHANOL — weekly EIA-production-implied corn grind tracker; (4) PACE_FEED — quarterly Grain-Stocks-implied feed & residual calculator; (5) VALIDATE + CHANGELOG carried over. Phase 0 was a single-vintage shell; this is the analyst workbook.", None),
 ("DATA SOURCES (every historical cell traces to one of these):", Font(bold=True, size=11)),
 ("1. ERS Feed Grains Database — Yearbook tables, all years (CSV). https://www.ers.usda.gov/data-products/feed-grains-database/feed-grains-yearbook-tables — file: feed-grains-yearbook-tables-all-years.csv — downloaded 2026-09-18. Tables used: Table 1 (acreage/yield/price), Table 4 (corn supply & disappearance), Table 31 (alcohol for fuel use = ethanol grind). Covers HIST_BALANCE 2010/11–2025/26. Cross-checked: 2024/25 finals and 2025/26 estimates match WASDE #675 exactly.", None),
 ("2. WASDE #675 (Sep 11, 2026), text: https://www.usda.gov/oce/commodity/wasde/wasde0926.txt — 2026/27 projection column + Aug→Sep vintage diff in VALIDATE.", None),
 ("3. Weekly export sales seeds: Dow Jones Newswires via TradingView 2026-09-11 (wk ending Aug 31/Sep 1–3: 15.597 MMT carried over, 1.929 MMT new 2026/27 sales, 0.775 MMT Sep 1–3 exports); Barchart 2026-09-17 (wk ending Sep 10: 1.027 MMT net sales); Barchart/TradingView 2026-09-14 (export inspections 1.525 MMT wk of Sep 10; 2.174 MMT first 10 days of MY).", None),
 ("4. Weekly ethanol seeds: DTN 2026-09-02 (1.110M bpd wk ending Aug 28); DTN 2026-09-10 (1.099M bpd wk ending Sep 4); Dow Jones via TradingView 2026-09-16 (1.099M bpd wk ending Sep 11).", None),
 ("", None),
 ("PACE / S-CURVE METHODOLOGY (plain English):", Font(bold=True, size=11)),
 ("Demand doesn't arrive evenly — exports surge in fall, ethanol runs steady, feed use follows livestock cycles. The S-curve captures each category's TYPICAL seasonal shape: for every week of the marketing year, what % of the FINAL annual total had historically been committed/ground by that week? Average that % across 5–10 years and you get the curve (plus min/max bands). Then each new week: IMPLIED FINAL = current cumulative pace ÷ historical % for that week. If implied final > WASDE's line, demand is running hot and WASDE will likely revise up. The pace tabs do this live — you enter the weekly print, the workbook implies the final.", None),
 ("Conversions: corn 1 metric ton = 39.368 bushels. Ethanol: weekly corn grind (M bu) = EIA production (thou bpd) × 7 days × 42 gal/bbl ÷ (gal-per-bushel × 1000); gal-per-bushel is a parameter cell (default 2.90 — calibrate against NASS Grain Crushings). MY week 1 = first week ending in September.", None),
 ("", None),
 ("ACTIVATING FULL S-CURVES (the reference tables are marked TO FIT until then):", Font(bold=True, size=11)),
 ("A. Export sales history: get a FREE FAS Open Data API key via https://api.data.gov/signup/ (select FAS), then pull weekly corn outstanding sales + accumulated exports from api.fas.usda.gov (5–10 marketing years, keyless bulk history is not available — the old query system is dead). For each MY week compute cumulative commitments ÷ that year's FINAL exports; average/min/max across years → paste into PACE_EXPORT's S-curve table. Formulas and charts go live automatically.", None),
 ("B. Ethanol history: free EIA key via https://www.eia.gov/opendata/register.php, or the 'Download Data (XLS File)' link on the EIA series page: https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=W_EPOOXE_YOP_NUS_MBBLD&f=W (Weekly U.S. Fuel Ethanol Plant Production). Weekly 2010→present → seasonal % of annual grind by MY week → paste into PACE_ETHANOL's S-curve table.", None),
 ("C. Feed & residual needs no S-curve: it's the residual. Enter each quarterly Grain Stocks print (NASS: Jan 12, Mar 31, Jun 30, Sep 30) plus quarterly exports/grind into PACE_FEED; implied quarterly F&R = (beg stocks [+ production in Q1] − end stocks − exports − grind − other FSI).", None),
 ("", None),
 ("HONEST GAPS (blank + flagged, never invented): weekly export & ethanol history (need the free API keys above); Dec-1-2025 / Mar-1-2026 / Jun-1-2026 Grain Stocks prints (enter on release); quarterly 2025/26 exports & grind splits (enter from FAS/Census/EIA); gal-per-bushel conversion (parameter to calibrate).", None),
]
r = 1
for text, font in lines:
    c = ws.cell(row=r, column=1, value=text)
    c.alignment = WRAP
    if font: c.font = font
    ws.row_dimensions[r].height = 15 if not text else (28 if len(text) < 120 else 58)
    r += 1
ws.column_dimensions['A'].width = 150
ws.sheet_properties.pageSetUpPr = None

# ======================================================== TAB 2: HIST_BALANCE
ws = wb.create_sheet('HIST_BALANCE'); ws.sheet_properties.tabColor = '2E7D32'
headers = ['Marketing year','Planted (M ac)','Harvested (M ac)','Yield (bu/ac)',
 'Beginning stocks (M bu)','Production (M bu)','Imports (M bu)','Supply, total (M bu)',
 'Feed & residual (M bu)','Food/Seed/Industrial (M bu)','Ethanol grind (M bu)','Exports (M bu)',
 'Total use (M bu)','Ending stocks (M bu)','Stocks/use %','Season avg price ($/bu)','Identity check']
NC = len(headers)
title_block(ws, 'U.S. Corn Balance Sheet — History 2010/11–2025/26',
 'Source: ERS Feed Grains Database yearbook tables (Table 1, Table 4, Table 31), downloaded 2026-09-18. FSI = Food/alcohol/industrial + seed. 2026/27 row = Sep WASDE #675 projection (blue).', NC)
hr = 3
for i, h in enumerate(headers, 1): ws.cell(row=hr, column=i, value=h)
style_header(ws, hr, NC)
for j, x in enumerate(rows):
    rr = 4 + j
    vals = [x['my'], x['planted'], x['harvested'], x['yield'], x['beg'], x['prod'], x['imp'],
            x['supply'], x['feed'], x['fsi'], x['ethanol'], x['exports'], x['tuse'], x['end']]
    for i, v in enumerate(vals, 1):
        c = ws.cell(row=rr, column=i, value=v); c.border = BORDER
        c.number_format = '#,##0.0' if i > 1 else '@'
    ws.cell(row=rr, column=15, value=f'=IF(N{rr}=0,"",N{rr}/M{rr})').number_format = '0.0%'  # stocks/use
    ws.cell(row=rr, column=15).border = BORDER
    ws.cell(row=rr, column=16, value=x['price']).number_format = '$#,##0.00'; ws.cell(row=rr, column=16).border = BORDER
    ws.cell(row=rr, column=17, value=f'=H{rr}-M{rr}-N{rr}').number_format = '#,##0.0'; ws.cell(row=rr, column=17).border = BORDER
# 2026/27 projection row (Sep WASDE #675)
pr = 4 + len(rows)
pv = ['2026/27 Proj (Sep WASDE)', 96.8, 88.5, 178.5, 1922, 15800, 25, 17747, 5950, 6955, 5600, 3275, 16180, 1567]
for i, v in enumerate(pv, 1):
    c = ws.cell(row=pr, column=i, value=v); c.border = BORDER; c.fill = PROJ_FILL
    c.number_format = '#,##0.0' if i > 1 else '@'
ws.cell(row=pr, column=15, value=f'=N{pr}/M{pr}').number_format = '0.0%'; ws.cell(row=pr, column=15).border = BORDER; ws.cell(row=pr, column=15).fill = PROJ_FILL
ws.cell(row=pr, column=16, value=4.80).number_format = '$#,##0.00'; ws.cell(row=pr, column=16).border = BORDER; ws.cell(row=pr, column=16).fill = PROJ_FILL
ws.cell(row=pr, column=17, value=f'=H{pr}-M{pr}-N{pr}').number_format = '#,##0.0'; ws.cell(row=pr, column=17).border = BORDER; ws.cell(row=pr, column=17).fill = PROJ_FILL
ws.conditional_formatting.add(f'Q4:Q{pr}', CellIsRule(operator='notEqual', formula=['0'], fill=FLAG_FILL))
ws.freeze_panes = 'A4'
ws.auto_filter.ref = f'A{hr}:{get_column_letter(NC)}{pr}'
widths(ws, {1:20, 2:12, 3:12, 4:11, 5:14, 6:13, 7:11, 8:13, 9:14, 10:16, 11:13, 12:12, 13:13, 14:13, 15:11, 16:14, 17:12})
# Chart: stocks/use % vs price
c1 = LineChart(); c1.title = 'U.S. corn: stocks-to-use vs season-average price'; c1.style = 10
c1.y_axis.title = 'Stocks/use %'; c1.x_axis.title = 'Marketing year'; c1.height = 7.5; c1.width = 15
d1 = Reference(ws, min_col=15, min_row=hr, max_row=pr); cats = Reference(ws, min_col=1, min_row=4, max_row=pr)
c1.add_data(d1, titles_from_data=True); c1.set_categories(cats)
c2 = LineChart(); d2 = Reference(ws, min_col=16, min_row=hr, max_row=pr); c2.add_data(d2, titles_from_data=True)
c2.y_axis.axId = 200; c2.y_axis.title = 'Price $/bu'; c2.y_axis.crosses = 'max'
c1 += c2
ws.add_chart(c1, f'A{pr+3}')

# ======================================================== TAB 3: PACE_EXPORT
ws = wb.create_sheet('PACE_EXPORT'); ws.sheet_properties.tabColor = '1565C0'
title_block(ws, 'Export pace forecaster — S-curve method',
 'METHOD: each week, total commitments = outstanding sales + accumulated exports. Implied final = commitments ÷ historical avg % of final for that MY week. If implied final > WASDE export line (3,275 M bu), demand is running hot. Historical S-curve table is TO FIT (needs free FAS API key — see README). Conversions: 1 MT corn = 39.368 bu.', 9)
# --- input block
ir = 4
in_hdr = ['Week-ending date','MY week #','Outstanding sales (MMT)','Accumulated exports (MMT)','Source / note',
          'Total commitments (MMT)','Total commitments (M bu)','Implied final exports (M bu)','vs WASDE 3,275']
for i, h in enumerate(in_hdr, 1): ws.cell(row=ir, column=i, value=h)
style_header(ws, ir, 9)
seed = [
 ('2026-09-03', 1, 17.526, 0.775, 'DJN via TradingView 2026-09-11: 15.597 carryover + 1.929 new sales (analyst sum); 0.775 Sep 1–3 exports'),
 ('2026-09-10', 2, 18.553, 2.174, 'Barchart 2026-09-17: +1.027 net sales (analyst sum); accum = export inspections 1.525 wk + prior (flag: inspections ≠ sales-based accum)'),
]
for k, (d, wk, out, acc, src) in enumerate(seed):
    rr = ir + 1 + k
    ws.cell(row=rr, column=1, value=d).number_format = 'yyyy-mm-dd'
    ws.cell(row=rr, column=2, value=wk)
    for col, v in ((3, out), (4, acc)):
        c = ws.cell(row=rr, column=col, value=v); c.number_format = '#,##0.000'; c.fill = INPUT_FILL; c.border = BORDER
    ws.cell(row=rr, column=5, value=src).font = NOTE_FONT; ws.cell(row=rr, column=5).alignment = WRAP
    ws.cell(row=rr, column=6, value=f'=C{rr}+D{rr}').number_format = '#,##0.000'; ws.cell(row=rr, column=6).border = BORDER
    ws.cell(row=rr, column=7, value=f'=F{rr}*39.368').number_format = '#,##0'; ws.cell(row=rr, column=7).border = BORDER
    ws.cell(row=rr, column=8, value=f'=IFERROR(G{rr}/VLOOKUP(B{rr},$K$5:$N$56,2,FALSE),"fit S-curve")'); ws.cell(row=rr, column=8).border = BORDER
    ws.cell(row=rr, column=9, value=f'=IF(ISNUMBER(H{rr}),H{rr}-3275,"")').number_format = '#,##0'; ws.cell(row=rr, column=9).border = BORDER
    for col in (1, 2, 5): ws.cell(row=rr, column=col).border = BORDER
for k in range(2, 52):
    rr = ir + 1 + k
    for col in (1, 2, 3, 4, 5):
        c = ws.cell(row=rr, column=col); c.border = BORDER
        if col in (3, 4): c.fill = INPUT_FILL; c.number_format = '#,##0.000'
    ws.cell(row=rr, column=6, value=f'=C{rr}+D{rr}').number_format = '#,##0.000'; ws.cell(row=rr, column=6).border = BORDER
    ws.cell(row=rr, column=7, value=f'=F{rr}*39.368').number_format = '#,##0'; ws.cell(row=rr, column=7).border = BORDER
    ws.cell(row=rr, column=8, value=f'=IFERROR(G{rr}/VLOOKUP(B{rr},$K$5:$N$56,2,FALSE),"fit S-curve")'); ws.cell(row=rr, column=8).border = BORDER
    ws.cell(row=rr, column=9, value=f'=IF(ISNUMBER(H{rr}),H{rr}-3275,"")').number_format = '#,##0'; ws.cell(row=rr, column=9).border = BORDER
ws.freeze_panes = 'A5'
widths(ws, {1:14, 2:9, 3:16, 4:17, 5:52, 6:16, 7:16, 8:18, 9:13, 11:9, 12:11, 13:9, 14:9})
# --- S-curve reference table (K:N)
ws['K4'] = 'S-CURVE REFERENCE (TO FIT — needs FAS API key; see README)'; ws['K4'].font = Font(bold=True, size=10, color='9C0006')
for i, h in enumerate(['MY week', 'Avg % of final', 'Min %', 'Max %'], 11): ws.cell(row=4, column=i, value=h)
style_header(ws, 4, 14)
for w in range(1, 53):
    rr = 4 + w
    ws.cell(row=rr, column=11, value=w).border = BORDER
    for col in (12, 13, 14):
        c = ws.cell(row=rr, column=col); c.border = BORDER; c.fill = GAP_FILL
    ws.cell(row=rr, column=12).value = None
ws['K57'] = 'STATUS: historical fit pending — paste fitted avg/min/max % here after FAS API pull.'; ws['K57'].font = GAP_FONT
# --- chart: current MY cumulative commitments vs bands
ch = LineChart(); ch.title = 'Export commitments pace: 2026/27 vs historical S-curve'; ch.style = 10
ch.y_axis.title = 'M bu'; ch.x_axis.title = 'MY week'; ch.height = 7.5; ch.width = 15
ch.add_data(Reference(ws, min_col=7, min_row=ir, max_row=ir + 52), titles_from_data=True)
ch.set_categories(Reference(ws, min_col=2, min_row=ir + 1, max_row=ir + 52))
ws.add_chart(ch, 'A60')

# ======================================================== TAB 4: PACE_ETHANOL
ws = wb.create_sheet('PACE_ETHANOL'); ws.sheet_properties.tabColor = 'EF6C00'
title_block(ws, 'Ethanol grind pace tracker — weekly EIA production → implied corn grind',
 'METHOD: weekly corn grind (M bu) = EIA production (thou bpd) × 7 × 42 ÷ (gal-per-bu × 1000). Compare cumulative grind and annualized pace vs WASDE ethanol line (5,600 M bu, Sep WASDE). Seasonal S-curve table is TO FIT (needs EIA weekly history — free key or XLS download; see README). gal-per-bushel is a parameter: calibrate against NASS Grain Crushings.', 9)
ws['A4'] = 'Gal ethanol per bushel of corn (parameter — calibrate vs NASS Grain Crushings):'; ws['A4'].font = Font(bold=True, size=10)
ws['C4'] = 2.90; ws['C4'].fill = INPUT_FILL; ws['C4'].font = Font(bold=True); ws['C4'].border = BORDER
ws['A5'] = 'WASDE 2026/27 ethanol & by-products line (M bu):'; ws['E5'] = 5600; ws['E5'].font = Font(bold=True)
ir = 7
in_hdr = ['Week-ending date','MY week #','EIA production (thou bpd)','Source','Implied corn grind (M bu/wk)',
          'Cumulative grind (M bu)','Annualized pace (M bu)','vs WASDE 5,600','Note']
for i, h in enumerate(in_hdr, 1): ws.cell(row=ir, column=i, value=h)
style_header(ws, ir, 9)
eseed = [
 ('2026-08-28', 0, 1110, 'DTN 2026-09-02', 'prior-MY reference week'),
 ('2026-09-04', 1, 1099, 'DTN 2026-09-10', 'MY week 1'),
 ('2026-09-11', 2, 1099, 'DJN via TradingView 2026-09-16', 'MY week 2'),
]
for k, (d, wk, prod, src, note) in enumerate(eseed):
    rr = ir + 1 + k
    ws.cell(row=rr, column=1, value=d).number_format = 'yyyy-mm-dd'
    ws.cell(row=rr, column=2, value=wk)
    c = ws.cell(row=rr, column=3, value=prod); c.number_format = '#,##0'; c.fill = INPUT_FILL; c.border = BORDER
    ws.cell(row=rr, column=4, value=src).font = NOTE_FONT
    ws.cell(row=rr, column=5, value=f'=IF(C{rr}="","",C{rr}*7*42/($C$4*1000))').number_format = '#,##0.0'; ws.cell(row=rr, column=5).border = BORDER
    ws.cell(row=rr, column=6, value=f'=IF(E{rr}="","",E{rr}+F{rr-1})' if k else f'=E{rr}').number_format = '#,##0'; ws.cell(row=rr, column=6).border = BORDER
    ws.cell(row=rr, column=7, value=f'=IF(E{rr}="","",AVERAGE($E$8:E{rr})*52)').number_format = '#,##0'; ws.cell(row=rr, column=7).border = BORDER
    ws.cell(row=rr, column=8, value=f'=IF(G{rr}="","",G{rr}-$E$5)').number_format = '#,##0'; ws.cell(row=rr, column=8).border = BORDER
    ws.cell(row=rr, column=9, value=note).font = NOTE_FONT
    for col in (1, 2, 4): ws.cell(row=rr, column=col).border = BORDER
for k in range(3, 53):
    rr = ir + 1 + k
    for col in (1, 2, 3, 4):
        c = ws.cell(row=rr, column=col); c.border = BORDER
        if col == 3: c.fill = INPUT_FILL; c.number_format = '#,##0'
    ws.cell(row=rr, column=5, value=f'=IF(C{rr}="","",C{rr}*7*42/($C$4*1000))').number_format = '#,##0.0'; ws.cell(row=rr, column=5).border = BORDER
    ws.cell(row=rr, column=6, value=f'=IF(E{rr}="","",E{rr}+F{rr-1})').number_format = '#,##0'; ws.cell(row=rr, column=6).border = BORDER
    ws.cell(row=rr, column=7, value=f'=IF(E{rr}="","",AVERAGE($E$8:E{rr})*52)').number_format = '#,##0'; ws.cell(row=rr, column=7).border = BORDER
    ws.cell(row=rr, column=8, value=f'=IF(G{rr}="","",G{rr}-$E$5)').number_format = '#,##0'; ws.cell(row=rr, column=8).border = BORDER
ws.freeze_panes = 'A8'
widths(ws, {1:14, 2:9, 3:17, 4:26, 5:18, 6:16, 7:16, 8:13, 9:22, 11:9, 12:11, 13:9, 14:9})
ws['K7'] = 'SEASONAL S-CURVE (TO FIT — EIA weekly history; see README)'; ws['K7'].font = Font(bold=True, size=10, color='9C0006')
for i, h in enumerate(['MY week', 'Avg % of final', 'Min %', 'Max %'], 11): ws.cell(row=7, column=i, value=h)
style_header(ws, 7, 14)
for w in range(0, 53):
    rr = 8 + w
    ws.cell(row=rr, column=11, value=w).border = BORDER
    for col in (12, 13, 14):
        c = ws.cell(row=rr, column=col); c.border = BORDER; c.fill = GAP_FILL
ws['K62'] = 'STATUS: historical fit pending — paste fitted avg/min/max % here after EIA pull.'; ws['K62'].font = GAP_FONT
ch = LineChart(); ch.title = 'Weekly implied corn grind: 2026/27 pace'; ch.style = 10
ch.y_axis.title = 'M bu/week'; ch.x_axis.title = 'MY week'; ch.height = 7.5; ch.width = 15
ch.add_data(Reference(ws, min_col=5, min_row=ir, max_row=ir + 53), titles_from_data=True)
ch.set_categories(Reference(ws, min_col=2, min_row=ir + 1, max_row=ir + 53))
ws.add_chart(ch, 'A64')

# ======================================================== TAB 5: PACE_FEED
ws = wb.create_sheet('PACE_FEED'); ws.sheet_properties.tabColor = '6A1B9A'
title_block(ws, 'Feed & residual pace tracker — quarterly Grain-Stocks-implied residual',
 'METHOD: feed & residual is the balancing item — it is never surveyed directly. Each quarter: implied F&R = beginning stocks (+ production in Q1) − ending stocks − exports − ethanol grind − other FSI. When a Grain Stocks print surprises, this calculator shows exactly how much F&R (and thus WASDE demand) must move. Enter each quarterly print on release (NASS Grain Stocks: Jan 12, Mar 31, Jun 30, Sep 30).', 10)
ws['A4'] = 'Worked template: 2025/26 (annual F&R actual = 6,350 M bu — quarterly components are INPUTS; sum of implied quarters should ≈ 6,350)'
ws['A4'].font = Font(bold=True, size=10)
ir = 6
in_hdr = ['Quarter (2025/26)', 'Beg stocks (M bu)', '+ Production (M bu)', '− End stocks (M bu)', '− Exports (M bu)',
          '− Ethanol grind (M bu)', '− Other FSI (M bu)', '= Implied F&R (M bu)', 'Source / note', 'Check vs annual']
for i, h in enumerate(in_hdr, 1): ws.cell(row=ir, column=i, value=h)
style_header(ws, ir, 10)
qdata = [
 ('Q1 Sep–Nov 2025', 1551.3, 17020.5, None, None, None, None, 'Beg = ERS yearbook; prod = ERS yearbook; end = Dec-1 Grain Stocks print (INPUT)'),
 ('Q2 Dec 2025–Feb 2026', None, 0, None, None, None, None, 'Beg = Dec-1 print; end = Mar-1 print (INPUTs)'),
 ('Q3 Mar–May 2026', None, 0, None, None, None, None, 'Beg = Mar-1 print; end = Jun-1 print (INPUTs)'),
 ('Q4 Jun–Aug 2026', None, 0, 1921.8, None, None, None, 'End = Sep WASDE 2025/26 ending stocks (Sep-30 Grain Stocks); beg = Jun-1 print (INPUT)'),
]
for k, (q, beg, prod, end, exp, eth, ofsi, note) in enumerate(qdata):
    rr = ir + 1 + k
    ws.cell(row=rr, column=1, value=q).border = BORDER
    for col, v in ((2, beg), (3, prod), (4, end), (5, exp), (6, eth), (7, ofsi)):
        c = ws.cell(row=rr, column=col, value=v); c.number_format = '#,##0.0'; c.border = BORDER
        if v is None: c.fill = INPUT_FILL
        elif col in (5, 6, 7): c.fill = INPUT_FILL
    if k == 0:
        for col in (5, 6, 7): ws.cell(row=rr, column=col).fill = INPUT_FILL
    ws.cell(row=rr, column=8, value=f'=IF(COUNT(B{rr}:G{rr})=6,B{rr}+C{rr}-D{rr}-E{rr}-F{rr}-G{rr},"enter all inputs")')
    ws.cell(row=rr, column=8).number_format = '#,##0.0'; ws.cell(row=rr, column=8).border = BORDER
    ws.cell(row=rr, column=9, value=note).font = NOTE_FONT; ws.cell(row=rr, column=9).alignment = WRAP; ws.cell(row=rr, column=9).border = BORDER
    ws.cell(row=rr, column=10, value='').border = BORDER
ar = ir + 5
ws.cell(row=ar, column=1, value='ANNUAL CHECK: sum of implied quarters').font = Font(bold=True)
ws.cell(row=ar, column=8, value=f'=SUM(H{ir+1}:H{ir+4})').number_format = '#,##0.0'; ws.cell(row=ar, column=8).font = Font(bold=True); ws.cell(row=ar, column=8).border = BORDER
ws.cell(row=ar, column=10, value='=IF(ISNUMBER(H11),"vs actual 6,350: "&TEXT(H11-6350,"#,##0"),"")').font = NOTE_FONT
ws.freeze_panes = 'A7'
widths(ws, {1:20, 2:14, 3:14, 4:14, 5:13, 6:15, 7:13, 8:15, 9:52, 10:20})
ws.row_dimensions[4].height = 30

# ======================================================== TAB 6: VALIDATE
ws = wb.create_sheet('VALIDATE'); ws.sheet_properties.tabColor = 'C62828'
title_block(ws, 'Validation checkpoint — read this before any number reaches a model or chart',
 'SECTION 1: historical identity audit (live formulas → HIST_BALANCE). SECTION 2: current vintage check — Aug→Sep 2026 WASDE diff (seeded example). Sign off below each release day.', 6)
ws['A4'] = '1) HISTORICAL IDENTITY AUDIT — Supply − Total use − Ending stocks (must = 0)'; ws['A4'].font = Font(bold=True, size=11)
for i, h in enumerate(['Marketing year', 'Identity residual (M bu)', 'Status'], 1): ws.cell(row=5, column=i, value=h)
style_header(ws, 5, 3)
for j, x in enumerate(rows):
    rr = 6 + j
    ws.cell(row=rr, column=1, value=x['my']).border = BORDER
    ws.cell(row=rr, column=2, value=f"='HIST_BALANCE'!Q{4+j}").number_format = '#,##0.0'; ws.cell(row=rr, column=2).border = BORDER
    ws.cell(row=rr, column=3, value=f'=IF(B{rr}=0,"PASS","FAIL")'); ws.cell(row=rr, column=3).border = BORDER
ws.conditional_formatting.add(f'C6:C{6+len(rows)-1}', CellIsRule(operator='equal', formula=['"FAIL"'], fill=FLAG_FILL))
r2 = 6 + len(rows) + 2
ws.cell(row=r2, column=1, value='2) CURRENT VINTAGE CHECK — Aug→Sep 2026 (WASDE #675), seeded example').font = Font(bold=True, size=11)
for i, h in enumerate(['Line item', 'Aug 2026', 'Sep 2026', 'Abs change', '% change', 'Flag'], 1): ws.cell(row=r2 + 1, column=i, value=h)
style_header(ws, r2 + 1, 6)
vdiff = [('Yield (bu/ac)', 180.7, 178.5), ('Production (M bu)', 16013, 15800), ('Ending stocks (M bu)', 1653, 1567),
         ('Season avg price ($/bu)', 4.50, 4.80), ('Feed & residual (M bu)', 6100, 5950), ('Exports (M bu)', 3275, 3275)]
for k, (item, aug, sep) in enumerate(vdiff):
    rr = r2 + 2 + k
    ws.cell(row=rr, column=1, value=item).border = BORDER
    ws.cell(row=rr, column=2, value=aug).number_format = '#,##0.0'; ws.cell(row=rr, column=2).border = BORDER
    ws.cell(row=rr, column=3, value=sep).number_format = '#,##0.0'; ws.cell(row=rr, column=3).border = BORDER
    ws.cell(row=rr, column=4, value=f'=C{rr}-B{rr}').number_format = '#,##0.0'; ws.cell(row=rr, column=4).border = BORDER
    ws.cell(row=rr, column=5, value=f'=IF(B{rr}=0,"",D{rr}/B{rr})').number_format = '0.0%'; ws.cell(row=rr, column=5).border = BORDER
    ws.cell(row=rr, column=6, value=f'=IF(ABS(E{rr})>0.05,"FLAG — review","")'); ws.cell(row=rr, column=6).border = BORDER
ws.conditional_formatting.add(f'F{r2+2}:F{r2+1+len(vdiff)}', CellIsRule(operator='notEqual', formula=['""'], fill=FLAG_FILL))
ws.cell(row=r2 + 2 + len(vdiff) + 1, column=1, value='Flag rule: |% change| > 5% on any line → review before promoting. Production > 2% also worth a note.').font = NOTE_FONT
sr = r2 + 2 + len(vdiff) + 3
ws.cell(row=sr, column=1, value='3) SIGN-OFF').font = Font(bold=True, size=11)
for i, h in enumerate(['Date', 'Release checked', 'Initials', 'Note (what moved, what matters)'], 1): ws.cell(row=sr + 1, column=i, value=h)
style_header(ws, sr + 1, 4)
for k in range(3):
    for col in range(1, 5):
        c = ws.cell(row=sr + 2 + k, column=col); c.border = BORDER; c.fill = INPUT_FILL
widths(ws, {1:34, 2:20, 3:14, 4:14, 5:12, 6:16})

# ======================================================== TAB 7: CHANGELOG
ws = wb.create_sheet('CHANGELOG'); ws.sheet_properties.tabColor = '616161'
title_block(ws, 'Changelog — append-only', 'Every release day: date, report, what changed, your note. This becomes the newsletter\'s "what moved and why" draft.', 4)
for i, h in enumerate(['Date', 'Report', 'What changed', 'Notes'], 1): ws.cell(row=3, column=i, value=h)
style_header(ws, 3, 4)
cl = [
 ('2026-09-18', 'v1 workbook build', 'HIST_BALANCE 2010/11–2025/26 from ERS Feed Grains Database yearbook (CSV, downloaded 2026-09-18); pace tabs + VALIDATE/CHANGELOG framework', 'Identity holds all 16 yrs; 2024/25 finals & 2025/26 est. cross-checked vs WASDE #675. Weekly S-curves TO FIT (need FAS/EIA API keys).'),
 ('2026-09-11', 'WASDE #675 (Sep)', 'Yield 180.7→178.5; production −213M bu to 15,800M; ending stocks 1,653→1,567M; price +$0.30 to $4.80; old-crop carryout 1,922M', 'Stocks-to-use 9.7% — below the 10% historical rally zone.'),
]
for k, (d, rep, chg, note) in enumerate(cl):
    rr = 4 + k
    ws.cell(row=rr, column=1, value=d).number_format = 'yyyy-mm-dd'
    ws.cell(row=rr, column=2, value=rep)
    ws.cell(row=rr, column=3, value=chg).alignment = WRAP
    ws.cell(row=rr, column=4, value=note).alignment = WRAP
    for col in range(1, 5): ws.cell(row=rr, column=col).border = BORDER
    ws.row_dimensions[rr].height = 45
for k in range(6):
    rr = 6 + k
    for col in range(1, 5):
        c = ws.cell(row=rr, column=col); c.border = BORDER; c.fill = INPUT_FILL
widths(ws, {1:13, 2:22, 3:60, 4:60})

for wsn in wb.sheetnames:
    wb[wsn].sheet_view.showGridLines = True
wb.save(OUT)
print('saved', OUT)
