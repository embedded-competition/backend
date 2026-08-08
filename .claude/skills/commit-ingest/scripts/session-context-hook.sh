#!/usr/bin/env bash
# Claude Code SessionStart hook: inject compact, deprecation-aware project context
# from the git commit log. Emits the JSON `additionalContext` form Claude Code requires.
# No-ops cleanly (exit 0, no output) outside a git repo or with no live context.
# Wire in settings.json:
#   { "hooks": { "SessionStart": [ { "matcher": "*",
#       "hooks": [ { "type": "command", "command": "<abs>/session-context-hook.sh" } ] } ] } }
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
ctx="$(bash "$here/ingest-commit-log.sh" main 2>/dev/null || true)"
[ -z "$ctx" ] && exit 0

printf '%s' "$ctx" | python3 -c \
  'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":sys.stdin.read()}}))' \
  2>/dev/null || exit 0
