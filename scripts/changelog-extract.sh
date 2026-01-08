#!/bin/bash
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "[ERR]: Usage: $0 <changelog_file> <output_file>" >&2
  exit 1
fi

changelog_file="$1"
output_file="$2"

if [ ! -f "$changelog_file" ]; then
  echo "[ERR]: Changelog file '$changelog_file' not found" >&2
  exit 1
fi

if ! grep -q "^## SNAPSHOT" "$changelog_file"; then
  echo "[ERR]: '## SNAPSHOT' section not found in '$changelog_file'" >&2
  exit 1
fi

result=$(awk '
  /^## SNAPSHOT/ { found=1; next }
  found && /^## / { exit }
  found { print }
' "$changelog_file")
# Trim the eventual newlines at the beginning
while [[ "$result" =~ ^[[:space:]] ]]; do
  result="${result#[[:space:]]}"
done
if [[ "$result" = "" ]]; then
  result="No notable changes."
fi

echo "$result" > "$output_file"

echo "[INF]: Changelog body extracted to '$output_file'"
