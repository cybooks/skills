#!/usr/bin/env bash
# Packages each skill folder as dist/<name>.skill (a zip with the folder at its root),
# for upload in the Claude apps.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf dist && mkdir dist
cd skills
for dir in cybooks-*/; do
  name="${dir%/}"
  [ -f "$name/SKILL.md" ] || { echo "$name: no SKILL.md" >&2; exit 1; }
  zip -qr "../dist/$name.skill" "$name" -x '*/__pycache__/*' -x '*.pyc' -x '*/.DS_Store'
  echo "dist/$name.skill"
done
