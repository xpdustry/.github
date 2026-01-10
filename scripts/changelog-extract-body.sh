#!/bin/bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "::error::Usage: $0 <changelog_file> <output_file>" >&2
  exit 1
fi

changelog_file="$1"
output_file="$2"

if [[ ! -f "$changelog_file" ]]; then
  echo "::error::Changelog file '$changelog_file' not found" >&2
  exit 1
fi

if ! grep -q "^## SNAPSHOT" "$changelog_file"; then
  echo "::error::'## SNAPSHOT' section not found in '$changelog_file'" >&2
  exit 1
fi

# Extract content between ## SNAPSHOT and the next ## heading
result=$(awk '
  /^## SNAPSHOT/ { found=1; next }
  found && /^## / { exit }
  found && !collecting && /^[[:space:]]*$/ { next }
  found { collecting=1; print }
' "$changelog_file")

if [[ -z "$result" ]]; then
  result="No notable changes."
fi

echo "$result" > "$output_file"

echo "::notice::Changelog body extracted to '$output_file'"