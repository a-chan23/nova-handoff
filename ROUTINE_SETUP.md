# NOVA QA→Prod Handoff — Cloud Routine Setup (pending IT/innovation)

**Goal:** Post the NOVA board QA→Prod handoff to Slack **#qa-daily-reports** twice daily at
**01:00 & 16:00 UTC** — 09:00 Taipei and 09:00 Pacific (PDT), the two shift handoffs — running in the
cloud so it does **not** depend on anyone's laptop being awake.

## What IT / the innovation team needs to provision
A Claude Code **cloud environment** (`environment_id`, looks like `env_…`) **or** a
**self-hosted runner pool** (`self_hosted_runner_pool_id`) on the account, with:
- The **Atlassian (Jira) MCP connector** enabled — Jira Cloud tenant `powerdigital.atlassian.net`
  (cloudId `102ca926-70a5-403c-b785-a8e617f1041e`), read access to project **NOVA**.
- The **Slack MCP connector** enabled — permission to post to channel `C0B398LUE12`
  (#qa-daily-reports).

> Both connectors must be available to **headless/scheduled** runs in that environment, not just
> interactive sessions. That is the piece that blocks a pure-cloud schedule today.

**Hand back:** the `environment_id` (or `self_hosted_runner_pool_id`). Then attaching the routine
below takes ~1 minute.

## Schedule
- cron: `0 1,16 * * *`, timezone `UTC`  → 01:00 (09:00 Taipei) and 16:00 (09:00 Pacific/PDT) UTC daily.

## Routine payload (RemoteTrigger `create`) — fill in the id
```json
{
  "name": "NOVA QA→Prod Handoff (2x daily)",
  "job_config": {
    "cron": "0 1,16 * * *",
    "timezone": "UTC",
    "ccr": { "environment_id": "<ENV_ID_FROM_IT>" }
  },
  "session_request": { "...": "see prompt below (field name TBD from schema)" }
}
```

## Routine instructions (what runs each fire)
1. Load Jira + Slack MCP tools (ToolSearch by name, fallback by keyword).
2. `searchJiraIssuesUsingJql` (cloudId above): `project = NOVA AND status in ("In QA","Ready for Prod","Deployed to Prod") ORDER BY status ASC, updated DESC`, fields summary/status/assignee.
3. Per ticket: `getJiraIssue` with `expand=changelog` + comments; keep only status-field changes + comments. **Integrity check:** confirm returned key/webUrl matches the requested key (this API occasionally returns a different issue); re-fetch if mismatched.
4. Compute counts per status + the **12h delta** (tickets whose newest status change or comment is within the last 12h of run time).
5. Publish the refreshed dashboard by committing `docs/index.html` to `main` (GitHub Pages redeploys it
   automatically — no approval gate), then post the handoff summary to Slack `C0B398LUE12` with links to the
   dashboard (`https://a-chan23.github.io/nova-handoff/`) and the NOVA board
   (`https://powerdigital.atlassian.net/jira/software/c/projects/NOVA/boards/338`). Write links as bounded
   markdown `[label](url)` with NO emoji on the link lines; never post a claude.ai artifact URL.
   Only NOVA-* keys, only the 3 pipeline statuses, all times UTC. If Jira fails, do not post — report the error.

## Status of other schedulers (cleanup)
- Local `scheduled-tasks` task `nova-qa-prod-handoff`: **disabled** (won't run). Machine-dependent, so not used.
- No `CronCreate` jobs active.

## Manual fallback (anytime, until the routine is live)
Ask Claude: "refresh the NOVA handoff and post it to #qa-daily-reports" — it pulls live Jira,
rebuilds `docs/index.html` via `gen_nova_handoff.py`, commits/pushes it (GitHub Pages redeploys), and posts to Slack.
