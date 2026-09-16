#!/usr/bin/env python3
"""Generate italy-iceland/index.html from the two source Excel files only."""
import json
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

import openpyxl

ITIN = Path(
    "/cursor/stores/bc-911ee421-67df-4abb-9887-5dd4e4c275d4/artifacts/store/Compass/docs/2026意大利冰岛行程_复核补全版.xlsx"
)
PACK = Path(
    "/cursor/stores/bc-911ee421-67df-4abb-9887-5dd4e4c275d4/artifacts/store/Compass/docs/行李物品清单2.xlsx"
)
OUT = Path("/workspace/italy-iceland/index.html")

TZ_IT = "Europe/Rome"
TZ_IS = "Atlantic/Reykjavik"
TZ_UK = "Europe/London"
TZ_CN = "Asia/Shanghai"


def cell(v):
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v
    return str(v).strip()


def parse_time_val(v):
    if isinstance(v, datetime):
        return v.time().replace(microsecond=0)
    if isinstance(v, time):
        return v.replace(microsecond=0)
    s = str(v).strip()
    if not s:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            pass
    return None


def parse_date_val(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def tz_for_date(d: date) -> str:
    if d <= date(2026, 10, 2):
        return TZ_IT
    if d <= date(2026, 10, 7):
        return TZ_IS
    return TZ_CN


def iso_at(d: date, t: time, tz: str | None = None) -> str:
    tz = tz or tz_for_date(d)
    dt = datetime.combine(d, t)
    # Fixed offsets for trip window (no manual DST tables needed for display)
    offsets = {
        TZ_IT: "+02:00",
        TZ_IS: "+00:00",
        TZ_UK: "+01:00",
        TZ_CN: "+08:00",
    }
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + offsets[tz]


def fmt_hm(t: time) -> str:
    return t.strftime("%H:%M")


def badge(req: str):
    if not req:
        return None
    if any(x in req for x in ("无需预约", "无需线上预约", "可现场购票", "现场先到先得", "无法提前预约")):
        return {"t": req, "c": "free"}
    if any(
        x in req
        for x in (
            "已预约",
            "已预订",
            "已出票",
            "机票已出票",
            "酒店已预订",
            "包车已确认",
            "停车预约已完成",
            "必须已预订",
        )
    ):
        return {"t": req, "c": "done"}
    if "酒店待确认" in req:
        return {"t": req, "c": "need"}
    if any(x in req for x in ("必须", "强烈建议", "建议提前", "需提前", "必须预约", "必须核对", "必须提前")):
        return {"t": req, "c": "need"}
    if "酒店" in req:
        return {"t": req, "c": "stay"}
    return {"t": req, "c": "free"}


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def linkify_place(text: str, dest: str, link: str) -> str:
    if not text:
        return ""
    q = dest or text
    href = link or f"https://www.google.com/maps/search/?api=1&query={q}"
    return f'<a class="place" target="_blank" rel="noopener" href="{esc(href)}">{esc(text)}</a>'


def load_itinerary():
    wb = openpyxl.load_workbook(ITIN, data_only=True)
    ws = wb["详细行程"]
    title = cell(ws.cell(1, 1).value)
    assumption = cell(ws.cell(2, 1).value)

    rows = []
    for r in range(5, ws.max_row + 1):
        row = {k: cell(ws.cell(r, c).value) for c, k in enumerate(
            ["date", "dow", "start", "end", "region", "activity", "from", "to", "transport", "trans_min", "act_min", "booking", "tip", "link"],
            1,
        )}
        if not any(str(v) for v in row.values() if v != ""):
            continue
        rows.append(row)

    days = []
    cur_date = None
    cur = None
    day_n = 0
    last_region = ""
    colors = ["var(--d1)", "var(--d2)", "var(--d3)", "var(--d4)", "var(--d5)"]

    for row in rows:
        d = parse_date_val(row["date"])
        if d:
            cur_date = d
            day_n += 1
            dow = str(row["dow"]) if row["dow"] else ""
            region = str(row["region"]) if row["region"] else ""
            if region:
                last_region = region.split("→")[0].strip()
            cur = {
                "n": day_n,
                "date": cur_date.isoformat(),
                "dd": f"{cur_date.month}.{cur_date.day}",
                "dw": dow,
                "color": colors[(day_n - 1) % len(colors)],
                "title": region or last_region or str(row["activity"])[:24],
                "route": region,
                "regions": [],
                "items": [],
            }
            days.append(cur)
        if cur is None:
            continue
        if row["region"]:
            last_region = str(row["region"]).split("→")[0].strip()
            if str(row["region"]) not in cur["regions"]:
                cur["regions"].append(str(row["region"]))

        st = parse_time_val(row["start"])
        if not st or not cur_date:
            continue

        act = str(row["activity"])
        region = str(row["region"]) if row["region"] else ""
        dest = str(row["to"]) if row["to"] else (region or act)
        tip_parts = []
        if row["from"] and row["to"]:
            tip_parts.append(f"{row['from']} → {row['to']}")
        if row["transport"]:
            tip_parts.append(f"交通：{row['transport']}")
        if row["trans_min"]:
            tip_parts.append(f"交通约 {row['trans_min']} 分钟")
        if row["act_min"]:
            tip_parts.append(f"活动约 {row['act_min']} 分钟")
        if row["tip"]:
            tip_parts.append(str(row["tip"]))

        # Multi-timezone segments on Oct 2 and Oct 7
        tz = tz_for_date(cur_date)
        if cur_date == date(2026, 10, 2) and st >= time(15, 55):
            tz = TZ_IS if st >= time(18, 30) else TZ_IT
        if cur_date == date(2026, 10, 7):
            if st >= time(16, 10) and st < time(20, 20):
                tz = TZ_IS
            elif st >= time(20, 20):
                tz = TZ_UK
            if "HU7912" in act or (st >= time(22, 0)):
                tz = TZ_UK
        if cur_date == date(2026, 10, 8) or "(+1)" in act:
            tz = TZ_CN
            cur_date_eff = date(2026, 10, 8)
        else:
            cur_date_eff = cur_date

        # Handle (+1) times in activity/end - use end time hints
        end_t = parse_time_val(row["end"])
        if end_t and "(+1)" in str(row.get("end", "")):
            cur_date_eff = cur_date + timedelta(days=1)

        h = esc(act)
        if dest and dest != act and dest in act:
            h = esc(act).replace(esc(dest), linkify_place(dest, dest, str(row["link"])))
        elif region and region in act:
            h = esc(act).replace(esc(region), linkify_place(region, dest, str(row["link"])))

        item = {
            "at": iso_at(cur_date_eff if tz == TZ_CN and cur_date == date(2026, 10, 7) else cur_date, st, tz),
            "tz": tz,
            "h": h,
            "n": " · ".join(tip_parts),
            "mk": badge(str(row["booking"])) if row["booking"] else None,
        }
        if row["link"]:
            item["l"] = str(row["link"])
        cur["items"].append(item)

        # enrich day title/route from first/major regions
        if cur["regions"]:
            cur["route"] = " · ".join(cur["regions"][:4])
            if len(cur["title"]) < 4 and cur["regions"]:
                cur["title"] = cur["regions"][0]

    # Day summaries from first/last items
    for d in days:
        if d["items"]:
            first = d["items"][0]["at"]
            last = d["items"][-1]["at"]
            d["sum"] = f"{d['dd']} {d['dw']} · {len(d['items'])} 项 · {d['route'] or d['title']}"
        else:
            d["sum"] = d["route"] or d["title"]

    notes = []
    nws = wb["核对说明"]
    for r in range(3, nws.max_row + 1):
        pri = cell(nws.cell(r, 1).value)
        dt = cell(nws.cell(r, 2).value)
        item = cell(nws.cell(r, 3).value)
        conclusion = cell(nws.cell(r, 4).value)
        advice = cell(nws.cell(r, 5).value)
        src = cell(nws.cell(r, 6).value)
        if not item:
            continue
        notes.append({"pri": str(pri), "date": str(dt), "item": str(item), "conclusion": str(conclusion), "advice": str(advice), "src": str(src)})

    return title, assumption, days, notes


def load_packing():
    wb = openpyxl.load_workbook(PACK, data_only=True)
    ws = wb["Sheet1"]
    groups = []
    cur = None
    for r in range(2, ws.max_row + 1):
        name = cell(ws.cell(r, 2).value)
        qty = cell(ws.cell(r, 3).value)
        cat = cell(ws.cell(r, 4).value)
        note = cell(ws.cell(r, 6).value)
        if not name:
            if note == "按日期分装":
                continue
            continue
        cat = str(cat) if cat else "其他"
        if not cur or cur["g"] != cat:
            cur = {"g": cat, "items": []}
            groups.append(cur)
        entry = {"t": str(name), "q": str(qty) if qty != "" else ""}
        # optional date-pack columns G-I from excel
        extras = []
        for c in range(7, 10):
            v = cell(ws.cell(r, c).value)
            if v:
                extras.append(str(v))
        if note:
            extras.insert(0, str(note))
        if extras:
            entry["d"] = " · ".join(extras)
        cur["items"].append(entry)
    return groups


def extract_flights(days):
    flights = []
    for d in days:
        for it in d["items"]:
            h = re.sub(r"<[^>]+>", "", it["h"])
            if "VCE→KEF" in h or "VCE→KEF" in it.get("n", ""):
                flights.append(
                    {
                        "dir": "意大利 → 冰岛",
                        "date": "10/2 周五",
                        "no": "VCE→KEF 直飞",
                        "from": {"iata": "VCE", "city": "威尼斯马可·波罗", "at": it["at"], "tz": it["tz"]},
                        "to": {"iata": "KEF", "city": "凯夫拉维克", "at": None, "tz": TZ_IS},
                        "dur": "约 4h35m",
                        "note": it["n"],
                    }
                )
            if "FI454" in h:
                flights.append(
                    {
                        "dir": "冰岛 → 伦敦",
                        "date": "10/7 周三",
                        "no": "FI454",
                        "from": {"iata": "KEF", "city": "凯夫拉维克", "at": it["at"], "tz": TZ_IS},
                        "to": {"iata": "LHR", "city": "伦敦希思罗 T2", "at": None, "tz": TZ_UK},
                        "dur": "约 3h10m",
                        "note": it["n"],
                    }
                )
            if "HU7912" in h:
                flights.append(
                    {
                        "dir": "伦敦 → 海口",
                        "date": "10/7 周三",
                        "no": "HU7912",
                        "from": {"iata": "LHR", "city": "伦敦希思罗 T3", "at": it["at"], "tz": TZ_UK},
                        "to": {"iata": "HAK", "city": "海口 T2", "at": None, "tz": TZ_CN},
                        "dur": "约 18h30m",
                        "note": it["n"],
                    }
                )
    # Fill arrival times from following items
    for d in days:
        for i, it in enumerate(d["items"]):
            h = re.sub(r"<[^>]+>", "", it["h"])
            if "VCE→KEF" in h:
                for nxt in d["items"][i + 1 :]:
                    if "凯夫拉维克机场" in re.sub(r"<[^>]+>", "", nxt["h"]) and "入境" in nxt["h"]:
                        # find landing ~18:30 on same day
                        for x in d["items"]:
                            xh = re.sub(r"<[^>]+>", "", x["h"])
                            if "VCE→KEF" in xh:
                                pass
                        break
    # Hard-set from excel row data we know
    for fl in flights:
        if fl["no"] == "VCE→KEF 直飞":
            fl["from"]["at"] = iso_at(date(2026, 10, 2), time(15, 55), TZ_IT)
            fl["to"]["at"] = iso_at(date(2026, 10, 2), time(18, 30), TZ_IS)
        if fl["no"] == "FI454":
            fl["from"]["at"] = iso_at(date(2026, 10, 7), time(16, 10), TZ_IS)
            fl["to"]["at"] = iso_at(date(2026, 10, 7), time(20, 20), TZ_UK)
        if fl["no"] == "HU7912":
            fl["from"]["at"] = iso_at(date(2026, 10, 7), time(22, 0), TZ_UK)
            fl["to"]["at"] = iso_at(date(2026, 10, 8), time(16, 30), TZ_CN)
    # dedupe
    seen = set()
    out = []
    for f in flights:
        k = f["no"]
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def build_chips(days):
    chips = []
    text = json.dumps(days, ensure_ascii=False)
    if "机票已出票" in text:
        chips.append({"t": "✈ 机票已出票", "s": "done"})
    if "酒店已预订" in text:
        chips.append({"t": "🏨 部分酒店已预订", "s": "done"})
    if "酒店待确认" in text:
        chips.append({"t": "🏨 冰河湖周边酒店待确认", "s": "pending"})
    if "包车已确认" in text:
        chips.append({"t": "🚐 冰岛南岸包车已确认", "s": "done"})
    if "必须提前预约" in text or "必须提前锁定" in text:
        chips.append({"t": "🎫 部分景点需提前预约", "s": "pending"})
    return chips


def render_html(title, assumption, days, notes, packing, flights, chips):
    trip = {
        "emoji": "🇮🇹🇮🇸",
        "title": title.replace("｜", " · ").split("·")[0].strip() if title else "意大利＋冰岛",
        "sub": assumption,
        "chips": chips,
    }

    template = Path("/workspace/hokkaido/index.html").read_text(encoding="utf-8")

    # Build new file from hokkaido template structure but replace content sections
    # Safer: write complete HTML using same CSS from template
    css_end = template.index("</style>")
    css = template[template.index("<style>") : css_end + len("</style>")]

    nav_links = [
        ('overview', '🗺 总览'),
        ('flights', '✈ 航班'),
        ('days', '📅 每日行程'),
        ('review', '📋 复核说明'),
        ('pack', '🎒 行李清单'),
    ]

    nav_html = "\n".join(f'  <a href="#{a}">{t}</a>' for a, t in nav_links)

    # Overview day list
    ov_days = "".join(
        f'<li><i style="background:{d["color"]}"></i><b>D{d["n"]} · {d["dd"]} {d["dw"]}</b><span>{esc(d["title"])} —— {esc(d["sum"])}</span></li>'
        for d in days
    )

    # Flights
    fl_html = ""
    for f in flights:
        fl_html += f'''<div class="card fl">
    <div class="fl-top"><span>{esc(f["dir"])} · {esc(f["date"])} · {esc(f["no"])}</span><span class="tag-ok">机票已出票</span></div>
    <div class="fl-row">
      <div class="fl-pt"><div class="iata">{esc(f["from"]["iata"])}</div><div class="tm">{fmt_hm(datetime.fromisoformat(f["from"]["at"]).time())}</div><div class="city">{esc(f["from"]["city"])}</div></div>
      <div class="fl-mid">{esc(f["dur"])}<div class="ln"></div></div>
      <div class="fl-pt" style="text-align:right"><div class="iata">{esc(f["to"]["iata"])}</div><div class="tm">{fmt_hm(datetime.fromisoformat(f["to"]["at"]).time())}</div><div class="city">{esc(f["to"]["city"])}</div></div>
    </div>
    <div class="fl-note">{esc(f["note"])}</div>
  </div>'''

    # Days - simplified without map buttons (no map URLs in excel)
    day_html = ""
    for d in days:
        items_html = ""
        for it in d["items"]:
            mk = ""
            if it.get("mk"):
                mk = f'<span class="mk {it["mk"]["c"]}">{esc(it["mk"]["t"])}</span>'
            note = f'<div class="n">{esc(it["n"])}</div>' if it.get("n") else ""
            tm = fmt_hm(datetime.fromisoformat(it["at"]).time())
            items_html += f"<li><div class=\"t\">{tm}</div><div class=\"c\"><div class=\"h\">{it['h']}{mk}</div>{note}</div></li>"

        day_html += f'''<div class="card day" id="d{d["n"]}">
  <div class="day-hd">
    <div class="dbox" style="border-color:{d["color"]}"><div class="dd">{d["dd"]}</div><div class="dw">{esc(d["dw"])}</div></div>
    <div><h3>D{d["n"]} · {esc(d["title"])}</h3><div class="rt">{esc(d["route"])}</div></div>
  </div>
  <div class="tools"><span class="sum">{esc(d["sum"])}</span></div>
  <ul class="tl">{items_html}</ul>
</div>'''

    review_html = ""
    for n in notes:
        pri_cls = "need" if n["pri"] in ("高风险", "必须确认", "较紧", "注意天气") else "done" if n["pri"] == "确认" else "free"
        review_html += f'''<div class="card tip">
  <h4>{esc(n["pri"])} · {esc(n["date"])} · {esc(n["item"])}</h4>
  <p><strong>结论：</strong>{esc(n["conclusion"])}</p>
  <p><strong>建议：</strong>{esc(n["advice"])}</p>
  {f'<p><a href="{esc(n["src"])}" target="_blank" rel="noopener">来源 ↗</a></p>' if n["src"] else ''}
</div>'''

    pack_html = ""
    for g in packing:
        rows = ""
        for i, it in enumerate(g["items"], 1):
            qty = f' ×{esc(it["q"])}' if it.get("q") else ""
            det = f'<div class="dt">{esc(it["d"])}</div>' if it.get("d") else ""
            rows += f'''<div class="todo" id="pack{i}">
  <div class="bx">·</div><div class="bd"><div class="tt"><span>{esc(it["t"])}{qty}</span></div>{det}</div></div>'''
        pack_html += f'<div class="card tgroup"><h4>{esc(g["g"])}</h4>{rows}</div>'

    chips_html = "".join(f'<span class="chip {c["s"]}">{esc(c["t"])}</span>' for c in chips)

    data_js = f"""
const TZ = "{TZ_IT}";
const TRIP = {json.dumps(trip, ensure_ascii=False)};
const DAYS = {json.dumps(days, ensure_ascii=False)};
const FLIGHTS = {json.dumps(flights, ensure_ascii=False)};
"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f4f0ea" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#14110f" media="(prefers-color-scheme: dark)">
<meta name="description" content="{esc(trip['title'])} · 行程手册">
<title>{esc(trip['emoji'])} {esc(trip['title'])} · 行程手册</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ctext y='26' font-size='26'%3E🇮🇹%3C/text%3E%3C/svg%3E">
{css}
.pack .bx {{border:none;color:var(--ink3);font-weight:700;font-size:14px}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1 id="h-title"></h1>
  <p class="sub" id="h-sub"></p>
  <div class="chips" id="h-chips">{chips_html}</div>
</header>
<div class="now">
  <div class="now-label"><span class="dot"></span>此刻关注 · NOW</div>
  <p class="now-title" id="n-title">正在计算…</p>
  <p class="now-note" id="n-note"></p>
  <div class="count" id="n-count">--</div>
</div>
<nav>
{nav_html}
</nav>
<section id="overview">
  <h2>🗺 行程总览</h2>
  <div class="card mapbox">
    <svg viewBox="0 0 900 420" role="img" aria-label="意大利与冰岛路线概览">
      <defs><style>.ol{{fill:var(--mapland);stroke:var(--mapink);stroke-width:2}}.rt{{fill:none;stroke-width:4;stroke-linecap:round}}.lbl{{fill:var(--mapink);font:600 14px sans-serif}}</style></defs>
      <rect width="900" height="420" fill="var(--mapbg)" rx="12"/>
      <path class="ol" d="M80 280 Q180 120 320 180 T520 160 T680 200 L720 260 L640 320 L420 340 L200 320 Z"/>
      <text x="90" y="300" class="lbl">意大利</text>
      <path class="rt" stroke="var(--d1)" d="M140 260 L260 220 L380 200 L480 190"/>
      <path class="rt" stroke="var(--d2)" d="M480 190 L560 170 L620 185"/>
      <path class="rt" stroke="var(--d3)" stroke-dasharray="8 6" d="M650 195 Q780 120 820 80"/>
      <ellipse class="ol" cx="820" cy="95" rx="55" ry="35"/>
      <text x="790" y="100" class="lbl">冰岛</text>
      <path class="rt" stroke="var(--d4)" d="M805 110 L780 130 L760 150"/>
      <text x="120" y="240" class="lbl">佛罗伦萨</text>
      <text x="360" y="185" class="lbl">多洛米蒂</text>
      <text x="560" y="175" class="lbl">威尼斯 VCE</text>
      <text x="780" y="155" class="lbl">雷克雅未克</text>
      <text x="760" y="175" class="lbl" style="font-size:12px;opacity:.8">南岸 · 冰河湖</text>
    </svg>
  </div>
  <ul class="daylist" id="ov-days">{ov_days}</ul>
</section>
<section id="flights">
  <h2>✈ 航班（已出票）</h2>
  <p class="lead">仅列出 Excel 行程表中的国际航段；时间为各机场当地时间。</p>
  <div class="grid2" id="fl-list">{fl_html}</div>
</section>
<section id="days">
  <h2>📅 每日行程</h2>
  <p class="lead">时间来自 Excel《详细行程》表；9/25–10/2 为意大利时间（CEST），10/2 晚起为冰岛时间，返程段按各机场当地时间标注。</p>
  <div id="day-list">{day_html}</div>
</section>
<section id="review">
  <h2>📋 行程复核说明</h2>
  <p class="lead">来自 Excel《核对说明》表（2026年9月15日复核）。</p>
  <div class="tips">{review_html}</div>
</section>
<section id="pack" class="pack">
  <h2>🎒 行李物品清单</h2>
  <p class="lead">只读展示，不可勾选 —— 内容仅来自《行李物品清单》Excel，按分类列出。</p>
  <div id="pack-list">{pack_html}</div>
</section>
<footer>
  {esc(trip['title'])} · 行程手册 · 单文件网页，离线可看。<br>
  页面不含确认号、证件号与房间号；内容仅来自上传的两份 Excel。
</footer>
</div>
<script>
{data_js}
const $ = (s) => document.querySelector(s);
const fmtTime = (iso, tz) => new Intl.DateTimeFormat("zh-CN", {{
  timeZone: tz || TZ, hour: "2-digit", minute: "2-digit", hour12: false
}}).format(new Date(iso));

$("#h-title").textContent = TRIP.emoji + " " + TRIP.title;
$("#h-sub").textContent = TRIP.sub;

const EVENTS = [];
DAYS.forEach((d) => d.items.forEach((it) => EVENTS.push({{
  t: new Date(it.at).getTime(),
  title: it.h.replace(/<[^>]+>/g, ""),
  note: it.n || "",
  day: d,
  tz: it.tz
}})));
EVENTS.sort((a,b) => a.t - b.t);

const pad = (v) => String(v).padStart(2, "0");
function tick() {{
  const now = Date.now();
  const next = EVENTS.find((e) => e.t > now);
  if (!next) {{
    $("#n-title").textContent = "行程已结束";
    $("#n-note").textContent = "";
    $("#n-count").textContent = "完成 🇮🇹🇮🇸";
    return;
  }}
  $("#n-title").textContent = next.title;
  $("#n-note").textContent = "D" + next.day.n + " · " + next.day.dd + " " + next.day.dw + " · " + (next.note || next.day.title);
  let s = Math.floor((next.t - now) / 1000);
  const dd = Math.floor(s / 86400); s -= dd * 86400;
  const hh = Math.floor(s / 3600); s -= hh * 3600;
  const mm = Math.floor(s / 60); s -= mm * 60;
  $("#n-count").innerHTML = (dd > 0 ? dd + "天 " : "") + pad(hh) + ":" + pad(mm) + ":" + pad(s) + "<small>后</small>";
}}
tick(); setInterval(tick, 1000);

document.querySelectorAll('nav a').forEach((a) => {{
  a.addEventListener("click", (e) => {{
    const el = document.querySelector(a.getAttribute("href"));
    if (el) {{ e.preventDefault(); el.scrollIntoView({{ behavior: "smooth", block: "start" }}); }}
  }});
}});
</script>
</body>
</html>
"""
    return html


def main():
    title, assumption, days, notes = load_itinerary()
    packing = load_packing()
    flights = extract_flights(days)
    chips = build_chips(days)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_html(title, assumption, days, notes, packing, flights, chips), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(f"Days: {len(days)}, packing groups: {len(packing)}, flights: {len(flights)}, review items: {len(notes)}")


if __name__ == "__main__":
    main()
