#!/usr/bin/env bash
# Compact, deprecation-aware project context from a branch's commit log.
# Reads trailers (Feature, ADR, Deprecates, Supersedes), drops deprecated/superseded,
# emits a compact LIVE view (no full bodies). Deterministic. Run with cwd inside the repo.
# Usage: ingest-commit-log.sh [<ref>]   (default: main)
set -euo pipefail
ref="${1:-main}"

# newline list of a trailer key's values across history (comma-split, trimmed)
vals() {
  git log "$ref" --format="%(trailers:key=$1,valueonly)" \
    | tr ',' '\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//; /^$/d'
}
dead=$(printf '%s\n%s\n' "$(vals Deprecates)" "$(vals Supersedes)" | sed '/^$/d' | sort -u)
is_dead() { [ -n "$1" ] && [ -n "$dead" ] && printf '%s\n' "$dead" | grep -qxF "$1"; }
trailer1() { git log -1 "$1" --format="%(trailers:key=$2,valueonly)" | sed '/^[[:space:]]*$/d' | head -1; }

echo "# Project context (live, deprecation-aware) — git log $ref"

echo
echo "## Decisions (ADR) — in force"
adr_found=0
for a in $(vals ADR | sort -u); do
  is_dead "$a" && continue
  echo "- $a"; adr_found=1
done
[ "$adr_found" = 0 ] && echo "- (없음)"

echo
echo "## Features — live"
feat_found=0; seen=" "
for sha in $(git log "$ref" --reverse --grep='^Feature:' --format='%H'); do
  feat=$(trailer1 "$sha" Feature); [ -z "$feat" ] && continue
  case "$seen" in *" $feat "*) continue ;; esac
  seen="$seen$feat "
  is_dead "$feat" && continue
  printf -- '- %s — %s\n' "$feat" "$(git log -1 "$sha" --format='%s')"; feat_found=1
done
[ "$feat_found" = 0 ] && echo "- (없음)"

if [ -n "$dead" ]; then
  dead_list=$(printf '%s\n' "$dead" | paste -sd',' - | sed 's/,/, /g')
  echo
  echo "## Deprecated (컨텍스트 제외): $(printf '%s\n' "$dead" | wc -l | tr -d ' ')개 — ${dead_list}"
fi
