#!/usr/bin/env python3
"""NOVA board — 12-hour QA->Prod handoff report generator. UTC-only times.

Reads tickets.json (list of ticket objects) from this directory, writes nova_handoff.html.
Ticket object:
  {"key","summary","currentStatus","assignee","priority",
   "statusChanges":[{"ts","author","from","to"}], "comments":[{"ts","author","body"}]}
Reference "now" for the 12h window + QA-age = env HANDOFF_NOW (ISO) else system now (UTC).

Views: changes-since-last-handoff; IN QA aging watch; module-overlap (regress-together)
watch; full pipeline in collapsible sections with collapsible per-ticket activity logs that
surface parsed Problem / Fix / How-to-test wrap-ups.
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
    "IN QA":            ("#e78c49", "In QA"),
    "READY FOR PROD":   ("#4a1fff", "Ready for Prod"),
    "DEPLOYED TO PROD": ("#007769", "Deployed to Prod"),
}
PRIO_COLOR = {"Critical":"#d63122","Highest":"#e78c49","High":"#e78c49",
              "Medium":"#767676","Low":"#b9bcb7","-":"#b9bcb7"}
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
    if days >= 3: return "#d63122"   # nova error — stuck (>3d)
    if days >= 2: return "#e78c49"   # nova caution — aging 2–3d
    return "#54ba73"                 # nova success — fresh (<2d)

def stage_counts(tks):
    stg = {}
    for t in tks:
        k = norm(t["currentStatus"]); stg[k] = stg.get(k, 0) + 1
    return stg

def dist_pills(stg):
    return "".join(f'<span class="mini" style="--sc:{STATUS_META[s][0]}">{stg[s]} {STAGE_SHORT[s]}</span>'
                   for s in STATUS_ORDER if stg.get(s))

def risk_of(tks):
    stg = stage_counts(tks)
    spans = len([k for k in stg if k in STATUS_ORDER]) > 1
    return ("HIGH", "#d63122") if (spans or len(tks) >= 4) else ("MED", "#e78c49")

def stage_columns(tks):
    """Render the cluster's tickets into three stage columns (QA · Ready · Prod)."""
    groups = {s: [] for s in STATUS_ORDER}
    for t in tks:
        groups.get(norm(t["currentStatus"]), groups[STATUS_ORDER[0]])
        k = norm(t["currentStatus"])
        (groups[k] if k in groups else groups.setdefault("OTHER", [])).append(t)
    cols = []
    for s in STATUS_ORDER:
        sc = STATUS_META[s][0]
        chips = "".join(f'<a class="scol-key" href="{BASE_URL}{t["key"]}">{t["key"]}</a>'
                        for t in sorted(groups[s], key=lambda x: x["key"]))
        body = chips if chips else '<span class="scol-none">—</span>'
        cols.append(f'<div class="stage-col" style="--sc:{sc}"><div class="stage-h">{STAGE_SHORT[s]} · {len(groups[s])}</div>'
                    f'<div class="scol-keys">{body}</div></div>')
    return '<div class="stages">' + "".join(cols) + '</div>'

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

