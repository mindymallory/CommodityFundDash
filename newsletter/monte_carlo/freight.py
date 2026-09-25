"""Weekly landed-cost freight monitor for the global corn model.

What it does
------------
1. Downloads the latest USDA AMS Grain Transportation Report (GTR) PDF and
   the GTR Table 1 dataset (weekly ocean freight rates), plus the current
   USDA FAS "Grain: World Markets and Trade" circular (monthly IGC export
   FOB bids).
2. Parses Table 20 of the GTR ("Ocean freight rates for selected
   shipments", source: Maritime Research, Inc.) for per-fixture ocean
   rates, including Brazil -> China heavy-grain fixtures.
3. Combines FOB + freight into landed costs by (origin, destination) and
   appends one staged row per week to freight_landed_stage_<date>.csv.
4. Writes charts + a current ranking table (least-cost -> most-expensive
   into China).
5. Exposes get_landed_costs() for world.py's China/ROW logit allocation
   (see INTEGRATION_SPEC_FREIGHT.md).

Refresh (one command):
    cd ~/workspace/your_files/commodity-newsletter-design
    python3 -m monte_carlo.freight

Honesty rules (enforced in code, not just comments):
- Every freight/FOB value carries its vintage date and source.
- Anything older than its max-age, or a proxy/estimate, is flagged and
  NEVER presented as live.
- Ukraine FOB is currently unquoted by IGC (not reported since 2026-09-01);
  the module uses the last quoted value and flags it stale, loudly.
- Argentina/Ukraine -> China ocean fixtures are not published anywhere
  public; Argentina uses the Brazil-China fixture mean as an explicit
  proxy, Ukraine has no freight leg until a human enters one.
"""

import csv
import datetime as dt
import io
import os
import re
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_ROOT = os.path.join(BASE, "raw")
CHART_DIR = os.path.join(BASE, "mc_charts")

GTR_PAGE = "https://www.ams.usda.gov/services/transportation-analysis/gtr"
GTR_TABLE1_XLSX = ("https://www.ams.usda.gov/sites/default/files/media/"
                   "GTRTable1.xlsx")
GRAIN_CIRCULAR = "https://apps.fas.usda.gov/psdonline/circulars/grain.pdf"

BU_PER_MT = 39.368  # metric tons -> bushels (corn)

ORIGINS = ["US_GULF", "US_PNW", "BR", "AR", "UP"]
DESTS = ["CN", "JP", "MX"]  # China, Japan, Mexico (Veracruz)

# FOB origins as quoted by IGC in the FAS circular -> our origin codes
FOB_ORIGIN_MAP = {
    "U.S. 3YC, Gulf": "US_GULF",
    "Brazil, Paranagu": "BR",
    "Argentina, Up River": "AR",
    "Ukraine": "UP",
}
# PNW corn FOB is not quoted by IGC. Assumption (flagged wherever used):
# PNW FOB = Gulf FOB - PNW_FOB_DISCOUNT_MT. Sensitivity +/- 10 $/mt is
# shown in the docs; the China ranking is robust across that band.
PNW_FOB_DISCOUNT_MT = 16.0

