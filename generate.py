"""
generate.py — Nowy Sącz weather dashboard generator
Fetches wttr.in JSON, produces index.html.
Dependencies: requests
"""
import json
import sys
from datetime import datetime
import requests

# ── Fetch ──────────────────────────────────────────────────────────────────
URL = "https://wttr.in/Nowy+Sacz?lang=pl&format=j1"
if len(sys.argv) > 1:
    # Local testing: python generate.py path/to/wttr.json
    with open(sys.argv[1], encoding="utf-8-sig") as f:
        data = json.load(f)
else:
    data = requests.get(URL, timeout=15).json()

cur   = data["current_condition"][0]
days  = data["weather"]  # 3 days

# ── Helpers ────────────────────────────────────────────────────────────────
def emoji(desc):
    d = desc.lower().strip()
    if "sunny" in d or "clear" in d:                          return "&#x2600;&#xFE0F;"
    if "partly" in d:                                          return "&#x26C5;"
    if "overcast" in d or "cloudy" in d:                       return "&#x2601;&#xFE0F;"
    if "patchy rain" in d or "drizzle" in d or "light rain" in d: return "&#x1F326;&#xFE0F;"
    if "thunder" in d:                                         return "&#x26C8;&#xFE0F;"
    if "rain" in d:                                            return "&#x1F327;&#xFE0F;"
    if "snow" in d or "sleet" in d or "blizzard" in d:         return "&#x1F328;&#xFE0F;"
    if "fog" in d or "mist" in d or "haze" in d:               return "&#x1F32B;&#xFE0F;"
    return "&#x1F321;&#xFE0F;"

def temp_class(t):
    t = int(t)
    if t < 8:   return "tcc"
    if t <= 15: return "tc"
    return "tw"

def rain_class(r): return "rain-hi" if int(r) >= 60 else "rain-lo"
def note_class(r): return "note alert" if int(r) >= 60 else "note"

def rain_bar(r):
    r = int(r)
    if r == 0: return ""
    return f'<div class="rain-bar"><div class="rain-fill" style="width:{r}%"></div></div>'

def slot_note(rain, wind, temp, part):
    rain, wind, temp = int(rain), int(wind), int(temp)
    if rain == 100:            return "Wet conditions. Use caution."
    if rain >= 60 and wind >= 20: return "Rain likely. Windy."
    if rain >= 60:             return "Rain likely."
    if temp < 8 and rain == 0: return "Chilly start. Layer up."
    if rain == 0 and wind >= 20: return "Dry but breezy."
    if rain == 0 and wind < 10:
        notes = {"morning": "Pleasant start. Light breeze.",
                 "afternoon": "Good outdoors.",
                 "evening": "Nice evening. Good visibility."}
        return notes[part]
    notes = {"morning": "Cool and dry. Grey skies.",
             "afternoon": "Comfortable. Light breeze.",
             "evening": "Calm evening. Dry conditions."}
    return notes[part]

def fmt_time_ampm(t):
    """'05:07 AM' → '05:07',  '08:08 PM' → '20:08'"""
    return datetime.strptime(t.strip(), "%I:%M %p").strftime("%H:%M")

