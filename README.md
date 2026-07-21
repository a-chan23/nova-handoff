# NOVA QA→Prod Handoff — automation

Auto-generates the NOVA board QA→Prod handoff dashboard from Jira and posts it to Slack
`#qa-daily-reports`, twice daily (07:00 & 19:00 UTC), as an async cross-timezone handoff.

## Files (source — committed)
- `gen_nova_handoff.py` — builds `nova_handoff.html` from `tickets.json` + `component_index.json`
- `component_index.json` — nova-web component/module index (for regression-overlap flagging)
- `run_prompt.md` — the self-contained instructions the agent runs each cycle (repo-relative paths)

## Generated each run (git-ignored)
`tickets.json`, `nova_handoff.html`, `*.log`

## Run it
- **On demand (local):** `/nova-handoff` in Claude Code, or `claude -p "$(cat run_prompt.md)" --dangerously-skip-permissions`
- **Machine-independent (cloud):** Claude Code on the web → **Routine** (see below). Nothing local needs to be awake.

## Cloud Routine setup (claude.ai/code) — machine-independent
1. Push this folder to a Git repo (GitHub or Bitbucket).
2. Sign in at **claude.ai/code** and **connect that repo** (this creates the cloud environment).
3. Create a **Routine**:
   - Schedule: `0 7,19 * * *` UTC (07:00 & 19:00 UTC) — or your two shift start-of-day times.
   - Prompt: "Read `run_prompt.md` in this repo and execute it exactly and autonomously."
4. Click **Run now** once to confirm the cloud env can reach the Jira + Slack connectors and publish the artifact.

## Requirements for the cloud run
- Jira (Atlassian) and Slack connectors enabled for the claude.ai account/workspace the Routine runs under.
- Permission to update artifact `8c72efff-a113-470e-a376-92e482d0552a` and post to Slack channel `C0B398LUE12`.

## Refreshing the component index (when nova-web changes)
Re-run the index builder against a fresh nova-web checkout and commit the updated `component_index.json`.
