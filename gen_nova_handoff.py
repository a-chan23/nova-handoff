#!/usr/bin/env python3
"""NOVA board — 12-hour QA->Prod handoff report generator. UTC-only times.

Reads tickets.json (list of ticket objects) from this directory, writes nova_handoff.html.
Ticket object:
  {"key","summary","currentStatus","assignee","priority",
   "statusChanges":[{"ts","author","from","to"}], "comments":[{"ts","author","body"}]}
Reference "now" for the 12h window + QA-age = env HANDOFF_NOW (ISO) else system now (UTC).

Dark three-column dashboard: left nav rail; center column with stat cards, a 10-day
pipeline trend, In-QA aging watch, module/component regression risk, and collapsible
pipeline sections; right rail with the "since last handoff" activity feed.
"""
import json, os, html, re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://powerdigital.atlassian.net/browse/"
BOARD_URL = "https://powerdigital.atlassian.net/jira/software/c/projects/NOVA/boards/338"
UTC = ZoneInfo("UTC")
WINDOW = timedelta(hours=12)
STATUS_ORDER = ["IN QA", "READY FOR PROD", "DEPLOYED TO PROD"]
# Stage colours mapped to nova/Nebula semantics: In QA = caution orange, Ready = electric
# purple (brand), Deployed = nova green (success/done).
STATUS_META = {
    "IN QA":            ("#f0a45e", "In QA",          "🧪"),
    "READY FOR PROD":   ("#8b93ff", "Ready for Prod", "✅"),
    "DEPLOYED TO PROD": ("#2fd6a6", "Deployed",       "🚀"),
}
PRIO_COLOR = {"Critical":"#ff6f61","Highest":"#f0a45e","High":"#f0a45e",
              "Medium":"#8b93a7","Low":"#5f6675","-":"#5f6675"}
STAGE_SHORT = {"IN QA":"QA", "READY FOR PROD":"Ready", "DEPLOYED TO PROD":"Prod"}

# nova product modules → keyword lists (matched against summary + comment text, lowercased).
# Module names mirror the real nova-web source tree (src/features/*), so regression risk
# maps to the actual code modules: intelligence/{creative-reports,comparative-reports,
# all-ads,creative-affinity,playbook,mixpanel}, creative-collab, library, talent, @sprnova/nebula.
NOVA_MODULES = {
    "Intelligence · Creative Reports":    ["creative report","table view","tableview","net results table","grid view","kpi order","report name","(copy)","ad group","custom group","grouping","gif","download support","asset download","net results"],
    "Intelligence · Comparative Reports": ["comparative report","ad type comparison","comparisonview","custom metric"],
    "Intelligence · All Ads":             ["all ads"],
    "Intelligence · Playbooks":           ["playbook"],
    "Intelligence · Mixpanel Tracking":   ["mixpanel"],
    "Creative Affinity · Data & Assets":  ["creative affinity","deprecated","old asset","thumbnail","ugc","video_cover_url","asset_type","effective_instagram","is_representative_asset","influencer","catalog","dpa","carousel_album","media_type","full refresh","spend data"],
    "Creative Collab":                    ["collab","brief recording","brief conceptname","creative collab"],
    "Client Portal (external)":           ["client portal","shared creative report","shared report","external user","external side"],
    "Integrations (data feeds)":          ["pinterest","attribution","fivetran","integration"],
    "TalentCentral / novaTalent":         ["novatalent","talent review","healthcare novatalent","bulk-add new skill"],
    "Nebula (component library)":         ["nebula","filter component","timepicker","reorderable"],
    "Library / Strategies":               ["library","package strategy","strategy package","blueprint","consulting fee"],
}

