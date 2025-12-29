#!/bin/bash
set -euo pipefail

if [ $# -ne 3 ]; then
  echo "[ERR]: Usage: $0 <changelog_file> <output_file> <new_version>" >&2
  exit 1
fi

changelog_file="$1"
output_file="$2"
new_version="$3"

# Check if changelog file exists
if [ ! -f "$changelog_file" ]; then
  echo "[ERR]: Changelog file '$changelog_file' not found" >&2
  exit 1
fi

new_version_header=$'\n'"## $new_version - $(date -u +%Y-%m-%d)"
tmp=$(mktemp)
awk -v header="$new_version_header" '
  /^## SNAPSHOT/ { print; print header; next }
  { print }
' "$changelog_file" > "$tmp" && mv "$tmp" "$output_file"

echo "[INF]: Changelog updated with version $new_version"