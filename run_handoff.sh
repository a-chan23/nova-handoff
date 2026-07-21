#!/bin/zsh
# NOVA QA→Prod handoff — headless runner for launchd (no cloud, no app window needed).
# Runs the /nova-handoff flow via the Claude CLI against run_prompt.md.
cd /Users/amanda.chan/Documents/Claude/nova-handoff || exit 1
echo "===== run $(date -u '+%Y-%m-%dT%H:%M:%SZ') UTC =====" >> handoff.log
/usr/local/bin/claude -p "$(cat run_prompt.md)" --dangerously-skip-permissions >> handoff.log 2>&1
echo "----- exit $? -----" >> handoff.log
