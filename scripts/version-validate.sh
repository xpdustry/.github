#!/bin/bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "[ERR]: Usage: $0 <version_file>" >&2
  exit 1
fi

semver_regex="^([0-9]+)\.([0-9]+)\.([0-9]+)(-([a-zA-Z][0-9a-zA-Z]*)\.([0-9]+))?$"
version_file="$1"

if [[ ! -f "$version_file" ]]; then
  echo "[ERR]: '$version_file' file not found" >&2
  exit 1
fi

version=$(tr -d "[:space:]" < "$version_file")
if [[ ! "$version" =~ $semver_regex ]]; then
  echo "[ERR]: File version invalid: '$version'" >&2
  exit 1
fi

exists=$(git tag -l "v$version")
if [ "$exists" != "" ]; then
  echo "[ERR]: The version file points to an existing tag"
  exit 1
fi

echo "[INF]: File version valid: $version"