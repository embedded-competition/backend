#!/usr/bin/env bash
# Assemble a squash-merge commit body from a feature branch's commits (deterministic).
# Order: ADR section FIRST (full decision text), aggregated trailer block LAST — so the
# trailers (incl. one `ADR:` per carried decision) are a real git trailer block, parseable
# by `git interpret-trailers` / `%(trailers)` and discoverable on main by `git log --grep`.
# - Aggregates Feature, Agent, Verdict across base..feature; emits an `ADR:` trailer per ADR.
# - Carries the FULL body of every ADR commit (message has an `ADR:` trailer).
# - plan/eval detail is intentionally dropped; only their trailers aggregate.
# Run with cwd inside the repo (caller sets cwd). Caller-agnostic.
# Usage:   assemble-squash-body.sh <base-ref> <feature-ref>
set -euo pipefail
base="${1:?usage: assemble-squash-body.sh <base-ref> <feature-ref>}"
feat="${2:?usage: assemble-squash-body.sh <base-ref> <feature-ref>}"
range="${base}..${feat}"

trailer_values() {
  git log --reverse "$range" --format="%(trailers:key=$1,valueonly)" | sed '/^[[:space:]]*$/d' | awk '!seen[$0]++'
}
feature=$(trailer_values Feature | head -1)
agents=$(trailer_values Agent | paste -sd',' - | sed 's/,/, /g')
verdict=$(trailer_values Verdict | tail -1)
# ADR-authoring commits: subject starts with `adr(` (ard.md). NOT the `ADR:` back-reference
# trailer that non-ADR commits use — matching that would double-carry the decision.
adr_shas=$(git log "$range" --format='%H' --grep='^adr(' || true)

adr_of() { git log -1 "$1" --format="%(trailers:key=ADR,valueonly)" | sed '/^[[:space:]]*$/d' | head -1; }

# 1) ADR section first — full decision text carried so it survives the squash
if [ -n "$adr_shas" ]; then
  echo "## Decisions (ADR)"
  while IFS= read -r sha; do
    [ -z "$sha" ] && continue
    echo
    echo "### ADR: $(adr_of "$sha")"
    git log -1 "$sha" --format='%b' | sed -E '/^(Agent|Phase|Feature|ADR|Verdict|Supersedes):[[:space:]]/d'
  done <<< "$adr_shas"
  echo   # blank line so the trailing trailer block is a separate (last) paragraph
fi

# 2) aggregated trailer block LAST — parseable git trailers (incl. one ADR: per decision)
[ -n "$feature" ] && echo "Feature: $feature"
[ -n "$agents"  ] && echo "Agent: $agents"
[ -n "$verdict" ] && echo "Verdict: $verdict"
if [ -n "$adr_shas" ]; then
  while IFS= read -r sha; do
    [ -z "$sha" ] && continue
    a=$(adr_of "$sha"); [ -n "$a" ] && echo "ADR: $a"
  done <<< "$adr_shas"
fi