# Estimated PNW->China ocean freight (Mindy's 2026-09-18 decision: adopt
# the proxy — no public PNW->China fixture newer than Aug 4, 2026 exists,
# so a direct quote cannot go live).
#
# Construction: PNW_CHINA_FREIGHT = contemporaneous GTR Table 1 PNW->Japan
# weekly rate + PNW_CHINA_PREMIUM_MT. The premium was estimated from
# 8 PNW->China fixtures (Maritime Research via GTR Table 20, Jan 2021 -
# Aug 2026: 6 heavy grain + 2 soybeans; vessel economics are
# grain-agnostic) vs the Table 1 PNW->Japan rate for the fixture week:
#   mean premium -0.96 $/mt, sd 2.11 $/mt (se of mean 0.75)
#   no time trend (+0.26 $/mt/yr, se 0.43; corr with time 0.24)
#   no level dependence (corr with PNW->Japan level -0.04)
#   OLS PNW_CN = a + b*PNW_JP: b = 0.98 (se 0.24, indistinguishable
#     from 1), R^2 = 0.73 -> the constant-premium form is parsimonious
#   holdout validation: fit on 7 (through Feb 2026), predict the
#     Aug-2026 fixture -> error -0.34 $/mt (OOS RMSE 0.34)
#   cross-check: implied Gulf-PNW spread to China (74.50 - 36.79 = 37.71)
#     sits between the Aug-2026 fixture-pair spread (34.25) and the GTR's
#     published Aug-2026 Gulf-vs-PNW spread to Japan (36.19) — consistent.
# Full methodology: freight_pnw_proxy.md (includes the direct Gulf->PNW
# fixture regression that FAILED: only 2 co-occurring fixture pairs in
# 5.75 years of GTRs, so the premium route was used instead).
# Prediction SE 2.24 $/mt (~$0.06/bu) sits inside the world model's
# existing per-draw spread noise (sd 0.10 $/bu), so no extra noise term
# is added. The leg is ALWAYS flagged "estimated" and is only used when
# world_config.FREIGHT_ALLOW_ESTIMATED_PNW is True.
PNW_CHINA_PREMIUM_MT = -0.96
PNW_CHINA_PREMIUM_SE_MT = 2.24

# Max ages (days) before a leg is flagged stale. Fixture means cover a
# 28-day window plus reporting lag, so weekly freight legs are good for
# ~5 weeks; FOB refreshes with the monthly FAS circular; manual legs are
# entered by a human whenever GAIN/Conab/ANEC data arrives.
MAX_AGE = {"freight_weekly": 35, "fob_monthly": 75, "manual": 120}

# Fixture selection: mean of fixtures with entry_date in the trailing
# FIXTURE_WINDOW_DAYS; if none, latest fixture within FIXTURE_FALLBACK_DAYS
# flagged stale; else n/a.
FIXTURE_WINDOW_DAYS = 28
FIXTURE_FALLBACK_DAYS = 120

EXPORT_REGIONS = {"U.S. Gulf", "PNW", "Brazil", "Argentina",
                  "U.S. Atlantic Coast"}
REGION_TO_ORIGIN = {"U.S. Gulf": "US_GULF", "PNW": "US_PNW",
                    "Brazil": "BR", "Argentina": "AR",
                    "U.S. Atlantic Coast": "US_GULF"}
# Import-region normalization for the destinations we track
DEST_PATTERNS = {
    "CN": re.compile(r"china", re.I),
    "JP": re.compile(r"japan", re.I),
    "MX": re.compile(r"mexico|veracruz", re.I),
}


# ------------------------------------------------------------ fetching ---

def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def discover_latest_gtr_url():
    """Scrape the GTR landing page for the latest issue PDF link."""
    html = _get(GTR_PAGE).decode("utf-8", "replace")
    m = re.findall(r'href="(/sites/default/files/media/GTR\d+\.pdf)"', html)
    if not m:
        raise RuntimeError("could not find a GTR PDF link on " + GTR_PAGE)
    return "https://www.ams.usda.gov" + m[0]


def fetch_raw(raw_dir):
    """Download latest GTR PDF + Table1 xlsx + FAS circular into raw_dir."""
    os.makedirs(raw_dir, exist_ok=True)
    gtr_url = discover_latest_gtr_url()
    jobs = [
        ("gtr_latest.pdf", gtr_url),
        ("GTRTable1.xlsx", GTR_TABLE1_XLSX),
        ("grain_circular.pdf", GRAIN_CIRCULAR),
    ]
    out = {}
    for name, url in jobs:
        path = os.path.join(raw_dir, name)
        if not os.path.exists(path):
            data = _get(url)
            with open(path, "wb") as f:
                f.write(data)
        out[name] = path
    return out


# ------------------------------------------------------------- parsing ---

def parse_table1_ocean(xlsx_path):
    """Weekly US Gulf / PNW ocean rates ($/mt, to Japan) from GTR Table 1.

    Returns list of (date, gulf, pnw), oldest first. Series starts 2002.
    """
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb["Data"]
    rows = []
    for r in ws.iter_rows(min_row=8, values_only=True):
        d, gulf, pnw = r[0], r[4], r[5]
        if d is None or gulf is None or pnw is None:
            continue
        try:
            gulf, pnw = float(gulf), float(pnw)
        except (TypeError, ValueError):
            continue  # header/label rows
        if isinstance(d, dt.datetime):
            d = d.date()
        rows.append((d, gulf, pnw))
    return rows


