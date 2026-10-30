#!/usr/bin/env bash
# Builds dist/one-on-one-<version>.zip with plugin.json at the archive root, the
# layout `claude --plugin-dir <zip>` and plugin uploads expect. Uses git archive
# so the zip holds exactly what's committed: no caches, local config or run data.
set -euo pipefail

cd "$(dirname "$0")/.."
plugin_dir=plugins/one-on-one

if [[ -n "$(git status --porcelain -- "$plugin_dir")" ]]; then
  echo "Uncommitted changes in $plugin_dir; commit them first so the zip matches." >&2
  exit 1
fi

version=$(python3 -c "import json; print(json.load(open('$plugin_dir/.claude-plugin/plugin.json'))['version'])")
out="dist/one-on-one-$version.zip"
mkdir -p dist
rm -f "$out"
git archive --format=zip -o "$out" "HEAD:$plugin_dir"

# `claude plugin validate` reads directories, not zips, so check an unpacked copy.
check=$(mktemp -d)
trap 'rm -rf "$check"' EXIT
unzip -q "$out" -d "$check"
claude plugin validate "$check"
echo "$out"
