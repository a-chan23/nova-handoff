# NOVA QA→Prod Handoff — automation

Auto-generates the NOVA board QA→Prod handoff dashboard from Jira and posts it to Slack
`#qa-daily-reports`, twice daily, as an async cross-timezone handoff.

**Live dashboard:** https://a-chan23.github.io/nova-handoff/ (GitHub Pages, served from `docs/index.html`
on `main`; redeploys automatically on every push — no publish-approval gate).

## Files (source — committed)
- `gen_nova_handoff.py` — builds `nova_handoff.html` + `docs/index.html` from `tickets.json` + `component_index.json`
- `component_index.json` — nova-web component/module index (for regression-overlap flagging)
- `run_prompt.md` — the self-contained instructions the agent runs each cycle (repo-relative paths)
- `docs/index.html` — the published dashboard served by GitHub Pages (committed; refreshed each run)

## Generated each run
- `docs/index.html` — committed & pushed so Pages redeploys (this is what the routine publishes)
- git-ignored: `tickets.json`, `nova_handoff.html`, `*.log`

## Run it
- **On demand (local):** `/nova-handoff` in Claude Code, or `claude -p "$(cat run_prompt.md)" --dangerously-skip-permissions`
- **Machine-independent (cloud):** Claude Code on the web → **Routine** (see below). Nothing local needs to be awake.

## Cloud Routine setup (claude.ai/code) — machine-independent
1. Push this folder to a Git repo (GitHub or Bitbucket).
2. Sign in at **claude.ai/code** and **connect that repo** (this creates the cloud environment).
3. Create a **Routine**:
   - Schedule: `0 1,17 * * *` UTC — two start-of-day slots covering both shifts: 09:00 Taipei (01:00 UTC) and 09:00 PST (17:00 UTC).
   - Prompt: "Read `run_prompt.md` in this repo and execute it exactly and autonomously."
4. Click **Run now** once to confirm the cloud env can reach the Jira + Slack connectors and can push to `main`.

## Publishing — GitHub Pages (no approval gate)
The dashboard is served by GitHub Pages from `docs/index.html` on `main`. Each run regenerates that file,
commits it, and pushes; Pages redeploys automatically. This replaces the old claude.ai Artifact publish,
which required an interactive approval that scheduled/headless runs can't satisfy (so the dashboard froze).
- Repo **Settings → Pages → Source: Deploy from a branch → `main` / `/docs`**.
- Live URL: https://a-chan23.github.io/nova-handoff/

## Requirements for the cloud run
- Jira (Atlassian) and Slack connectors enabled for the claude.ai account/workspace the Routine runs under.
- Push access to `main` (to publish the refreshed `docs/index.html`) and post rights to Slack channel `C0B398LUE12`.

## Refreshing the component index (when nova-web changes)
Re-run the index builder against a fresh nova-web checkout and commit the updated `component_index.json`.