def _parse_entry_date(s):
    s = s.strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%d-%b-%y", "%d-%b-%Y",
                "%b %d %Y", "%b%d, %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    m = re.match(r"([A-Za-z]{3,9})\s*(\d{1,2})[,\s]+(\d{4})", s)
    if m:
        try:
            return dt.datetime.strptime(
                "%s %s %s" % (m.group(1)[:3], m.group(2), m.group(3)),
                "%b %d %Y").date()
        except ValueError:
            pass
    return None


def parse_fixtures(pdf_path):
    """Parse GTR Table 20 fixture rows from a GTR PDF.

    Returns list of dicts: export_region, import_region, grain,
    entry_date, loading_date, volume_mt, rate_usd_mt, week_ending.
    """
    import pymupdf
    doc = pymupdf.open(pdf_path)
    week_ending = None
    records = []
    for page in doc:
        t = page.get_text()
        if "selected shipments" not in t.lower():
            continue
        m = re.search(r"week ending\s+(\d{2}/\d{2}/\d{4})", t)
        if m:
            week_ending = dt.datetime.strptime(m.group(1),
                                               "%m/%d/%Y").date()
        seg = t[t.find("Table 20."):t.find("Ocean rates")]
        lines = [ln.strip() for ln in seg.split("\n")]
        i = 0
        while i < len(lines):
            if lines[i] in EXPORT_REGIONS:
                try:
                    exp, imp, grain = lines[i], lines[i + 1], lines[i + 2]
                    entry = _parse_entry_date(lines[i + 3])
                    load = lines[i + 4]
                    vol = float(lines[i + 5].replace(",", ""))
                    rate = float(lines[i + 6].strip())
                except (IndexError, ValueError):
                    i += 1
                    continue
                records.append({
                    "export_region": exp, "import_region": imp,
                    "grain": grain, "entry_date": entry,
                    "loading_date": load, "volume_mt": vol,
                    "rate_usd_mt": rate, "week_ending": week_ending,
                })
                i += 7
            else:
                i += 1
    return records


def parse_fas_fob(pdf_path):
    """Parse IGC corn export FOB bids from the FAS Grain circular.

    Returns {origin_code: (value_usd_mt, vintage_date)} for the most
    recent quoted column. Unquoted origins (currently Ukraine) are
    filled from the prior column and flagged stale by the caller via
    vintage date.
    """
    import pymupdf
    doc = pymupdf.open(pdf_path)
    fob = {}
    for page in doc:
        t = page.get_text()
        if "CORN PRICES" not in t or "Export bids (fob" not in t:
            continue
        lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
        # header dates: e.g. "8-Sep-26", "7-Aug-26", "8-Sep-25"
        try:
            h = lines.index("Export bids (fob, US$ per ton)")
        except ValueError:
            continue
        dates = []
        for ln in lines[h + 1:h + 4]:
            m = re.match(r"(\d{1,2})-([A-Za-z]{3})-(\d{2})", ln)
            if m:
                dates.append(dt.datetime.strptime(
                    "%s-%s-20%s" % (m.group(1), m.group(2), m.group(3)),
                    "%d-%b-%Y").date())
        if not dates:
            continue
        i = h + 1 + len(dates)
        cur = {}
        while i < len(lines):
            ln = lines[i]
            origin = None
            for key in FOB_ORIGIN_MAP:
                if ln.startswith(key.split(",")[0]):
                    origin = FOB_ORIGIN_MAP[key]
                    break
            if origin is None:
                i += 1
                continue
            vals = []
            for k in range(1, 4):
                if i + k >= len(lines):
                    break
                v = lines[i + k].strip()
                if v == "N/A":
                    vals.append(None)
                else:
                    try:
                        vals.append(float(v.replace(",", "")))
                    except ValueError:
                        break
            if len(vals) == len(dates):
                for v, d in zip(vals, dates):
                    if v is not None:
                        cur[origin] = (v, d)
                        break
            i += 1 + len(vals)
        fob.update(cur)
        break
    return fob