def day_abbr(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%a").upper()

def day_ddmm(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m")

# ── Extract slots ──────────────────────────────────────────────────────────
SLOT_IDX = {"morning": 2, "afternoon": 4, "evening": 6}
PARTS    = ["morning", "afternoon", "evening"]

slots = []  # list of dicts, one per (day, part)
for di, day in enumerate(days):
    for part in PARTS:
        h = day["hourly"][SLOT_IDX[part]]
        slots.append({
            "day_idx":  di,
            "date":     day["date"],
            "part":     part,
            "temp":     int(h["tempC"]),
            "desc":     h["weatherDesc"][0]["value"].strip(),
            "rain":     int(h["chanceofrain"]),
            "wind":     int(h["windspeedKmph"]),
            "emoji":    emoji(h["weatherDesc"][0]["value"]),
            "tclass":   temp_class(h["tempC"]),
            "rclass":   rain_class(h["chanceofrain"]),
            "nclass":   note_class(h["chanceofrain"]),
            "note":     slot_note(h["chanceofrain"], h["windspeedKmph"], h["tempC"], part),
            "rainbar":  rain_bar(h["chanceofrain"]),
        })

# ── Forecast confidence ────────────────────────────────────────────────────
rains = [s["rain"] for s in slots]
if any(r > 60 for r in rains):
    conf_pct  = 80
    conf_note = "High confidence in dry periods.<br>Rain timing has moderate uncertainty."
elif all(r <= 30 for r in rains):
    conf_pct  = 92
    conf_note = "High confidence in dry and settled conditions."
else:
    conf_pct  = 84
    conf_note = "Dry periods reliable; rain windows less certain."

# ── Quick Insights ─────────────────────────────────────────────────────────
wet_slots = [s for s in slots if s["rain"] > 60]
if wet_slots:
    ws       = wet_slots[0]
    day_name = day_abbr(ws["date"])
    last_wet = wet_slots[-1]
    if last_wet is ws:
        ins_rain = f"High {day_name} {ws['part']}"
    else:
        ins_rain = f"High {day_name} {ws['part']}–{last_wet['part']}"
else:
    ins_rain = "Low across all days"

max_wind_slot = max(slots, key=lambda s: s["wind"])
wlvl = "Strong" if max_wind_slot["wind"] >= 30 else "Moderate" if max_wind_slot["wind"] >= 15 else "Light"
ins_wind = f"{wlvl}, strongest {day_abbr(max_wind_slot['date'])} {max_wind_slot['part']}"

dry_mild = [s for s in slots if s["rain"] == 0 and 10 <= s["temp"] <= 20 and s["wind"] < 20]
if len(dry_mild) >= 2:
    a, b = dry_mild[0], dry_mild[1]
    ins_best = f"{day_abbr(a['date'])} {a['part']} &amp; {day_abbr(b['date'])} {b['part']}"
elif dry_mild:
    a = dry_mild[0]
    ins_best = f"{day_abbr(a['date'])} {a['part']}"
else:
    ins_best = "Limited dry windows"

morning_temps = [s["temp"] for s in slots if s["part"] == "morning"]
aft_temps     = [s["temp"] for s in slots if s["part"] == "afternoon"]
ins_comfort   = f"Cool mornings ({min(morning_temps)}–{max(morning_temps)}°C), mild afternoons"

if wet_slots:
    ins_watch = f"Wet roads {day_abbr(wet_slots[-1]['date'])} {wet_slots[-1]['part']}"
elif min(morning_temps) < 5:
    cold_day = [s for s in slots if s["part"] == "morning" and s["temp"] < 5][0]
    ins_watch = f"Frost risk {day_abbr(cold_day['date'])} morning"
else:
    ins_watch = "Check hourly before heading out"

# ── Best & Worst times ────────────────────────────────────────────────────
score_best = lambda s: (100 - s["rain"]) - s["wind"] + s["temp"]
score_worst = lambda s: s["rain"] + s["wind"] - s["temp"]
best_slot  = max(slots, key=score_best)
worst_slot = max(slots, key=score_worst)

PART_HOURS = {"morning": "06:00–09:00", "afternoon": "12:00–15:00", "evening": "18:00–21:00"}
best_time  = f"{day_abbr(best_slot['date'])} {best_slot['part']}<br>{PART_HOURS[best_slot['part']]}"
best_why   = f"Dry, {best_slot['temp']}°C, {best_slot['wind']} km/h wind"
worst_time = f"{day_abbr(worst_slot['date'])} {worst_slot['part']}<br>{PART_HOURS[worst_slot['part']]}"
worst_why_parts = []
if worst_slot["rain"] >= 60: worst_why_parts.append("Rain")
if worst_slot["wind"] >= 20: worst_why_parts.append("strong wind")
if worst_slot["temp"] < 5:  worst_why_parts.append("near-frost temp")
worst_why = ", ".join(worst_why_parts) if worst_why_parts else f"{worst_slot['rain']}% rain, {worst_slot['wind']} km/h"

# ── What to Wear ──────────────────────────────────────────────────────────
rainy_days   = list(dict.fromkeys(day_abbr(s["date"]) for s in wet_slots))
dry_days     = [day_abbr(d["date"]) for d in days if not any(s["rain"] > 60 for s in slots if s["date"] == d["date"])]
max_temps    = [int(d["maxtempC"]) for d in days]
min_temps    = [int(d["mintempC"]) for d in days]

wear_rows = ""
if rainy_days:
    wear_rows += f'''<div class="wear-row"><div class="wear-icon">&#x2602;&#xFE0F;</div><div class="wear-txt"><strong>{" &amp; ".join(rainy_days)}:</strong><br>Bring umbrella &amp; waterproof</div></div>'''
if dry_days:
    avg_max = sum(max_temps) / len(max_temps)
    jacket = "Light jacket recommended" if avg_max < 18 else "T-shirt weather, layer for evenings"
    wear_rows += f'''<div class="wear-row"><div class="wear-icon">&#x1F9E5;</div><div class="wear-txt"><strong>{" &amp; ".join(dry_days[:2])}:</strong><br>{jacket}</div></div>'''

# ── Activity ratings ──────────────────────────────────────────────────────
wet_count    = sum(1 for s in slots if s["rain"] > 60)
cold_morning = any(s["temp"] < 5 for s in slots if s["part"] == "morning")
max_wind     = max(s["wind"] for s in slots)
has_100_rain = any(s["rain"] == 100 for s in slots)

def rating_badge(r, note=""):
    cls = {"GOOD": "ag", "FAIR": "af", "POOR": "ap"}[r]
    txt = f"{r} ({note})" if note else r
    return f'<span class="{cls}">{txt}</span>'

walk_r  = "POOR" if wet_count >= 4 else "FAIR" if wet_count >= 1 else "GOOD"
cycle_r = "POOR" if wet_count >= 2 or max_wind >= 30 else "FAIR" if wet_count >= 1 or max_wind >= 20 else "GOOD"
hike_note = "Sat AM" if any(s["temp"] < 8 and s["part"] == "morning" and day_abbr(s["date"]) == "SAT" for s in slots) else ""
hike_r  = "POOR" if wet_count >= 3 else "FAIR" if wet_count >= 1 or cold_morning else "GOOD"
photo_r = "POOR" if wet_count >= 4 else "FAIR" if wet_count >= 2 else "GOOD"
drive_r = "POOR" if has_100_rain else "FAIR" if wet_count >= 1 else "GOOD"
drive_note = f"{day_abbr(wet_slots[-1]['date'])} {wet_slots[-1]['part'].title()}" if wet_slots else ""

act_rows = f"""
<div class="act-row"><span class="act-name">&#x1F6B6; Walking / Leisure</span>{rating_badge(walk_r)}</div>
<div class="act-row"><span class="act-name">&#x1F6B4; Cycling</span>{rating_badge(cycle_r)}</div>
<div class="act-row"><span class="act-name">&#x1F97E; Hiking</span>{rating_badge(hike_r, hike_note)}</div>
<div class="act-row"><span class="act-name">&#x1F4F7; Photography</span>{rating_badge(photo_r)}</div>
<div class="act-row"><span class="act-name">&#x1F697; Driving</span>{rating_badge(drive_r, drive_note)}</div>
"""

# ── Lawn watering recommendation ─────────────────────────────────────────
today_slots    = [s for s in slots if s["day_idx"] == 0]
tomorrow_slots = [s for s in slots if s["day_idx"] == 1]
today_rain_max    = max(s["rain"] for s in today_slots)
tomorrow_rain_max = max(s["rain"] for s in tomorrow_slots)
today_max_t       = int(days[0]["maxtempC"])

if today_rain_max >= 60:
    lawn_verdict = "Nie podlewaj"
    lawn_color   = "red"
    lawn_bg      = "#fef2f2"
    lawn_emoji   = "&#x1F6AB;"
    lawn_when    = "&#x2014;"
    lawn_amount  = "&#x2014;"
    lawn_reason  = f"Deszcz prognozowany dzi&#x15B; ({today_rain_max}&#x25; szans) &#x2014; trawnik sam si&#x119; nawodni."
elif tomorrow_rain_max >= 60:
    lawn_verdict = "Poczekaj do jutra"
    lawn_color   = "yellow"
    lawn_bg      = "#fefce8"
    lawn_emoji   = "&#x23F3;"
    lawn_when    = "&#x2014;"
    lawn_amount  = "&#x2014;"
    lawn_reason  = f"Jutro prognozowany deszcz ({tomorrow_rain_max}&#x25; szans) &#x2014; oszcz&#x119;d&#x17A; wod&#x119;."
elif today_rain_max >= 30:
    lawn_verdict = "Opcjonalnie"
    lawn_color   = "yellow"
    lawn_bg      = "#fefce8"
    lawn_emoji   = "&#x1F914;"
    lawn_when    = "Wieczorem (18:00&#x2013;20:00)"
    lawn_amount  = "5&#x2013;10 l/m&#xB2;"
    lawn_reason  = f"Mo&#x17C;liwy lekki deszcz ({today_rain_max}&#x25;) &#x2014; podlej tylko je&#x15B;li gleba sucha."
else:
    lawn_verdict = "Podlej dzi&#x15B;"
    lawn_color   = "green"
    lawn_bg      = "#f0fdf4"
    lawn_emoji   = "&#x1F4A7;"
    if today_max_t >= 25:
        lawn_when   = "Rano (6:00&#x2013;8:00) &#x2014; przed upa&#x142;em"
        lawn_amount = "15&#x2013;20 l/m&#xB2; (~25 min zraszacz)"
        lawn_reason = f"Gor&#x105;cy dzie&#x144; ({today_max_t}&#xB0;C), brak opad&#xF3;w &#x2014; podlewaj wcze&#x15B;nie rano, by unikn&#x105;&#x107; parowania."
    elif today_max_t >= 15:
        lawn_when   = "Rano (6:00&#x2013;8:00) lub wieczorem (18:00&#x2013;20:00)"
        lawn_amount = "10&#x2013;15 l/m&#xB2; (~15&#x2013;20 min zraszacz)"
        lawn_reason = f"Sucho i {today_max_t}&#xB0;C &#x2014; optymalne warunki, unikaj podlewania w po&#x142;udnie."
    else:
        lawn_when   = "Wieczorem (18:00&#x2013;20:00)"
        lawn_amount = "5&#x2013;10 l/m&#xB2; (~10&#x2013;15 min zraszacz)"
        lawn_reason = f"Ch&#x142;odny dzie&#x144; ({today_max_t}&#xB0;C) bez opad&#xF3;w &#x2014; ma&#x142;e podlewanie wystarczy."

# ── Temperature trend SVG ─────────────────────────────────────────────────
max_t = [int(d["maxtempC"]) for d in days]
xs    = [50, 100, 150]
ys    = [70 - (t - 5) * 4 for t in max_t]
day_abbrs = [day_abbr(d["date"]) for d in days]

def lbl_y(y): return y + 12 if y < 18 else y - 6

pts = " ".join(f"{x},{y}" for x, y in zip(xs, ys))
trend_svg = f"""<svg viewBox="0 0 160 90" style="width:100%;height:84px;overflow:visible">
  <text x="12" y="13" font-size="9" fill="#d1d5db">20&#xB0;</text>
  <text x="12" y="33" font-size="9" fill="#d1d5db">15&#xB0;</text>
  <text x="12" y="53" font-size="9" fill="#d1d5db">10&#xB0;</text>
  <text x="12" y="73" font-size="9" fill="#d1d5db">5&#xB0;</text>
  <line x1="28" y1="10" x2="155" y2="10" stroke="#f3f4f6" stroke-width="1"/>
  <line x1="28" y1="30" x2="155" y2="30" stroke="#f3f4f6" stroke-width="1"/>
  <line x1="28" y1="50" x2="155" y2="50" stroke="#f3f4f6" stroke-width="1"/>
  <line x1="28" y1="70" x2="155" y2="70" stroke="#f3f4f6" stroke-width="1"/>
  <polyline points="{pts}" fill="none" stroke="#fb923c" stroke-width="2.5" stroke-linejoin="round"/>
  {"".join(f'<circle cx="{x}" cy="{y}" r="5" fill="#fb923c"/>' for x,y in zip(xs,ys))}
  {"".join(f'<text x="{x}" y="{lbl_y(y)}" font-size="9" fill="#374151" text-anchor="middle" font-weight="600">{t}&#xB0;</text>' for x,y,t in zip(xs,ys,max_t))}
  {"".join(f'<text x="{x}" y="83" font-size="9" fill="#9ca3af" text-anchor="middle">{a}</text>' for x,a in zip(xs,day_abbrs))}
</svg>"""

# ── Weather Story ─────────────────────────────────────────────────────────
def describe_day(di):
    day_slots = [s for s in slots if s["day_idx"] == di]
    has_rain  = any(s["rain"] > 60 for s in day_slots)
    max_rain  = max(s["rain"] for s in day_slots)
    max_w     = max(s["wind"] for s in day_slots)
    max_t_val = int(days[di]["maxtempC"])
    name      = day_abbr(days[di]["date"])
    if has_rain and max_w >= 20:
        return f"{name} brings rain and stronger winds (up to {max_w} km/h, {max_rain}% rain chance)"
    if has_rain:
        return f"{name} sees patchy rain with {max_rain}% chance at peak"
    return f"{name} stays dry and calm, reaching {max_t_val}°C"

story_parts = [describe_day(0), describe_day(1), describe_day(2)]
story = f"{story_parts[0].capitalize()}. {story_parts[1].capitalize()}. {story_parts[2].capitalize()}."

# ── Day blocks HTML ───────────────────────────────────────────────────────
def build_day_block(di):
    day   = days[di]
    name  = day_abbr(day["date"])
    ddmm  = day_ddmm(day["date"])
    rise  = fmt_time_ampm(day["astronomy"][0]["sunrise"])
    sset  = fmt_time_ampm(day["astronomy"][0]["sunset"])
    rows  = ""
    for pi, part in enumerate(PARTS):
        s      = slots[di * 3 + pi]
        first  = ' first' if pi == 0 else ''
        day_cell = f'<div><div class="dname">{name}</div><div class="ddate">{ddmm}</div><div class="dsun">&#x2600; {rise}<br>&#x2193; {sset}</div></div>' if pi == 0 else '<div></div>'
        rows += f"""
      <div class="day-row{first}">
        {day_cell}
        <div class="part">{part.capitalize()}</div>
        <div class="weath"><span class="wi">{s["emoji"]}</span><span class="wd">{s["desc"]}</span></div>
        <div class="temp-pill {s['tclass']}">{s['temp']}&#xB0;C</div>
        <div><div class="rain-pct {s['rclass']}">{s['rain']}%</div>{s['rainbar']}</div>
        <div class="wind-cell">&#x1F4A8; {s['wind']} km/h</div>
        <div class="{s['nclass']}">{s['note']}</div>
      </div>"""
    return f'<div class="day-block">{rows}\n    </div>'

day_blocks = "\n    ".join(build_day_block(i) for i in range(3))

# ── Current conditions ────────────────────────────────────────────────────
cur_emoji = emoji(cur["weatherDesc"][0]["value"])
cur_temp  = cur["temp_C"]
cur_feels = cur["FeelsLikeC"]
cur_desc  = cur["weatherDesc"][0]["value"].strip()
cur_wind  = cur["windspeedKmph"]
updated   = datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")

# ── Assemble HTML ─────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="3600">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pogoda Nowy S&#x105;cz</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#e8f0f7; display:flex; justify-content:center; padding:20px; min-height:100vh; }}
  .card {{ background:#fff; border-radius:20px; max-width:860px; width:100%; box-shadow:0 6px 32px rgba(0,0,0,.12); overflow:hidden; }}
  .header {{ background:linear-gradient(160deg,#deeefb 0%,#f0f8ff 100%); padding:20px 26px; display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }}
  .hdr-left {{ display:flex; align-items:center; gap:12px; }}
  .hdr-icon {{ font-size:62px; line-height:1; }}
  .hdr-temp {{ font-size:62px; font-weight:800; color:#111827; line-height:1; }}
  .hdr-feels {{ font-size:12px; color:#6b7280; margin-top:3px; text-transform:uppercase; letter-spacing:.3px; }}
  .hdr-mid {{ margin-left:10px; }}
  .hdr-desc {{ font-size:28px; font-weight:700; color:#111827; }}
  .hdr-location {{ font-size:12px; color:#6b7280; margin-bottom:4px; letter-spacing:.2px; }}
  .hdr-wind {{ font-size:14px; color:#6b7280; margin-top:5px; }}
  .hdr-right {{ text-align:right; min-width:180px; }}
  .conf-title {{ font-size:10px; font-weight:800; color:#2563eb; text-transform:uppercase; letter-spacing:.6px; }}
  .conf-bar-wrap {{ background:#e5e7eb; border-radius:6px; height:9px; margin:6px 0 3px; overflow:hidden; }}
  .conf-bar {{ background:linear-gradient(90deg,#4ade80,#16a34a); height:9px; border-radius:6px; }}
  .conf-pct {{ font-size:24px; font-weight:800; color:#111827; }}
  .conf-note {{ font-size:10.5px; color:#6b7280; line-height:1.4; margin-top:2px; }}
  .insights {{ padding:14px 26px; background:#f8fafc; border-bottom:1px solid #e5e7eb; }}
  .section-title {{ font-size:10px; font-weight:800; color:#2563eb; text-transform:uppercase; letter-spacing:.8px; margin-bottom:10px; }}
  .insights-grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:4px; }}
  .ins-icon {{ font-size:20px; margin-bottom:2px; }}
  .ins-label {{ font-size:11px; font-weight:700; color:#1f2937; margin-bottom:1px; }}
  .ins-val {{ font-size:11px; color:#6b7280; line-height:1.3; }}
  .forecast {{ padding:16px 26px 12px; }}
  .forecast-hdr {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }}
  .forecast-hdr h2 {{ font-size:15px; font-weight:800; color:#111827; }}
  .fc-legend {{ font-size:11px; color:#9ca3af; display:flex; gap:12px; }}
  .day-block {{ border:1.5px solid #e5e7eb; border-radius:12px; overflow:hidden; margin-bottom:8px; }}
  .day-row {{ display:grid; grid-template-columns:78px 86px 148px 60px 78px 74px 1fr; align-items:center; padding:8px 11px; gap:5px; border-bottom:1px solid #f3f4f6; }}
  .day-row:last-child {{ border-bottom:none; }}
  .day-row.first {{ background:#f8fafc; }}
  .dname {{ font-size:18px; font-weight:900; color:#2563eb; line-height:1.1; }}
  .ddate {{ font-size:13px; font-weight:700; color:#2563eb; }}
  .dsun {{ font-size:10px; color:#f59e0b; margin-top:2px; line-height:1.5; }}
  .part {{ font-size:12.5px; color:#374151; font-weight:500; }}
  .weath {{ display:flex; align-items:center; gap:5px; }}
  .wi {{ font-size:18px; }}
  .wd {{ font-size:11px; color:#374151; line-height:1.3; }}
  .temp-pill {{ font-size:12px; font-weight:700; padding:3px 7px; border-radius:6px; text-align:center; }}
  .tw  {{ background:#fef9c3; color:#92400e; }}
  .tc  {{ background:#dbeafe; color:#1e40af; }}
  .tcc {{ background:#bfdbfe; color:#1e3a8a; }}
  .rain-pct {{ font-size:12px; font-weight:700; }}
  .rain-lo {{ color:#9ca3af; }}
  .rain-hi {{ color:#1d4ed8; }}
  .rain-bar {{ height:4px; background:#e5e7eb; border-radius:2px; margin-top:2px; }}
  .rain-fill {{ height:4px; background:#3b82f6; border-radius:2px; }}
  .wind-cell {{ font-size:11px; color:#6b7280; }}
  .note {{ font-size:11px; color:#374151; line-height:1.35; }}
  .note.alert {{ color:#dc2626; font-weight:700; }}
  .bottom4 {{ display:grid; grid-template-columns:repeat(4,1fr); border-top:1.5px solid #e5e7eb; }}
  .bsec {{ padding:12px 14px 14px; border-right:1px solid #e5e7eb; }}
  .bsec:last-child {{ border-right:none; }}
  .bsec-title {{ font-size:10px; font-weight:800; color:#2563eb; text-transform:uppercase; letter-spacing:.6px; margin-bottom:8px; }}
  .bw-item {{ margin-bottom:8px; }}
  .bw-head {{ font-size:11px; font-weight:800; }}
  .bw-head.g {{ color:#16a34a; }}
  .bw-head.r {{ color:#dc2626; }}
  .bw-time {{ font-size:11.5px; font-weight:700; color:#111827; margin-top:1px; line-height:1.35; }}
  .bw-why  {{ font-size:10.5px; color:#6b7280; margin-top:1px; }}
  .wear-row {{ display:flex; align-items:flex-start; gap:7px; margin-bottom:7px; }}
  .wear-icon {{ font-size:22px; }}
  .wear-txt {{ font-size:11px; color:#374151; line-height:1.4; }}
  .wear-txt strong {{ color:#111827; }}
  .act-row {{ display:flex; justify-content:space-between; align-items:center; font-size:11.5px; margin-bottom:4px; }}
  .act-name {{ display:flex; align-items:center; gap:3px; color:#374151; }}
  .ag {{ color:#16a34a; font-weight:800; font-size:10.5px; }}
  .af {{ color:#d97706; font-weight:800; font-size:10.5px; }}
  .ap {{ color:#dc2626; font-weight:800; font-size:10.5px; }}
  .story {{ padding:12px 26px 15px; background:#f8fafc; border-top:1.5px solid #e5e7eb; display:flex; align-items:flex-start; gap:10px; }}
  .story-badge {{ background:#2563eb; color:#fff; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; flex-shrink:0; margin-top:1px; }}
  .story-label {{ font-size:10px; font-weight:800; color:#2563eb; text-transform:uppercase; letter-spacing:.6px; margin-bottom:2px; }}
  .story-text {{ font-size:11.5px; color:#4b5563; line-height:1.5; }}
  .updated {{ font-size:9px; color:#d1d5db; text-align:center; padding:6px; background:#f8fafc; }}
  .lawn-rec {{ padding:14px 26px; border-bottom:1px solid #e5e7eb; display:flex; align-items:center; gap:16px; }}
  .lawn-badge {{ font-size:36px; flex-shrink:0; }}
  .lawn-title {{ font-size:10px; font-weight:800; color:#2563eb; text-transform:uppercase; letter-spacing:.8px; margin-bottom:5px; }}
  .lawn-verdict {{ font-size:20px; font-weight:800; margin-bottom:4px; }}
  .lawn-green {{ color:#16a34a; }}
  .lawn-yellow {{ color:#d97706; }}
  .lawn-red {{ color:#dc2626; }}
  .lawn-meta {{ display:flex; flex-wrap:wrap; gap:18px; font-size:12px; color:#374151; margin-bottom:4px; font-weight:500; }}
  .lawn-reason {{ font-size:11px; color:#6b7280; line-height:1.45; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="hdr-left">
      <div class="hdr-icon">{cur_emoji}</div>
      <div>
        <div class="hdr-temp">{cur_temp}&#xB0;C</div>
        <div class="hdr-feels">Feels like {cur_feels}&#xB0;C</div>
      </div>
      <div class="hdr-mid">
        <div class="hdr-location">&#x1F4CD; Nowy S&#x105;cz, Poland</div>
        <div class="hdr-desc">{cur_desc}</div>
        <div class="hdr-wind">&#x1F4A8; Wind {cur_wind} km/h</div>
      </div>
    </div>
    <div class="hdr-right">
      <div class="conf-title">Forecast Confidence</div>
      <div class="conf-bar-wrap"><div class="conf-bar" style="width:{conf_pct}%"></div></div>
      <div class="conf-pct">{conf_pct}%</div>
      <div class="conf-note">{conf_note}</div>
    </div>
  </div>

  <div class="insights">
    <div class="section-title">Quick Insights</div>
    <div class="insights-grid">
      <div><div class="ins-icon">&#x1F302;</div><div class="ins-label">Rain risk</div><div class="ins-val">{ins_rain}</div></div>
      <div><div class="ins-icon">&#x1F32C;&#xFE0F;</div><div class="ins-label">Wind</div><div class="ins-val">{ins_wind}</div></div>
      <div><div class="ins-icon">&#x1F324;&#xFE0F;</div><div class="ins-label">Best window</div><div class="ins-val">{ins_best}</div></div>
      <div><div class="ins-icon">&#x1F321;&#xFE0F;</div><div class="ins-label">Comfort</div><div class="ins-val">{ins_comfort}</div></div>
      <div><div class="ins-icon">&#x26A0;&#xFE0F;</div><div class="ins-label">Watch out</div><div class="ins-val">{ins_watch}</div></div>
    </div>
  </div>

  <div class="lawn-rec" style="background:{lawn_bg}">
    <div class="lawn-badge">{lawn_emoji}</div>
    <div style="flex:1">
      <div class="lawn-title">&#x1F33F; Podlewanie trawnika</div>
      <div class="lawn-verdict lawn-{lawn_color}">{lawn_verdict}</div>
      <div class="lawn-meta">
        <span>&#x1F558;&nbsp;{lawn_when}</span>
        <span>&#x1F4A7;&nbsp;{lawn_amount}</span>
      </div>
      <div class="lawn-reason">{lawn_reason}</div>
    </div>
  </div>

  <div class="forecast">
    <div class="forecast-hdr">
      <h2>3-DAY DETAILED FORECAST</h2>
      <div class="fc-legend"><span>&#x1F4A7; Rain %</span><span>&#x1F4A8; Wind</span></div>
    </div>
    {day_blocks}
  </div>

  <div class="bottom4">
    <div class="bsec">
      <div class="bsec-title">Best &amp; Worst Times</div>
      <div class="bw-item"><div class="bw-head g">&#x2705; BEST</div><div class="bw-time">{best_time}</div><div class="bw-why">{best_why}</div></div>
      <div class="bw-item"><div class="bw-head r">&#x274C; WORST</div><div class="bw-time">{worst_time}</div><div class="bw-why">{worst_why}</div></div>
    </div>
    <div class="bsec">
      <div class="bsec-title">What to Wear</div>
      {wear_rows}
    </div>
    <div class="bsec">
      <div class="bsec-title">Activity Outlook</div>
      {act_rows}
    </div>
    <div class="bsec">
      <div class="bsec-title">Temperature Trend</div>
      {trend_svg}
    </div>
  </div>

  <div class="story">
    <div class="story-badge">i</div>
    <div>
      <div class="story-label">Weather Story</div>
      <div class="story-text">{story}</div>
    </div>
  </div>
  <div class="updated">Last updated: {updated}</div>
</div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"index.html written — {cur_temp}°C {cur_desc}, conf {conf_pct}%")
