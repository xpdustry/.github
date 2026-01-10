#!/bin/bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "::error::Usage: $0 <changelog_file> <new_version>" >&2
  exit 1
fi

changelog_file="$1"
new_version="$2"

if [[ ! -f "$changelog_file" ]]; then
  echo "::error::Changelog file '$changelog_file' not found" >&2
  exit 1
fi

if ! grep -q "^## SNAPSHOT" "$changelog_file"; then
  echo "::error::'## SNAPSHOT' section not found in '$changelog_file'" >&2
  exit 1
fi

release_date=$(date -u +%Y-%m-%d)
awk -v header="## v$new_version - $release_date" '
  /^## SNAPSHOT/ { print; print ""; print header; next }
  { print }
' "$changelog_file" > "$changelog_file.tmp" && mv "$changelog_file.tmp" "$changelog_file"

echo "::notice::Changelog updated with version $new_version ($release_date)"