def load_manual_legs(raw_dir):
    """Human-entered freight legs (Argentina/Ukraine), with vintages.

    CSV columns: origin,destination,freight_usd_mt,vintage_date,source,note
    Missing file -> {}.
    """
    path = os.path.join(raw_dir, "freight_manual_legs.csv")
    legs = {}
    if not os.path.exists(path):
        return legs
    with open(path) as f:
        for row in csv.DictReader(f):
            if not row.get("freight_usd_mt"):
                continue
            legs[(row["origin"], row["destination"])] = {
                "freight_usd_mt": float(row["freight_usd_mt"]),
                "vintage": dt.datetime.strptime(
                    row["vintage_date"], "%Y-%m-%d").date(),
                "source": row.get("source", ""),
                "note": row.get("note", ""),
            }
    return legs


# --------------------------------------------------------- landed cost ---

def _dest_of(import_region):
    for code, pat in DEST_PATTERNS.items():
        if pat.search(import_region or ""):
            return code
    return None


def select_freight(fixtures, origin, dest, asof):
    """Pick an ocean rate for (origin, dest) from fixtures.

    Returns (rate, vintage_date, n_fixtures, method, flag) where flag is
    '' | 'stale' | 'proxy' | 'n/a'.
    """
    cands = []
    for fx in fixtures:
        if REGION_TO_ORIGIN.get(fx["export_region"]) != origin:
            continue
        if _dest_of(fx["import_region"]) != dest:
            continue
        if fx["entry_date"] is None:
            continue
        cands.append(fx)
    recent = [c for c in cands
              if (asof - c["entry_date"]).days <= FIXTURE_WINDOW_DAYS]
    if recent:
        rate = sum(c["rate_usd_mt"] for c in recent) / len(recent)
        vint = max(c["entry_date"] for c in recent)
        return rate, vint, len(recent), "fixture_mean_%dw" % (
            FIXTURE_WINDOW_DAYS // 7), ""
    old = [c for c in cands
           if (asof - c["entry_date"]).days <= FIXTURE_FALLBACK_DAYS]
    if old:
        best = max(old, key=lambda c: c["entry_date"])
        return (best["rate_usd_mt"], best["entry_date"], 1,
                "latest_fixture", "stale")
    return None, None, 0, "none", "n/a"


def build_week(asof, fob, fixtures, table1_rows, manual_legs):
    """Build one staged week of landed costs. Returns list of row dicts."""
    rows = []
    # FOB per origin (US_PNW estimated off Gulf)
    fob_map, fob_vint, fob_src, fob_flag = {}, {}, {}, {}
    for o in ORIGINS:
        if o == "US_PNW":
            v, d = fob.get("US_GULF", (None, None))
            if v is not None:
                fob_map[o] = v - PNW_FOB_DISCOUNT_MT
                fob_vint[o] = d
                fob_src[o] = "IGC via FAS, Gulf less %.0f $/mt (assumption)" % PNW_FOB_DISCOUNT_MT
                fob_flag[o] = "assumption"
        elif o in fob:
            v, d = fob[o]
            fob_map[o] = v
            fob_vint[o] = d
            fob_src[o] = "IGC via FAS Grain circular"
            fob_flag[o] = ""
    # weekly Table 1 lookup for Japan legs
    t1 = {d: (g, p) for d, g, p in table1_rows}

    for o in ORIGINS:
        for dest in DESTS:
            fr, fr_vint, nfx, method, flag = select_freight(
                fixtures, o, dest, asof)
            fr_src = "GTR Table 20 fixtures (Maritime Research)"
            # Japan legs: Table 1 weekly series is the direct source
            if dest == "JP" and o in ("US_GULF", "US_PNW") and t1:
                wk = max(d for d in t1 if d <= asof) if any(
                    d <= asof for d in t1) else None
                if wk is not None:
                    fr = t1[wk][0] if o == "US_GULF" else t1[wk][1]
                    fr_vint, nfx = wk, 1
                    method = "GTR Table 1 weekly"
                    flag = "" if (asof - wk).days <= MAX_AGE[
                        "freight_weekly"] else "stale"
                    fr_src = "GTR Table 1 dataset (AMS)"
            # Argentina->China: proxy = Brazil-China fixture mean
            if flag == "n/a" and o == "AR" and dest == "CN":
                fr2, v2, n2, m2, f2 = select_freight(
                    fixtures, "BR", "CN", asof)
                if fr2 is not None:
                    fr, fr_vint, nfx, method = fr2, v2, n2, "proxy:" + m2
                    flag = "proxy"
                    fr_src = ("no public AR fixture; Brazil-China "
                              "fixture mean as proxy")
            # Manual human legs override / fill gaps
            if (o, dest) in manual_legs:
                m = manual_legs[(o, dest)]
                fr, fr_vint = m["freight_usd_mt"], m["vintage"]
                nfx, method, fr_src = 1, "manual", m["source"]
                flag = ("stale" if (asof - fr_vint).days > MAX_AGE["manual"]
                        else "manual")
            f = fob_map.get(o)
            landed = (f + fr) if (f is not None and fr is not None) else None
            age_fob = (asof - fob_vint[o]).days if o in fob_vint and fob_vint[o] else None
            age_fr = (asof - fr_vint).days if fr_vint else None
            stale = ((age_fob is not None and age_fob > MAX_AGE["fob_monthly"])
                     or (age_fr is not None and age_fr > MAX_AGE["freight_weekly"])
                     or flag == "stale")
            # NOTE: "proxy", "manual", "assumption", "n/a" are their own
            # flags and do NOT imply age-staleness; they are shown as-is.
            rows.append({
                "week_ending": asof.isoformat(), "origin": o,
                "destination": dest,
                "fob_usd_mt": f,
                "fob_vintage": fob_vint.get(o).isoformat()
                if o in fob_vint and fob_vint[o] else "",
                "fob_source": fob_src.get(o, ""),
                "freight_usd_mt": fr,
                "freight_vintage": fr_vint.isoformat() if fr_vint else "",
                "freight_source": fr_src,
                "freight_method": method,
                "landed_usd_mt": landed,
                "landed_usd_bu": (landed / BU_PER_MT) if landed else None,
                "flag": ";".join(x for x in
                                 [fob_flag.get(o, ""), flag,
                                  "STALE" if stale else ""]
                                 if x),
            })

    # Estimated PNW->China leg (Mindy's 2026-09-18 decision; see the
    # PNW_CHINA_PREMIUM_MT comment block and freight_pnw_proxy.md).
    # Built from the contemporaneous Table 1 PNW->Japan weekly rate, so
    # each staged week carries its own week's estimate. ALWAYS flagged
    # "estimated" — never presented as a quote.
    if t1:
        wk = max((d for d in t1 if d <= asof), default=None)
        if wk is not None:
            est_fr = t1[wk][1] + PNW_CHINA_PREMIUM_MT
            f_pnw = fob_map.get("US_PNW")
            landed_est = (f_pnw + est_fr
                          if f_pnw is not None else None)
            est_stale = (asof - wk).days > MAX_AGE["freight_weekly"]
            rows.append({
                "week_ending": asof.isoformat(), "origin": "US_PNW_EST",
                "destination": "CN",
                "fob_usd_mt": f_pnw,
                "fob_vintage": fob_vint.get("US_PNW").isoformat()
                if fob_vint.get("US_PNW") else "",
                "fob_source": fob_src.get("US_PNW", ""),
                "freight_usd_mt": round(est_fr, 2),
                "freight_vintage": wk.isoformat(),
                "freight_source": (
                    "estimated: GTR Table 1 PNW->Japan weekly ($%.2f/mt) + "
                    "China premium (%.2f $/mt; see freight_pnw_proxy.md)"
                    % (t1[wk][1], PNW_CHINA_PREMIUM_MT)),
                "freight_method": "proxy:premium_regression",
                "landed_usd_mt": (round(landed_est, 2)
                                  if landed_est is not None else None),
                "landed_usd_bu": (round(landed_est / BU_PER_MT, 4)
                                  if landed_est is not None else None),
                "flag": ";".join(x for x in
                                 [fob_flag.get("US_PNW", ""), "estimated",
                                  "STALE" if est_stale else ""]
                                 if x),
            })
    return rows


STAGE_COLS = ["week_ending", "origin", "destination", "fob_usd_mt",
              "fob_vintage", "fob_source", "freight_usd_mt",
              "freight_vintage", "freight_source", "freight_method",
              "landed_usd_mt", "landed_usd_bu", "flag"]


def stage_path():
    return os.path.join(BASE, "freight_landed_stage_%s.csv"
                        % dt.date.today().isoformat())


def append_stage(rows, path):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=STAGE_COLS,
                           extrasaction="ignore")
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k))
                        for k in STAGE_COLS})