# Finer granularity: real nova-web components (verified paths under src/features) → alias keywords.
# When ≥2 tickets touch the same component, that's a file-level regression overlap.
NOVA_COMPONENTS = {
    "ComparisonView":                 ("intelligence/creative-reports/components/ComparisonView", ["comparisonview","comparison view"]),
    "TableView":                      ("intelligence/creative-reports/components/TableView", ["tableview","table view"]),
    "MetricsSelector":                ("creative-reports/components/ComparisonView/MetricsSelector", ["metricsselector","metrics selector","metric selector","add kpi","kpi chip"]),
    "DateChipDropdown":               ("creative-reports/components/AdFilters/DateChipDropdown", ["datechipdropdown","date chip","date range"]),
    "AdGroupDetailDialog":            ("creative-reports/components/AdGroupDetailDialog", ["adgroupdetail","ad group","custom ad group","custom group","ad grouping"]),
    "AIAnalysisButton":               ("creative-reports/components/AIAnalysisButton", ["aianalysisbutton","ai analysis button","ai button"]),
    "NetResultsFooterMetricCell":     ("intelligence/shared/aggregation/NetResultsFooterMetricCell", ["net results","netresults"]),
    "ClientSharedCreativeReportPage": ("intelligence/creative-reports/ClientSharedCreativeReportPage", ["clientsharedcreativereportpage","shared creative report","shared report"]),
    "AllAdsFilters":                  ("intelligence/all-ads/components/AllAdsFilters", ["all ads"]),
    "PlaybookFilters":                ("intelligence/playbook/components/PlaybookFilters", ["playbook"]),
    "Sidebar (ScrollForm)":           ("components/ScrollForm/components/Sidebar", ["sidebar navigation","sidebar nav","intelligence-client selected"]),
}

# Headers we recognize inside a "wrap-up" style comment.
WRAP_HEADERS = ["problem","root cause","background","what changed","what we changed",
                "fix","how to verify","how to test","how to reproduce","steps to reproduce",
                "notes","note","repos / jira","repos","repo","summary","acceptance criteria"]

def norm(s): return (s or "").strip().upper()
def esc(s): return html.escape(s or "")
def parse(ts): return datetime.fromisoformat(ts)
def ufmt(dt): return dt.astimezone(UTC).strftime("%b %-d · %H:%M")

def activity(t):
    acts = []
    for sc in t.get("statusChanges", []):
        acts.append((parse(sc["ts"]), "status", sc.get("author",""), f'{sc.get("from","?")}  →  {sc.get("to","?")}'))
    for c in t.get("comments", []):
        acts.append((parse(c["ts"]), "comment", c.get("author",""), c.get("body","")))
    acts.sort(key=lambda x: x[0])
    return acts

def last_ts(t):
    a = activity(t)
    return a[-1][0] if a else parse("2000-01-01T00:00:00+00:00")

def qa_entered(t):
    entered = None
    for sc in sorted(t.get("statusChanges", []), key=lambda s: parse(s["ts"])):
        if norm(sc.get("to")) == "IN QA":
            entered = parse(sc["ts"])
    return entered

