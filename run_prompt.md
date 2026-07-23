Refresh and post the NOVA board "QA → Prod" handoff. Be fully autonomous; do not ask questions.
All file paths below are RELATIVE to this repo's root — run every step from the repo root so it works
locally and in a cloud environment (no absolute machine paths).

CONTEXT
- Jira Cloud cloudId = 102ca926-70a5-403c-b785-a8e617f1041e (tenant powerdigital.atlassian.net)
- Generator: ./gen_nova_handoff.py (reads ./tickets.json and ./component_index.json, writes BOTH
  ./nova_handoff.html and ./docs/index.html; times in UTC; the 12h handoff window is computed automatically)
- Live dashboard (GitHub Pages, refreshes on push, NO approval gate): https://a-chan23.github.io/nova-handoff/
  Pages serves ./docs/index.html from the `main` branch. This is the canonical dashboard URL — post THIS in Slack.
- Slack channel: C0B398LUE12 (#qa-daily-reports)
- NOVA board: https://powerdigital.atlassian.net/jira/software/c/projects/NOVA/boards/338

STEPS
1. Load Jira + Slack tools via ToolSearch (search "jira search issues jql", "jira get issue", "slack send message").
2. searchJiraIssuesUsingJql (cloudId above, searchResultMode "issues", responseContentFormat "markdown"), jql:
   project = NOVA AND status in ("In QA","Ready for Prod","Deployed to Prod") ORDER BY status ASC, updated DESC
   fields ["summary","status","assignee","priority"], maxResults 100. Record every NOVA key + current status.
3. For EACH key: getJiraIssue (same cloudId), fields ["summary","status","assignee","priority","comment"], expand="changelog".
   Extract status-field changelog changes (ts=history created, author, from=fromString, to=toString) and comments
   (ts, author, plain-text body; keep component identifiers like ComparisonView/TableView verbatim).
   INTEGRITY CHECK: confirm the returned key/webUrl matches the requested key — this API sometimes returns a
   different issue; re-fetch directly if mismatched.
4. Overwrite ./tickets.json (JSON array), one object per ticket:
   {"key","summary","currentStatus","assignee","priority","statusChanges":[{"ts","author","from","to"}],"comments":[{"ts","author","body"}]}
5. Run: python3 gen_nova_handoff.py   (from repo root; it writes ./nova_handoff.html AND ./docs/index.html)
6. Publish the refreshed dashboard by committing ./docs/index.html to `main` and pushing — GitHub Pages
   redeploys automatically with NO approval prompt. Do this with the git CLI from the repo root:
     git add docs/index.html
     git commit -m "Refresh NOVA handoff dashboard <UTC timestamp>"   (skip the commit if nothing changed)
     git push origin HEAD:main
   The live page https://a-chan23.github.io/nova-handoff/ updates within ~1 minute. (Do NOT rely on the
   claude.ai Artifact tool here — headless/scheduled runs cannot satisfy its publish-approval gate, which is
   why the dashboard previously went stale.) tickets.json and nova_handoff.html stay git-ignored; only
   docs/index.html is committed.
7. Compute from tickets.json: counts per status, and the handoff delta = tickets whose newest statusChange OR comment
   is within the last 12h of current UTC time.
8. Load the Slack tool (ToolSearch "slack send message") and post to channel C0B398LUE12: counts per status + a
   "Since last handoff (last 12h)" bullet list (KEY → STATUS — summary), the two oldest In-QA tickets (aging watch),
   the top HIGH-risk modules, and the dashboard + board links. If zero changed in 12h, say so. All times UTC.
   LINK FORMATTING (required):
   - The dashboard link MUST be the GitHub Pages URL https://a-chan23.github.io/nova-handoff/ — NEVER a
     claude.ai artifact URL (the artifact is retired).
   - Always write every URL as a bounded Slack markdown link — [label](url) — never a bare URL. Slack auto-links
     a bare URL and greedily swallows any following character into the hyperlink target, producing a broken link.
   - Put NO emoji on the dashboard/board link lines (and never place any emoji, label, or another link
     immediately before or after a URL). Keep each link on its own line with a plain text prefix only, e.g.:
       `Dashboard: [NOVA QA→Prod Handoff](https://a-chan23.github.io/nova-handoff/)`
       `NOVA board: [board 338](<board-url>)`

RULES: only NOVA-* keys, only those 3 statuses. If Jira fails, do NOT post — exit with the error. If Slack fails, report why.