# ------------------------------------------------------------- charts ---

def ranking_table(rows, dest="CN"):
    """Current ranking into dest: list of (origin, landed_mt, flag)."""
    sub = [r for r in rows if r["destination"] == dest
           and r["landed_usd_mt"] is not None]
    sub.sort(key=lambda r: r["landed_usd_mt"])
    return [(r["origin"], r["landed_usd_mt"], r["landed_usd_bu"],
             r["fob_usd_mt"], r["freight_usd_mt"], r["flag"]) for r in sub]


def write_charts(rows, table1_rows, asof):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(CHART_DIR, exist_ok=True)

    # (a) Current landed-cost ranking into China, FOB vs freight stacked
    rk = ranking_table(rows, "CN")
    fig, ax = plt.subplots(figsize=(9, 4.6))
    origins = [r[0] for r in rk]
    fobs = [r[3] for r in rk]
    frts = [r[4] for r in rk]
    y = range(len(origins))
    ax.barh(list(y), fobs, label="FOB", color="#4C78A8")
    ax.barh(list(y), frts, left=fobs, label="Ocean freight",
            color="#F58518")
    for i, r in enumerate(rk):
        tag = ("  [%s]" % r[5]) if r[5] else ""
        ax.text(r[1] + 3, i, "$%.0f/mt%s" % (r[1], tag),
                va="center", fontsize=9)
    ax.set_yticks(list(y))
    ax.set_yticklabels(origins)
    ax.set_xlabel("US$/metric ton")
    ax.set_xlim(0, max(r[1] for r in rk) * 1.38)
    ax.set_title("Landed cost into China, week ending %s\n"
                 "brackets = flagged (proxy / stale / assumption)"
                 % asof.isoformat())
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "mc_freight_landed_china.png"),
                dpi=110)
    plt.close(fig)

    # (b) Ocean-rate history: Table 1 Gulf/PNW->Japan + recent fixtures
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ds = [d for d, _, _ in table1_rows if d >= dt.date(2020, 1, 1)]
    g = [x[1] for x in table1_rows if x[0] >= dt.date(2020, 1, 1)]
    p = [x[2] for x in table1_rows if x[0] >= dt.date(2020, 1, 1)]
    ax.plot(ds, g, label="US Gulf -> Japan (GTR Table 1, weekly)",
            color="#4C78A8", lw=1.2)
    ax.plot(ds, p, label="PNW -> Japan (GTR Table 1, weekly)",
            color="#54A24B", lw=1.2)
    ax.set_ylabel("US$/metric ton")
    ax.set_title("US ocean freight rates to Japan (weekly, AMS) — "
                 "China fixtures tracked separately in staged CSV")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "mc_freight_ocean_history.png"),
                dpi=110)
    plt.close(fig)


