Refresh and post the NOVA board "QA → Prod" handoff. Be fully autonomous; do not ask questions.
All file paths below are RELATIVE to this repo's root — run every step from the repo root so it works
locally and in a cloud environment (no absolute machine paths).

CONTEXT
- Jira Cloud cloudId = 102ca926-70a5-403c-b785-a8e617f1041e (tenant powerdigital.atlassian.net)
- Generator: ./gen_nova_handoff.py (reads ./tickets.json and ./component_index.json, writes ./nova_handoff.html;
  times in UTC; the 12h handoff window is computed from the current time automatically)
- Artifact to update IN PLACE: https://claude.ai/code/artifact/8c72efff-a113-470e-a376-92e482d0552a
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
5. Run: python3 gen_nova_handoff.py   (from repo root; it writes ./nova_handoff.html)
6. Republish ./nova_handoff.html to the SAME artifact (Artifact tool: url=https://claude.ai/code/artifact/8c72efff-a113-470e-a376-92e482d0552a,
   favicon 🚦; retry with force=true on 409).
7. Compute from tickets.json: counts per status, and the handoff delta = tickets whose newest statusChange OR comment
   is within the last 12h of current UTC time.
8. Load the Slack tool (ToolSearch "slack send message") and post to channel C0B398LUE12: counts per status + a
   "Since last handoff (last 12h)" bullet list (KEY → STATUS — summary), the two oldest In-QA tickets (aging watch),
   the top HIGH-risk modules, and the dashboard + board links. If zero changed in 12h, say so. All times UTC.
   LINK FORMATTING (required): always write every URL as a bounded Slack markdown link — [label](url) — never a
   bare URL. Slack auto-links a bare URL and greedily swallows any following character (including an emoji or the
   newline+emoji on the next line) into the hyperlink target, producing a broken link. So: no bare URLs, and never
   place an emoji, label, or another link immediately before/after a bare URL. Put the dashboard and board links on
   their own lines as e.g. `📊 Dashboard: [NOVA QA→Prod Handoff](<dashboard-url>)` and
   `📋 NOVA board: [board 338](<board-url>)` — the emoji sits outside the [ ](  ) so it can never be absorbed.

RULES: only NOVA-* keys, only those 3 statuses. If Jira fails, do NOT post — exit with the error. If Slack fails, report why.
