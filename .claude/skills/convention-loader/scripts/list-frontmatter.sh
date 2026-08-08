#!/usr/bin/env bash
# Read ONLY the frontmatter (name, description) of every *.md under a directory (recursive).
# Bodies are never read — keeps the scan cheap for selection by description.
# Usage: list-frontmatter.sh <dir>
# Output: one record per file, blank-line separated.
#   file: <path>
#   name: <name>
#   description: <description>
set -euo pipefail
dir="${1:?usage: list-frontmatter.sh <dir>}"
found=0
while IFS= read -r f; do
  found=1
  awk '
    NR==1 && $0=="---" {infm=1; next}
    infm && $0=="---" {exit}
    infm && /^name:/        {v=$0; sub(/^name:[[:space:]]*/,"",v); name=v}
    infm && /^description:/  {v=$0; sub(/^description:[[:space:]]*/,"",v); desc=v}
    END {printf "file: %s\nname: %s\ndescription: %s\n\n", FILENAME, name, desc}
  ' "$f"
done < <(find "$dir" -type f -name '*.md' | sort)
[ "$found" = 0 ] && echo "no *.md in $dir" >&2
exit 0