# ------------------------------------------------- integration API ---

def get_landed_costs(dest="CN", stage_csv=None):
    """Latest-week landed costs for world.py's logit allocation.

    Returns {origin: {fob_bu, freight_bu, landed_bu, fob_spread_bu,
    vintage_days, stale, flag}}. FOB spreads are vs US_GULF. Raises
    FileNotFoundError if no staged CSV exists.
    """
    path = stage_csv or _latest_stage()
    latest, rows = None, []
    with open(path) as f:
        for r in csv.DictReader(f):
            if r["destination"] != dest:
                continue
            rows.append(r)
            if latest is None or r["week_ending"] > latest:
                latest = r["week_ending"]
    rows = [r for r in rows if r["week_ending"] == latest]
    asof = dt.datetime.strptime(latest, "%Y-%m-%d").date()
    us_fob = next((float(r["fob_usd_mt"]) for r in rows
                   if r["origin"] == "US_GULF" and r["fob_usd_mt"]), None)
    out = {}
    for r in rows:
        o = r["origin"]
        fob = float(r["fob_usd_mt"]) if r["fob_usd_mt"] else None
        frt = float(r["freight_usd_mt"]) if r["freight_usd_mt"] else None
        vint_days = None
        for col in ("freight_vintage", "fob_vintage"):
            if r[col]:
                d = (asof - dt.datetime.strptime(
                    r[col], "%Y-%m-%d").date()).days
                vint_days = d if vint_days is None else max(vint_days, d)
        out[o] = {
            "fob_bu": fob / BU_PER_MT if fob else None,
            "freight_bu": frt / BU_PER_MT if frt else None,
            "landed_bu": ((fob + frt) / BU_PER_MT
                           if fob and frt else None),
            "fob_spread_bu": ((fob - us_fob) / BU_PER_MT
                               if fob and us_fob else None),
            "vintage_days": vint_days,
            "stale": bool((r["flag"] or "").strip()),
            "flag": r["flag"],
            "week_ending": latest,
        }
    return out


