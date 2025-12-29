#!/bin/bash
set -euo pipefail

semver_regex="^([0-9]+)\.([0-9]+)\.([0-9]+)(-([a-zA-Z][0-9a-zA-Z]*)\.([0-9]+))?$"
version_file="$1"
file_version=
next_version=

if [[ ! -f "$version_file" ]]; then
  echo "[ERR]: '$version_file' file not found" >&2
  exit 1
fi

file_version=$(tr -d "[:space:]" < "$version_file")
if [[ ! "$file_version" =~ $semver_regex ]]; then
  echo "[ERR]: File version invalid: '$file_version'" >&2
  exit 1
fi

major="${BASH_REMATCH[1]}"
minor="${BASH_REMATCH[2]}"
patch="${BASH_REMATCH[3]}"
extra="${BASH_REMATCH[5]}" # 4th group is contains the extra info, so we skip to 5
build="${BASH_REMATCH[6]}"
if [[ -n "$extra" ]]; then
  next_version="$major.$minor.$patch-$extra.$((build + 1))"
else
  next_version="$major.$minor.$((patch + 1))"
fi

echo -n "$next_version" > "$version_file"
echo "[INF]: Version incremented: $file_version -> $next_version"