def report(tickets, now):
    cutoff = now - WINDOW
    by_status = {s: [] for s in STATUS_ORDER}
    for t in tickets:
        by_status.setdefault(norm(t["currentStatus"]), []).append(t)
    for s in by_status:
        by_status[s].sort(key=last_ts, reverse=True)
    counts = {s: len(by_status.get(s, [])) for s in STATUS_ORDER}

    delta = []
    for t in tickets:
        recent = [a for a in activity(t) if a[0] >= cutoff]
        if recent:
            delta.append((t, recent))
    delta.sort(key=lambda x: x[1][-1][0], reverse=True)

    qa = []
    for t in by_status.get("IN QA", []):
        e = qa_entered(t)
        if e is not None:
            qa.append((t, now - e))
    qa.sort(key=lambda x: x[1], reverse=True)

    # module overlap clusters (≥2 tickets share a module)
    tag_map = {}
    for t in tickets:
        for tag in ticket_tags(t):
            tag_map.setdefault(tag, []).append(t)
    clusters = {k: v for k, v in tag_map.items() if len(v) >= 2}
    def span(v): return len(set(norm(x["currentStatus"]) for x in v))
    clusters = sorted(clusters.items(), key=lambda kv: (-span(kv[1]), -len(kv[1]), kv[0]))

    # finer: component (file-level) clusters
    comp_map, comp_path, comp_mod = {}, {}, {}
    for t in tickets:
        for comp, (path, mod) in ticket_components(t).items():
            comp_map.setdefault(comp, []).append(t); comp_path[comp] = path; comp_mod[comp] = mod
    comp_clusters = sorted(((c, v) for c, v in comp_map.items() if len(v) >= 2),
                           key=lambda kv: (-span(kv[1]), -len(kv[1]), kv[0]))

    o = ['<style>', '''
    :root{--bg:#f4f7fc;--fg:#262626;--muted:#6b6b6b;--faint:#767676;--line:#e3e8f1;
      --card:#fff;--panel:#eff6fa;--link:#4a1fff;--brand:#4a1fff;--hi:#eae7f7;--hiline:#d7cff1;
      --shadow:0 1px 3px rgba(38,38,38,.07),0 1px 2px rgba(38,38,38,.04);
      --mono:source-code-pro,ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
      --sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
    *{box-sizing:border-box;}
    .wrap{max-width:880px;margin:0 auto;padding:14px 14px 48px;background:var(--bg);font-family:var(--sans);font-size:15px;line-height:1.5;color:var(--fg);}
    .eyebrow{font-family:var(--mono);font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--link);font-weight:600;}
    .h1{font-size:25px;font-weight:700;letter-spacing:-0.02em;margin:3px 0 5px;text-wrap:balance;}
    .sub{color:var(--muted);margin:0 0 18px;font-size:13.5px;}.sub b{color:var(--fg);}
    .stats{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 24px;}
    .stat{flex:1 1 120px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 14px;position:relative;overflow:hidden;box-shadow:var(--shadow);}
    .stat::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--sc);}
    .stat .n{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1;}
    .stat .l{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em;margin-top:5px;}

    .block-h{display:flex;align-items:baseline;gap:9px;margin:0 0 10px;flex-wrap:wrap;}
    .block-h h2{font-size:17px;font-weight:700;margin:0;letter-spacing:-.01em;}
    .block-h .meta{color:var(--faint);font-family:var(--mono);font-size:12px;}

    .hero{background:var(--hi);border:1px solid var(--hiline);border-radius:14px;padding:18px 20px;margin:0 0 22px;box-shadow:var(--shadow);}
    .hero h2{font-size:18px;}
    .d-item{padding:11px 0;border-top:1px solid var(--hiline);}.d-item:first-of-type{border-top:none;}
    .d-head{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;}
    .d-head a{font-family:var(--mono);font-weight:600;font-size:13px;color:var(--link);text-decoration:none;}
    .d-head .st{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;padding:1px 8px;border-radius:999px;color:#fff;background:var(--sc);}
    .d-head .ti{color:var(--fg);font-size:13.5px;}
    .d-log{margin:6px 0 0;padding:0;list-style:none;font-size:12.5px;}
    .d-log li{display:flex;gap:9px;padding:2px 0;color:#3a4048;}
    .d-log .tm{font-family:var(--mono);font-size:11.5px;color:var(--faint);white-space:nowrap;min-width:80px;}
    .d-log .fl{font-family:var(--mono);color:var(--fg);}.d-log .fl b{color:var(--sc);}
    .d-none{color:var(--muted);font-size:13.5px;}

    .panel{border:1px solid var(--line);border-radius:14px;padding:16px 18px 10px;margin:0 0 22px;background:var(--card);box-shadow:var(--shadow);}
    .qa-row{display:flex;align-items:center;gap:10px;padding:9px 0;border-top:1px solid var(--line);}
    .qa-row:first-of-type{border-top:none;}
    .qa-age{font-family:var(--mono);font-weight:700;font-size:12.5px;color:#fff;padding:3px 9px;border-radius:7px;white-space:nowrap;min-width:66px;text-align:center;background:var(--ac);}
    .qa-key{font-family:var(--mono);font-weight:600;font-size:12.5px;color:var(--link);text-decoration:none;white-space:nowrap;}
    .qa-ti{color:var(--fg);font-size:13px;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
    .qa-who{color:var(--faint);font-size:12px;white-space:nowrap;}
    .legend{color:var(--faint);font-size:11.5px;margin:8px 0 4px;font-family:var(--mono);}

    /* module & component risk cards (collapsible) */
    details.riskcard{border:1px solid var(--line);border-left:5px solid var(--rc);border-radius:10px;margin:9px 0;background:#fff;overflow:hidden;box-shadow:var(--shadow);}
    details.riskcard>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:9px;flex-wrap:wrap;padding:11px 13px;}
    details.riskcard>summary::-webkit-details-marker{display:none;}
    details.riskcard[open]>summary{border-bottom:1px solid var(--line);}
    .riskcard .chev{color:var(--faint);font-size:11px;transition:transform .15s ease;}
    details.riskcard[open]>summary .chev{transform:rotate(90deg);}
    .riskcard .lvl{font-family:var(--mono);font-size:10px;font-weight:700;color:#fff;background:var(--rc);padding:2px 8px;border-radius:6px;letter-spacing:.04em;}
    .riskcard .nm{font-weight:700;font-size:14px;}
    .riskcard .nm.mono{font-family:var(--mono);font-size:13px;}
    .riskcard .ct{font-size:11px;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-variant-numeric:tabular-nums;}
    .riskcard .dist{margin-left:auto;display:flex;gap:5px;flex-wrap:wrap;}
    .mini{font-family:var(--mono);font-size:10px;font-weight:700;color:#fff;background:var(--sc);padding:2px 7px;border-radius:999px;white-space:nowrap;}
    .rc-body{padding:11px 13px 12px;}
    .rc-path{font-family:var(--mono);font-size:10.5px;color:var(--faint);margin:0 0 2px;word-break:break-all;}
    .stages{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px;}
    .stage-col{background:var(--panel);border:1px solid var(--line);border-top:3px solid var(--sc);border-radius:8px;padding:7px 9px 8px;}
    .stage-h{font-family:var(--mono);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--sc);margin-bottom:6px;}
    .scol-keys{display:flex;flex-direction:column;gap:4px;}
    .scol-key{font-family:var(--mono);font-size:11.5px;color:var(--link);text-decoration:none;font-weight:600;}
    .scol-key:hover{text-decoration:underline;}
    .scol-none{color:var(--faint);font-size:12px;}
    @media(max-width:560px){.stages{grid-template-columns:1fr;}}

    details.sec{margin:0 0 12px;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--card);box-shadow:var(--shadow);}
    details.sec>summary{list-style:none;cursor:pointer;padding:12px 16px;display:flex;align-items:center;gap:10px;font-weight:700;
      font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--sc);background:var(--panel);}
    details.sec>summary::-webkit-details-marker{display:none;}
    .sec .dot{width:9px;height:9px;border-radius:50%;background:var(--sc);}
    .sec .cnt{margin-left:auto;color:var(--faint);font-size:12px;font-weight:600;letter-spacing:0;}
    .chev{transition:transform .15s ease;color:var(--faint);font-size:12px;}
    details[open]>summary .chev{transform:rotate(90deg);}
    .sec-body{padding:6px 10px 10px;}

    details.tk{border:1px solid var(--line);border-left:4px solid var(--sc);border-radius:9px;margin:8px 4px;overflow:hidden;background:var(--card);}
    details.tk[open]{box-shadow:0 1px 4px rgba(20,26,40,.05);}
    details.tk>summary{list-style:none;cursor:pointer;padding:10px 13px;}
    details.tk>summary::-webkit-details-marker{display:none;}
    .tk-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
    .tk-key{font-family:var(--mono);font-weight:600;font-size:12.5px;color:var(--link);text-decoration:none;}
    .chip{font-size:10px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;padding:2px 7px;border-radius:999px;color:#fff;background:var(--pc);}
    .agechip{font-family:var(--mono);font-size:10.5px;font-weight:700;color:#fff;background:var(--ac);padding:2px 7px;border-radius:999px;}
    .wrapchip{font-size:10px;font-weight:700;color:var(--link);background:var(--hi);border:1px solid var(--hiline);padding:1px 7px;border-radius:999px;}
    .newtag{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--link);background:var(--hi);border:1px solid var(--hiline);padding:1px 7px;border-radius:999px;}
    .tk-last{margin-left:auto;color:var(--faint);font-size:11px;font-family:var(--mono);white-space:nowrap;}
    .tk-title{font-weight:600;font-size:14px;margin:6px 0 0;text-wrap:balance;}
    .tk-meta{color:var(--muted);font-size:12px;margin-top:2px;}
    .tk-tags{margin-top:5px;display:flex;gap:5px;flex-wrap:wrap;}
    .tk-tag{font-size:10px;color:var(--muted);background:var(--panel);border:1px solid var(--line);padding:1px 6px;border-radius:5px;}
    .cmp-tag{font-family:var(--mono);font-size:10px;color:var(--link);background:var(--hi);border:1px solid var(--hiline);padding:1px 6px;border-radius:5px;}
    .ov-name .cmp{font-family:var(--mono);font-size:12.5px;font-weight:700;}
    .ov-name .path{font-family:var(--mono);font-size:10.5px;color:var(--faint);font-weight:400;}

    .wrapup{margin:10px 13px 2px;background:#f7f9fc;border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:12.5px;}
    .wrapup .row{display:flex;gap:8px;padding:3px 0;}
    .wrapup .lab{flex:0 0 74px;font-weight:700;font-size:10px;text-transform:uppercase;letter-spacing:.04em;padding-top:2px;}
    .wrapup .lab.p{color:#d63122;}.wrapup .lab.f{color:#007769;}.wrapup .lab.t{color:#4a1fff;}
    .wrapup .val{color:#2a3138;}

    .scroll{overflow-x:auto;border-top:1px solid var(--line);margin-top:10px;}
    table{border-collapse:collapse;width:100%;font-size:12.5px;min-width:460px;}
    th,td{text-align:left;padding:6px 11px;border-top:1px solid var(--line);vertical-align:top;}
    thead th{background:var(--panel);color:var(--muted);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;border-top:none;white-space:nowrap;}
    td.t{white-space:nowrap;font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:11.5px;color:#3a424c;}
    tr.win td{background:#f6f4fe;}
    .k-status{font-weight:700;font-size:10.5px;color:var(--sc-row);white-space:nowrap;}
    .k-comment{font-weight:700;font-size:10.5px;color:var(--muted);white-space:nowrap;}
    .who{white-space:nowrap;color:#3a424c;font-size:12px;}
    .flow{font-family:var(--mono);font-size:11.5px;white-space:nowrap;}.flow b{color:var(--sc-row);}
    .body{color:#2a3138;}
    .none{color:var(--faint);font-style:italic;padding:9px 13px;font-size:12.5px;}
    .foot{color:var(--faint);font-size:11.5px;margin-top:30px;border-top:1px solid var(--line);padding-top:13px;line-height:1.6;}
    a.board{color:var(--link);text-decoration:none;font-weight:600;}
    @media(max-width:640px){.h1{font-size:20px;}.stat .n{font-size:22px;}.qa-ti{white-space:normal;}.wrapup .lab{flex-basis:60px;}}
    ''', '</style>', '<div class="wrap">']

    o.append('<div class="eyebrow">NOVA Board · 12-Hour Handoff</div>')
    o.append('<div class="h1">QA → Prod Handoff</div>')
    o.append(f'<p class="sub">Snapshot <b>{ufmt(now)} UTC</b> · <b>NOVA</b> · {len(tickets)} in pipeline · all times UTC · '
             f'<a class="board" href="{BOARD_URL}">NOVA board ↗</a></p>')

    o.append('<div class="stats">')
    for s in STATUS_ORDER:
        c, label = STATUS_META[s]
        o.append(f'<div class="stat" style="--sc:{c}"><div class="n">{counts[s]}</div><div class="l">{label}</div></div>')
    o.append('</div>')

    # ---- HERO ----
    o.append('<div class="hero">')
    o.append(f'<div class="block-h"><h2>🔔 Since last handoff</h2><span class="meta">last 12h · {ufmt(cutoff)} → {ufmt(now)}</span></div>')
    if not delta:
        o.append('<p class="d-none">No status changes or comments on NOVA pipeline tickets in the last 12 hours.</p>')
    else:
        for t, recent in delta:
            c, label = STATUS_META.get(norm(t["currentStatus"]), ("#5b6675", t["currentStatus"].title()))
            o.append(f'<div class="d-item" style="--sc:{c}"><div class="d-head">'
                     f'<a href="{BASE_URL}{t["key"]}">{t["key"]}</a><span class="st">{label}</span>'
                     f'<span class="ti">{esc(t["summary"])}</span></div><ul class="d-log">')
            for dt, kind, who, detail in recent:
                if kind == "status":
                    o.append(f'<li><span class="tm">{ufmt(dt)}</span><span class="fl"><b>{esc(detail)}</b></span></li>')
                else:
                    o.append(f'<li><span class="tm">{ufmt(dt)}</span><span class="cm">💬 {esc(who)}: {esc(detail)}</span></li>')
            o.append('</ul></div>')
    o.append('</div>')

    # ---- IN QA aging ----
    if qa:
        o.append('<div class="panel">')
        o.append('<div class="block-h"><h2>⏳ In QA — aging watch</h2><span class="meta">longest-waiting first</span></div>')
        for t, td in qa:
            ac = qa_color(td)
            o.append(f'<div class="qa-row">'
                     f'<span class="qa-age" style="--ac:{ac}">{fmt_dwell(td)}</span>'
                     f'<a class="qa-key" href="{BASE_URL}{t["key"]}">{t["key"]}</a>'
                     f'<span class="qa-ti">{esc(t["summary"])}</span>'
                     f'<span class="qa-who">{esc(t.get("assignee","—"))}</span></div>')
        o.append('<p class="legend">age = time since entering IN QA · green &lt;2d · orange 2–3d (flagged) · red ≥3d</p>')
        o.append('</div>')

    # ---- Module overlap ----
    if clusters:
        o.append('<div class="panel">')
        o.append('<div class="block-h"><h2>🔗 Module risk</h2><span class="meta">nova areas with active changes — regress together</span></div>')
        for tag, tks in clusters:
            risk_lbl, risk_col = risk_of(tks)
            op = " open" if risk_lbl == "HIGH" else ""
            o.append(f'<details class="riskcard"{op} style="--rc:{risk_col}"><summary>'
                     f'<span class="chev">▶</span>'
                     f'<span class="lvl">{risk_lbl}</span>'
                     f'<span class="nm">{esc(tag)}</span>'
                     f'<span class="ct">{len(tks)}</span>'
                     f'<span class="dist">{dist_pills(stage_counts(tks))}</span></summary>'
                     f'<div class="rc-body">{stage_columns(tks)}</div></details>')
        o.append('<p class="legend">HIGH = changes across multiple stages, or 4+ concurrent tickets · '
                 'columns are the pipeline stage each ticket sits in: <b style="color:#e78c49">QA</b> · '
                 '<b style="color:#4a1fff">Ready</b> · <b style="color:#007769">Prod</b></p>')
        o.append('</div>')

    # ---- Component (file-level) overlap ----
    if comp_clusters:
        o.append('<div class="panel">')
        o.append('<div class="block-h"><h2>🧩 Shared components</h2><span class="meta">same nova-web file touched by multiple tickets — highest-confidence regression</span></div>')
        for comp, tks in comp_clusters:
            risk_lbl, risk_col = risk_of(tks)
            op = " open" if risk_lbl == "HIGH" else ""
            o.append(f'<details class="riskcard"{op} style="--rc:{risk_col}"><summary>'
                     f'<span class="chev">▶</span>'
                     f'<span class="lvl">{risk_lbl}</span>'
                     f'<span class="nm mono">{esc(comp)}</span>'
                     f'<span class="ct">{len(tks)}</span>'
                     f'<span class="dist">{dist_pills(stage_counts(tks))}</span></summary>'
                     f'<div class="rc-body"><div class="rc-path">{esc(comp_path.get(comp,""))}</div>'
                     f'{stage_columns(tks)}</div></details>')
        o.append('<p class="legend">these tickets edit the same file — QA them together before release · paths are under nova-web <code>src/</code></p>')
        o.append('</div>')

    # ---- Pipeline (collapsible) ----
    o.append('<div class="block-h" style="margin-top:8px"><h2>Full pipeline</h2><span class="meta">tap a section, then a ticket, to expand</span></div>')
    for s in STATUS_ORDER:
        c, label = STATUS_META[s]
        sec_open = " open" if s != "DEPLOYED TO PROD" else ""
        o.append(f'<details class="sec"{sec_open} style="--sc:{c}">')
        o.append(f'<summary><span class="chev">▶</span><span class="dot"></span>{label}<span class="cnt">{counts[s]}</span></summary>')
        o.append('<div class="sec-body">')
        for t in by_status.get(s, []):
            prio = t.get("priority","-") or "-"
            acts = activity(t)
            lt = acts[-1][0] if acts else None
            fresh = lt is not None and lt >= cutoff
            wrap = parse_wrapup(t.get("comments", []))
            tags = sorted(ticket_tags(t))
            tk_open = " open" if fresh else ""
            o.append(f'<details class="tk"{tk_open} style="--sc:{c};--sc-row:{c}"><summary><div class="tk-top">')
            o.append(f'<a class="tk-key" href="{BASE_URL}{t["key"]}">{t["key"]}</a>')
            o.append(f'<span class="chip" style="--pc:{PRIO_COLOR.get(prio,"#8a93a0")}">{prio}</span>')
            if s == "IN QA":
                e = qa_entered(t)
                if e is not None:
                    td = now - e
                    o.append(f'<span class="agechip" style="--ac:{qa_color(td)}">⏳ {fmt_dwell(td)} in QA</span>')
            if wrap: o.append('<span class="wrapchip">📋 wrap-up</span>')
            if fresh: o.append('<span class="newtag">● updated</span>')
            o.append(f'<span class="tk-last">last {ufmt(lt) if lt else "—"}</span>')
            o.append('</div>')
            o.append(f'<div class="tk-title">{esc(t["summary"])}</div>')
            o.append(f'<div class="tk-meta">{esc(t.get("assignee","—"))}</div>')
            comps = ticket_components(t)
            if tags or comps:
                o.append('<div class="tk-tags">')
                o.append("".join(f'<span class="tk-tag">{esc(x)}</span>' for x in tags))
                o.append("".join(f'<span class="cmp-tag" title="{esc(p)}">🧩 {esc(c)}</span>' for c, (p, m) in sorted(comps.items())))
                o.append('</div>')
            o.append('</summary>')
            if wrap:
                o.append('<div class="wrapup">')
                if wrap["problem"]: o.append(f'<div class="row"><span class="lab p">Problem</span><span class="val">{esc(wrap["problem"])}</span></div>')
                if wrap["fix"]:     o.append(f'<div class="row"><span class="lab f">Fix</span><span class="val">{esc(wrap["fix"])}</span></div>')
                if wrap["test"]:    o.append(f'<div class="row"><span class="lab t">How to test</span><span class="val">{esc(wrap["test"])}</span></div>')
                o.append('</div>')
            if not acts:
                o.append('<div class="none">No status changes or comments recorded.</div>')
            else:
                o.append('<div class="scroll"><table><thead><tr><th>UTC time</th><th>Kind</th><th>Who</th><th>Activity</th></tr></thead><tbody>')
                for dt, kind, who, detail in acts:
                    win = ' class="win"' if dt >= cutoff else ''
                    if kind == "status":
                        typ='<span class="k-status">● STATUS</span>'; det=f'<span class="flow"><b>{esc(detail)}</b></span>'
                    else:
                        typ='<span class="k-comment">○ comment</span>'; det=f'<span class="body">{esc(detail)}</span>'
                    o.append(f'<tr{win}><td class="t">{ufmt(dt)}</td><td>{typ}</td><td class="who">{esc(who)}</td><td>{det}</td></tr>')
                o.append('</tbody></table></div>')
            o.append('</details>')
        o.append('</div></details>')

    o.append('<div class="foot">NOVA board only · rebuilt every 12h (07:00 & 19:00 UTC). '
             'Priority views: changes-since-last-handoff, In-QA aging, and module-overlap (regress-together). '
             'Ticket wrap-ups (Problem / Fix / How to test) are parsed from dev comments. QA age = time since a ticket last entered IN QA. Times UTC.</div>')
    o.append('</div>')
    return "\n".join(o)

if __name__ == "__main__":
    with open(os.path.join(HERE, "tickets.json")) as f:
        tickets = json.load(f)
    env_now = os.environ.get("HANDOFF_NOW")
    now = parse(env_now).astimezone(UTC) if env_now else datetime.now(UTC)
    with open(os.path.join(HERE, "nova_handoff.html"), "w") as f:
        f.write(report(tickets, now))
    print(f"Wrote nova_handoff.html · {len(tickets)} NOVA tickets · now={now.isoformat()}")