def _latest_stage():
    cands = [f for f in os.listdir(BASE)
             if f.startswith("freight_landed_stage_") and f.endswith(".csv")]
    if not cands:
        raise FileNotFoundError("no staged freight CSV in " + BASE)
    cands.sort()
    return os.path.join(BASE, cands[-1])


# --------------------------------------------------------------- main ---

def refresh(raw_dir=None, backfill_weeks=0):
    """One-command refresh: fetch -> parse -> stage -> charts -> ranking."""
    today = dt.date.today()
    raw_dir = raw_dir or os.path.join(
        RAW_ROOT, "freight_%s" % today.isoformat())
    fetched = fetch_raw(raw_dir)
    fixtures, seen_we = [], set()
    if backfill_weeks:
        pdfs = sorted(
            [os.path.join(raw_dir, f) for f in os.listdir(raw_dir)
             if f.startswith("GTR") and f.endswith(".pdf")])
        for pdf in pdfs[-backfill_weeks:]:
            try:
                fixtures.extend(parse_fixtures(pdf))
            except Exception as e:  # noqa: BLE001 - one bad PDF skips
                print("  skip %s: %s"
                      % (os.path.basename(pdf), e))
    else:
        fixtures = parse_fixtures(fetched["gtr_latest.pdf"])
    fob = parse_fas_fob(fetched["grain_circular.pdf"])
    table1 = parse_table1_ocean(fetched["GTRTable1.xlsx"])
    manual = load_manual_legs(raw_dir)

    asof = max([f["week_ending"] for f in fixtures if f["week_ending"]]
               + [d for d, _, _ in table1]) if (fixtures or table1) else today
    rows = build_week(asof, fob, fixtures, table1, manual)
    spath = stage_path()
    already = set()
    if os.path.exists(spath):
        with open(spath) as f:
            for r in csv.DictReader(f):
                already.add(r["week_ending"])
    if asof.isoformat() in already:
        print("week %s already staged in %s; charts refreshed, no duplicate"
              % (asof, os.path.basename(spath)))
    else:
        append_stage(rows, spath)
        print("staged: %s (%d rows, week ending %s)"
              % (spath, len(rows), asof))
    write_charts(rows, table1, asof)

    print("staged: %s (%d rows, week ending %s)" % (spath, len(rows), asof))
    print("fixtures parsed: %d | FOB origins: %s"
          % (len(fixtures), sorted(fob)))
    print("\nLanded cost into China (US$/mt), cheapest first:")
    for o, mt, bu, f, fr, flag in ranking_table(rows, "CN"):
        print("  %-7s %7.1f  ($%.2f/bu)  FOB %6.1f + freight %5.1f  %s"
              % (o, mt, bu, f, fr, ("[%s]" % flag) if flag else ""))
    missing = [r["origin"] for r in rows
               if r["destination"] == "CN" and r["landed_usd_mt"] is None]
    if missing:
        print("no landed cost (data gap): %s" % ", ".join(missing))
    return spath


if __name__ == "__main__":
    import sys
    backfill = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    refresh(backfill_weeks=backfill if backfill else 0)