def fmt_dwell(td):
    total_h = int(td.total_seconds() // 3600)
    d, h = divmod(total_h, 24)
    if d >= 1: return f"{d}d {h}h"
    if total_h >= 1: return f"{total_h}h"
    return "<1h"

def qa_color(td):
    days = td.total_seconds() / 86400
    if days >= 3: return "#ff6f61"   # nova error — stuck (>3d)
    if days >= 2: return "#f0a45e"   # nova caution — aging 2–3d
    return "#2fd6a6"                 # nova success — fresh (<2d)

def stage_counts(tks):
    stg = {}
    for t in tks:
        k = norm(t["currentStatus"]); stg[k] = stg.get(k, 0) + 1
    return stg

def risk_of(tks):
    stg = stage_counts(tks)
    spans = len([k for k in stg if k in STATUS_ORDER]) > 1
    return ("HIGH", "#ff6f61") if (spans or len(tks) >= 4) else ("MED", "#f0a45e")

def ticket_tags(t):
    text = (t.get("summary","") + " " + " ".join(c.get("body","") for c in t.get("comments",[]))).lower()
    return {tag for tag, kws in NOVA_MODULES.items() if any(k in text for k in kws)}

# Full component inventory (built from the nova-web src tree) for exact code-identifier matching.
try:
    _ci = json.load(open(os.path.join(HERE, "component_index.json")))
    COMPONENT_INDEX = _ci.get("all", {})
    _matchable = sorted(_ci.get("matchable", {}).keys(), key=len, reverse=True)
    EXACT_RE = re.compile(r'(?<![A-Za-z0-9])(' + "|".join(re.escape(n) for n in _matchable) + r')(?![A-Za-z0-9])') if _matchable else None
except Exception:
    COMPONENT_INDEX, EXACT_RE = {}, None

def ticket_components(t):
    """Return {component: (path, module)} — exact code identifiers (full index) + curated alias phrases."""
    raw = t.get("summary","") + " " + " ".join(c.get("body","") for c in t.get("comments",[]))
    low = raw.lower()
    out = {}
    if EXACT_RE:                                   # precise: literal code identifiers
        for m in set(EXACT_RE.findall(raw)):
            info = COMPONENT_INDEX.get(m, {})
            out[m] = (info.get("path",""), info.get("module",""))
    for comp, (path, kws) in NOVA_COMPONENTS.items():   # recall: human phrases for key components
        if any(k in low for k in kws):
            info = COMPONENT_INDEX.get(comp, {})
            out.setdefault(comp, (path or info.get("path",""), info.get("module","")))
    return out

def parse_wrapup(comments):
    """Extract Problem / Fix / How-to-test from the most complete structured comment."""
    best = None
    for c in comments:
        b = c.get("body","") or ""
        if re.search(r'\bproblem\s*:', b, re.I) and re.search(r'(how to (verify|test)|what (we )?changed|\bfix\b)', b, re.I):
            best = b  # prefer the latest qualifying comment
    if not best:
        return None
    pat = re.compile(r'(' + "|".join(re.escape(h) for h in WRAP_HEADERS) + r')\s*:', re.I)
    matches = list(pat.finditer(best))
    parts = {}
    for i, m in enumerate(matches):
        key = m.group(1).lower()
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(best)
        val = re.sub(r'\s+', ' ', best[start:end]).strip(" .;")
        if val and key not in parts:
            parts[key] = val[:420]
    problem = parts.get("problem") or parts.get("root cause")
    fix = parts.get("what changed") or parts.get("what we changed") or parts.get("fix")
    test = parts.get("how to verify") or parts.get("how to test") or parts.get("how to reproduce") or parts.get("steps to reproduce")
    if not any([problem, fix, test]):
        return None
    return {"problem": problem, "fix": fix, "test": test}

# ── dark-dashboard render helpers ───────────────────────────────────────────
def _short_body(s, n=150):
    s = re.sub(r'\s+', ' ', (s or "")).strip()
    return s if len(s) <= n else s[:n-1].rstrip() + "…"

def _redact_names(text, names):
    """Strip person names from free text before it's rendered on the public page:
    generic Jira @mentions (1-3 capitalized tokens) plus any known display name."""
    if not text:
        return text
    text = re.sub(r"@[A-Z][\w.'’-]+(?:\s+[A-Z][\w.'’-]+){0,2}", "@teammate", text)
    for n in sorted((x for x in names if x), key=len, reverse=True):
        text = text.replace(n, "a teammate")
    return text

def _smooth(pts, baseline):
    """Catmull-Rom → cubic-bezier path. Returns (line_d, area_d)."""
    if not pts:
        return "", ""
    if len(pts) == 1:
        x, y = pts[0]
        return f"M {x:.1f},{y:.1f}", f"M {x:.1f},{y:.1f} L {x:.1f},{baseline} Z"
    d = f"M {pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i-1] if i > 0 else pts[0]
        p1, p2 = pts[i], pts[i+1]
        p3 = pts[i+2] if i + 2 < len(pts) else pts[-1]
        c1x = p1[0] + (p2[0]-p0[0]) / 6; c1y = p1[1] + (p2[1]-p0[1]) / 6
        c2x = p2[0] - (p3[0]-p1[0]) / 6; c2y = p2[1] - (p3[1]-p1[1]) / 6
        d += f" C {c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    area = d + f" L {pts[-1][0]:.1f},{baseline} L {pts[0][0]:.1f},{baseline} Z"
    return d, area

def trend_svg(tickets, now):
    """10-day trend: count of transitions INTO 'IN QA' (entered) vs 'DEPLOYED TO PROD'."""
    days = [(now - timedelta(days=i)).date() for i in range(9, -1, -1)]
    idx = {d: i for i, d in enumerate(days)}
    qa = [0]*10; prod = [0]*10
    for t in tickets:
        for sc in t.get("statusChanges", []):
            try: d = parse(sc["ts"]).astimezone(UTC).date()
            except Exception: continue
            if d not in idx: continue
            to = norm(sc.get("to"))
            if to == "IN QA": qa[idx[d]] += 1
            elif to == "DEPLOYED TO PROD": prod[idx[d]] += 1
    X0, X1, YT, YB = 34, 886, 18, 210
    maxv = max(2, max(qa + prod))
    xs = [X0 + (X1 - X0) * i / 9 for i in range(10)]
    def y(v): return YB - (v / maxv) * (YB - YT)
    qa_pts = list(zip(xs, [y(v) for v in qa]))
    pr_pts = list(zip(xs, [y(v) for v in prod]))
    qa_line, qa_area = _smooth(qa_pts, YB)
    pr_line, pr_area = _smooth(pr_pts, YB)
    o = ['<svg viewBox="0 0 900 240" width="100%" preserveAspectRatio="none" style="display:block">']
    o.append('<defs><linearGradient id="gp" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#2fd6a6" stop-opacity=".28"/><stop offset="1" stop-color="#2fd6a6" stop-opacity="0"/></linearGradient>'
             '<linearGradient id="gq" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#f0a45e" stop-opacity=".22"/><stop offset="1" stop-color="#f0a45e" stop-opacity="0"/></linearGradient></defs>')
    for frac in (0, 1/3, 2/3, 1):
        gy = YB - frac * (YB - YT); lab = round(maxv * frac)
        o.append(f'<line x1="{X0}" y1="{gy:.0f}" x2="{X1}" y2="{gy:.0f}" stroke="#242a38" stroke-width="1"/>')
        o.append(f'<text x="26" y="{gy+3:.0f}" fill="#5f6675" font-size="10" text-anchor="end" font-family="monospace">{lab}</text>')
    o.append(f'<path d="{qa_area}" fill="url(#gq)"/><path d="{qa_line}" fill="none" stroke="#f0a45e" stroke-width="2.5" stroke-linecap="round"/>')
    o.append(f'<path d="{pr_area}" fill="url(#gp)"/><path d="{pr_line}" fill="none" stroke="#2fd6a6" stroke-width="2.5" stroke-linecap="round"/>')
    for i, d in enumerate(days):
        o.append(f'<text x="{xs[i]:.0f}" y="231" fill="#5f6675" font-size="10" text-anchor="middle" font-family="monospace">{d.month}/{d.day}</text>')
    o.append(f'<circle cx="{X1}" cy="{y(prod[-1]):.0f}" r="3.5" fill="#2fd6a6"/><circle cx="{X1}" cy="{y(qa[-1]):.0f}" r="3.5" fill="#f0a45e"/>')
    o.append('</svg>')
    return "".join(o)

CSS = """
    *{box-sizing:border-box;}
    .nx{--bg:#0c0e13;--card:#151822;--card2:#1a1e2a;--line:#242a38;--fg:#e8eaf1;--muted:#8b93a7;--faint:#5f6675;
      --brand:#7c6cff;--qa:#f0a45e;--ready:#8b93ff;--prod:#2fd6a6;--err:#ff6f61;
      --sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;--mono:source-code-pro,ui-monospace,Menlo,monospace;
      background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:14px;line-height:1.5;
      border-radius:18px;overflow:hidden;display:grid;grid-template-columns:216px 1fr 316px;min-height:760px;max-width:1380px;margin:0 auto;}
    .nx a{color:inherit;text-decoration:none;}
    .side{background:#0a0c11;border-right:1px solid var(--line);padding:20px 16px;display:flex;flex-direction:column;gap:6px;}
    .brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:17px;margin:2px 4px 20px;}
    .brand .lg{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,var(--brand),#b3a6ff);display:flex;align-items:center;justify-content:center;font-size:15px;}
    .nav{display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:11px;color:var(--muted);font-weight:600;font-size:13.5px;}
    .nav.on{background:var(--card2);color:var(--fg);}
    .nav .i{width:18px;text-align:center;opacity:.9;}
    .nav .c{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--faint);}
    .side .foot{margin-top:auto;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;text-align:center;}
    .side .foot h4{margin:0 0 4px;font-size:13.5px;}
    .side .foot p{margin:0 0 10px;color:var(--muted);font-size:12px;}
    .badge-live{display:inline-flex;align-items:center;gap:6px;background:rgba(47,214,166,.13);color:var(--prod);font-weight:700;font-size:11px;padding:5px 10px;border-radius:999px;}
    .dot{width:7px;height:7px;border-radius:50%;background:currentColor;display:inline-block;}
    .main{padding:24px 26px;overflow:auto;}
    .hd{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:20px;}
    .hd h1{margin:0 0 4px;font-size:24px;font-weight:800;letter-spacing:-.02em;}
    .hd .sub{color:var(--muted);font-size:13.5px;}.hd .sub b{color:var(--fg);}
    .pill{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 12px;font-size:12.5px;color:var(--muted);font-family:var(--mono);white-space:nowrap;}
    .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px;}
    .stat{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 17px;}
    .stat .top{display:flex;align-items:center;gap:10px;color:var(--muted);font-size:13px;font-weight:600;}
    .stat .ic{width:30px;height:30px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:15px;background:var(--tint);}
    .stat .n{font-size:30px;font-weight:800;letter-spacing:-.02em;margin-top:12px;line-height:1;}
    .stat .d{font-size:12px;margin-left:9px;font-weight:700;}
    .up{color:var(--prod);} .flat{color:var(--faint);}
    .card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin-bottom:18px;}
    .card h3{margin:0;font-size:15px;font-weight:700;}
    .card .hrow{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;}
    .legend{display:flex;gap:14px;font-size:11.5px;color:var(--muted);font-family:var(--mono);}
    .legend i{width:9px;height:9px;border-radius:2px;display:inline-block;margin-right:5px;vertical-align:middle;}
    .rowlist{display:flex;flex-direction:column;gap:9px;}
    .row{display:flex;align-items:center;gap:12px;background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:11px 14px;}
    .row .k{font-family:var(--mono);font-weight:700;font-size:12.5px;color:var(--ready);}
    .row .ti{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--fg);font-size:13px;}
    .row .who{color:var(--faint);font-size:11.5px;white-space:nowrap;}
    .age{font-family:var(--mono);font-weight:700;font-size:11.5px;color:#0c0e13;padding:3px 9px;border-radius:7px;white-space:nowrap;}
    .none{color:var(--faint);font-size:12.5px;padding:4px 2px;}
    .mods{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
    .mod{background:var(--card2);border:1px solid var(--line);border-left:3px solid var(--mc);border-radius:12px;padding:12px 14px;}
    .mod .mtop{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;}
    .mod .rk{font-family:var(--mono);font-size:10px;font-weight:800;padding:2px 7px;border-radius:6px;color:#0c0e13;}
    .mod .nm{font-weight:700;font-size:13px;}
    .mod .nm.mono{font-family:var(--mono);font-size:12px;}
    .mini{display:flex;gap:6px;flex-wrap:wrap;}
    .mp{font-family:var(--mono);font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:999px;}
    details.sec{background:var(--card);border:1px solid var(--line);border-radius:14px;margin-bottom:11px;overflow:hidden;}
    details.sec>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:13px 16px;font-weight:700;font-size:13px;text-transform:uppercase;letter-spacing:.05em;}
    details.sec>summary::-webkit-details-marker{display:none;}
    .chev{color:var(--faint);transition:transform .15s;}details[open]>summary .chev{transform:rotate(90deg);}
    .sec .cnt{margin-left:auto;color:var(--faint);font-family:var(--mono);}
    .tk{border-top:1px solid var(--line);padding:10px 16px;}
    .tk .l1{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
    .tk .kk{font-family:var(--mono);font-weight:700;font-size:12px;color:var(--ready);}
    .tk .tt{color:var(--fg);font-size:13px;}.tk .mt{color:var(--faint);font-size:11.5px;margin-top:3px;}
    .chip{font-size:9.5px;font-weight:800;text-transform:uppercase;letter-spacing:.03em;padding:2px 7px;border-radius:999px;color:#0c0e13;}
    .chip.new{background:var(--prod);}.chip.wrap{background:var(--brand);color:#fff;}
    .cmp{font-family:var(--mono);font-size:10px;color:var(--ready);background:#8b93ff1a;border:1px solid var(--line);padding:1px 6px;border-radius:5px;}
    .right{background:#0a0c11;border-left:1px solid var(--line);padding:22px 18px;overflow:auto;}
    .stcard{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;text-align:center;margin-bottom:20px;}
    .stcard .big{font-size:20px;font-weight:800;letter-spacing:-.01em;}
    .stcard .sm{color:var(--muted);font-size:12px;margin-top:2px;font-family:var(--mono);}
    .stcard .btns{display:flex;gap:8px;justify-content:center;margin-top:13px;}
    .stcard .b{flex:1;background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:8px;font-size:12px;font-weight:600;color:var(--muted);}
    .feedh{font-weight:700;font-size:14px;margin:0 0 14px;}
    .fitem{display:flex;gap:11px;padding:11px 0;border-top:1px solid var(--line);}
    .fitem:first-of-type{border-top:none;}
    .av{width:30px;height:30px;border-radius:50%;flex:none;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:#0c0e13;}
    .fitem .body{min-width:0;}
    .fitem .who{font-weight:700;font-size:12.5px;}
    .fitem .st{font-size:10px;font-weight:800;text-transform:uppercase;padding:1px 7px;border-radius:999px;color:#0c0e13;}
    .fitem .meta{color:var(--faint);font-size:11px;font-family:var(--mono);margin-bottom:3px;}
    .fitem .ftt{font-size:12.5px;color:var(--fg);}
    .fitem .msg{color:var(--muted);font-size:12.5px;background:var(--card2);border:1px solid var(--line);border-radius:9px;padding:7px 9px;margin-top:5px;}
    .fitem .msg.flow{font-family:var(--mono);font-size:11.5px;}
    @media(max-width:1080px){.nx{grid-template-columns:1fr;}.side,.right{border:none;border-top:1px solid var(--line);} .stats{grid-template-columns:1fr;} .mods{grid-template-columns:1fr;}}
"""

def report(tickets, now):
    cutoff = now - WINDOW
    # person names to redact from any free text rendered on the public page
    person_names = set()
    for _t in tickets:
        if _t.get("assignee"): person_names.add(_t["assignee"])
        for _sc in _t.get("statusChanges", []):
            if _sc.get("author"): person_names.add(_sc["author"])
        for _c in _t.get("comments", []):
            if _c.get("author"): person_names.add(_c["author"])
    red = lambda s: _redact_names(s, person_names)
    by_status = {s: [] for s in STATUS_ORDER}
    for t in tickets:
        by_status.setdefault(norm(t["currentStatus"]), []).append(t)
    for s in by_status:
        by_status[s].sort(key=last_ts, reverse=True)
    counts = {s: len(by_status.get(s, [])) for s in STATUS_ORDER}

    # tickets whose newest activity is within the 12h window
    delta = []
    for t in tickets:
        acts = activity(t)
        if acts and acts[-1][0] >= cutoff:
            delta.append((t, acts[-1]))
    delta.sort(key=lambda x: x[1][0], reverse=True)

    # arrivals INTO each status within the window (stat-card deltas)
    arrivals = {s: 0 for s in STATUS_ORDER}
    for t in tickets:
        for s in STATUS_ORDER:
            if any(norm(sc.get("to")) == s and parse(sc["ts"]) >= cutoff for sc in t.get("statusChanges", [])):
                arrivals[s] += 1

    # In-QA aging
    qa = []
    for t in by_status.get("IN QA", []):
        e = qa_entered(t)
        if e is not None:
            qa.append((t, now - e))
    qa.sort(key=lambda x: x[1], reverse=True)

    def span(v): return len(set(norm(x["currentStatus"]) for x in v))

    # module overlap clusters (≥2 tickets share a module)
    tag_map = {}
    for t in tickets:
        for tag in ticket_tags(t):
            tag_map.setdefault(tag, []).append(t)
    clusters = sorted(((k, v) for k, v in tag_map.items() if len(v) >= 2),
                      key=lambda kv: (-span(kv[1]), -len(kv[1]), kv[0]))

    # component (file-level) clusters
    comp_map, comp_path = {}, {}
    for t in tickets:
        for comp, (path, mod) in ticket_components(t).items():
            comp_map.setdefault(comp, []).append(t); comp_path[comp] = path
    comp_clusters = sorted(((c, v) for c, v in comp_map.items() if len(v) >= 2),
                           key=lambda kv: (-span(kv[1]), -len(kv[1]), kv[0]))

    o = ['<style>', CSS, '</style>', '<div class="nx">']

    # ── left rail ────────────────────────────────────────────────────────
    o.append('<aside class="side">')
    o.append('<div class="brand"><span class="lg">🚦</span> NOVA Handoff</div>')
    o.append('<a class="nav on"><span class="i">🏠</span>Overview</a>')
    for s in STATUS_ORDER:
        c, label, ic = STATUS_META[s]
        o.append(f'<a class="nav"><span class="i">{ic}</span>{label}<span class="c">{counts[s]}</span></a>')
    o.append('<a class="nav"><span class="i">🔗</span>Module risk</a>')
    o.append(f'<a class="nav" href="{BOARD_URL}"><span class="i">📋</span>Board</a>')
    o.append('<div class="foot"><div class="badge-live"><span class="dot"></span>Cloud routine live</div>'
             '<h4 style="margin-top:10px">Follow-the-sun</h4>'
             '<p>Auto-posts 07:00 & 19:00 UTC — no machine needed.</p>'
             f'<a class="b" style="display:block;background:var(--brand);color:#fff;border-radius:10px;padding:9px;font-weight:700" href="{BOARD_URL}">Open NOVA board</a></div>')
    o.append('</aside>')

    # ── center column ────────────────────────────────────────────────────
    o.append('<main class="main">')
    o.append(f'<div class="hd"><div><h1>QA → Prod Handoff</h1>'
             f'<div class="sub">{len(tickets)} tickets in pipeline · <b>{len(delta)}</b> changed in the last 12h · all times UTC</div></div>'
             f'<div class="pill">📅 snapshot {ufmt(now)} UTC</div></div>')

    o.append('<div class="stats">')
    for s in STATUS_ORDER:
        c, label, ic = STATUS_META[s]
        a = arrivals[s]
        d = f'<span class="d up">↑ +{a} in 12h</span>' if a else '<span class="d flat">flat</span>'
        o.append(f'<div class="stat"><div class="top"><span class="ic" style="--tint:{c}22;color:{c}">{ic}</span>{label}</div>'
                 f'<div class="n">{counts[s]}{d}</div></div>')
    o.append('</div>')

    # pipeline trend
    o.append('<div class="card"><div class="hrow"><h3>Pipeline flow · last 10 days</h3>'
             '<div class="legend"><span><i style="background:#f0a45e"></i>Entered QA</span>'
             '<span><i style="background:#2fd6a6"></i>Deployed</span></div></div>')
    o.append(trend_svg(tickets, now))
    o.append('</div>')

    # In-QA aging watch
    o.append('<div class="card"><div class="hrow"><h3>⏳ In QA — aging watch</h3>'
             '<span class="cnt" style="color:var(--faint);font-size:12px">longest first</span></div>')
    if qa:
        o.append('<div class="rowlist">')
        for t, td in qa:
            o.append(f'<div class="row"><span class="age" style="background:{qa_color(td)}">{fmt_dwell(td)}</span>'
                     f'<a class="k" href="{BASE_URL}{t["key"]}">{t["key"]}</a>'
                     f'<span class="ti">{esc(red(t["summary"]))}</span></div>')
        o.append('</div>')
    else:
        o.append('<div class="none">Nothing sitting in QA.</div>')
    o.append('</div>')

    # module / component risk
    o.append('<div class="card"><div class="hrow"><h3>🔗 Module risk</h3>'
             '<span class="cnt" style="color:var(--faint);font-size:12px">regress together</span></div>')
    if clusters or comp_clusters:
        o.append('<div class="mods">')
        def mod_card(name, tks, mono=False):
            lbl, col = risk_of(tks); stg = stage_counts(tks)
            pills = "".join(
                f'<span class="mp" style="background:{STATUS_META[s][0]}22;color:{STATUS_META[s][0]}">{stg[s]} {STAGE_SHORT[s]}</span>'
                for s in STATUS_ORDER if stg.get(s))
            nm = f'<span class="nm mono">{esc(name)}</span>' if mono else f'<span class="nm">{esc(name)}</span>'
            return (f'<div class="mod" style="--mc:{col}"><div class="mtop"><span class="rk" style="background:{col}">{lbl}</span>{nm}</div>'
                    f'<div class="mini">{pills}</div></div>')
        for tag, tks in clusters:
            o.append(mod_card(tag, tks))
        for comp, tks in comp_clusters:
            o.append(mod_card(comp, tks, mono=True))
        o.append('</div>')
    else:
        o.append('<div class="none">No modules with 2+ concurrent tickets.</div>')
    o.append('</div>')

    # collapsible pipeline sections
    for s in STATUS_ORDER:
        c, label, ic = STATUS_META[s]
        op = "" if s == "DEPLOYED TO PROD" else " open"
        o.append(f'<details class="sec"{op}><summary style="color:{c}"><span class="chev">▶</span>{ic} {label}<span class="cnt">{counts[s]}</span></summary>')
        rows = by_status.get(s, [])
        if not rows:
            o.append('<div class="tk"><span class="mt" style="color:var(--faint)">None.</span></div>')
        for t in rows:
            prio = t.get("priority", "-") or "-"
            acts = activity(t)
            fresh = bool(acts) and acts[-1][0] >= cutoff
            wrap = parse_wrapup(t.get("comments", []))
            comps = ticket_components(t)
            o.append('<div class="tk"><div class="l1">')
            o.append(f'<a class="kk" href="{BASE_URL}{t["key"]}">{t["key"]}</a>')
            o.append(f'<span class="tt">{esc(red(t["summary"]))}</span>')
            if fresh: o.append('<span class="chip new">updated</span>')
            if wrap: o.append('<span class="chip wrap">wrap-up</span>')
            o.append('</div>')
            o.append(f'<div class="mt">{esc(prio)}')
            if comps:
                o.append(' ' + "".join(f'<span class="cmp">{esc(cn)}</span>' for cn in sorted(comps)))
            o.append('</div></div>')
        o.append('</details>')
    o.append('</main>')

    # ── right rail: since-last-handoff feed ──────────────────────────────
    o.append('<aside class="right">')
    o.append(f'<div class="stcard"><div class="big">Handoff · {now.astimezone(UTC).strftime("%b %-d")}</div>'
             f'<div class="sm">{ufmt(now)} UTC snapshot</div>'
             '<div class="btns"><span class="b">↻ 07:00 UTC</span><span class="b">↻ 19:00 UTC</span></div></div>')
    o.append('<div class="feedh">🔔 Since last handoff</div>')
    if not delta:
        o.append('<div class="none">No status changes or comments in the last 12 hours.</div>')
    else:
        for t, (dt, kind, who, detail) in delta[:10]:
            sc = norm(t["currentStatus"])
            col, label, _ = STATUS_META.get(sc, ("#5f6675", t["currentStatus"].title(), ""))
            o.append('<div class="fitem">')
            o.append(f'<span class="av" style="background:{col}">{"↻" if kind == "status" else "💬"}</span>')
            o.append('<div class="body">')
            o.append(f'<div class="who">{t["key"]} <span class="st" style="background:{col}">{label}</span></div>')
            o.append(f'<div class="meta">{ufmt(dt)} UTC</div>')
            o.append(f'<div class="ftt">{esc(red(_short_body(t["summary"], 90)))}</div>')
            if kind == "status":
                o.append(f'<div class="msg flow">{esc(detail)}</div>')
            else:
                o.append(f'<div class="msg">{esc(red(_short_body(detail)))}</div>')
            o.append('</div></div>')
    o.append('</aside>')

    o.append('</div>')
    return "\n".join(o)

if __name__ == "__main__":
    with open(os.path.join(HERE, "tickets.json")) as f:
        tickets = json.load(f)
    env_now = os.environ.get("HANDOFF_NOW")
    now = parse(env_now).astimezone(UTC) if env_now else datetime.now(UTC)
    html = report(tickets, now)
    # Local/artifact copy
    with open(os.path.join(HERE, "nova_handoff.html"), "w") as f:
        f.write(html)
    # GitHub Pages copy — committed and served at https://a-chan23.github.io/nova-handoff/
    docs_dir = os.path.join(HERE, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    with open(os.path.join(docs_dir, "index.html"), "w") as f:
        f.write(html)
    print(f"Wrote nova_handoff.html + docs/index.html · {len(tickets)} NOVA tickets · now={now.isoformat()}")
