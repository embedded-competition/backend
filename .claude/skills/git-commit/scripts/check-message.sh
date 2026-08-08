#!/usr/bin/env bash
# Validate a commit message file against shared-git-commit basics.
# - subject = <type>(<scope>)?: <text>, length <= 72
# - Feature/ADR trailer values must be <id>-<slug>, not a bare number
# Usage: check-message.sh <message-file>   (exit 0 ok, 1 violation)
set -euo pipefail
f="${1:?usage: check-message.sh <message-file>}"
subject=$(sed -n '1p' "$f")
status=0

if ! printf '%s' "$subject" | grep -qE '^(feat|fix|refactor|chore|docs|test|build|ci|perf|style|plan|eval|adr)(\([a-z0-9-]+\))?: .+'; then
  printf 'FAIL subject: "<type>(<scope>): <subject>" 형식 아님 → %s\n' "$subject"; status=1
fi
if [ "$(printf '%s' "$subject" | wc -m | tr -d ' ')" -gt 72 ]; then
  printf 'FAIL subject > 72자\n'; status=1
fi
while IFS= read -r line; do
  [ -z "$line" ] && continue
  key=${line%%:*}; val=$(printf '%s' "${line#*:}" | sed 's/^[[:space:]]*//')
  if printf '%s' "$val" | grep -qE '^[0-9]+$'; then
    printf 'FAIL trailer %s: 맨 숫자(%s) — <id>-<slug> 필요\n' "$key" "$val"; status=1
  fi
done < <(grep -E '^(Feature|ADR):[[:space:]]' "$f" || true)

# Phase / Verdict enum
while IFS= read -r line; do
  key=${line%%:*}; val=$(printf '%s' "${line#*:}" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
  case "$key" in
    Phase)   printf '%s' "$val" | grep -qxE 'plan|build|eval' || { printf 'FAIL Phase: %s — plan|build|eval 만 허용\n' "$val"; status=1; } ;;
    Verdict) printf '%s' "$val" | grep -qxE 'pass|fail|needs-changes' || { printf 'FAIL Verdict: %s — pass|fail|needs-changes 만 허용\n' "$val"; status=1; } ;;
  esac
done < <(grep -E '^(Phase|Verdict):[[:space:]]' "$f" || true)

[ "$status" = 0 ] && echo "OK: message format + trailer index valid"
exit $status
