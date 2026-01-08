#!/bin/bash
set -euo pipefail

semver_regex="^([0-9]+)\.([0-9]+)\.([0-9]+)(-([a-zA-Z][0-9a-zA-Z]*)\.([0-9]+))?$"
version_file="$1"
file_version=
next_version="${2:-}"

if [[ ! -f "$version_file" ]]; then
  echo "[ERR]: '$version_file' file not found" >&2
  exit 1
fi

file_version=$(tr -d "[:space:]" < "$version_file")
if [[ ! "$file_version" =~ $semver_regex ]]; then
  echo "[ERR]: File version invalid: '$file_version'" >&2
  exit 1
else
  echo "[INF]: File version valid: $file_version"
fi

if [[ "$next_version" = "" ]]; then
  echo "[INF]: No next version, exiting"
  exit 0
fi
if [[ ! "$next_version" =~ $semver_regex ]]; then
  echo "[ERR]: Invalid next version: '$next_version'" >&2
  exit 1
fi
if [[ "$file_version" != "$next_version" ]]; then
  echo "[ERR]: File version ($file_version) != Next version ($next_version)" >&2
  exit 1
else
  echo "[INF]: File version = Next version, continuing"
fi
