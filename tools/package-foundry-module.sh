#!/usr/bin/env bash
# Package the Foundry module for release.
#
# Foundry installs from a manifest URL: it fetches module.json, reads the "download"
# field, and unpacks that zip into Data/modules/<id>/. The zip therefore holds the
# module's *contents* at the archive root — module.json must be the top-level entry,
# not nested inside a folder.
#
#   ./tools/package-foundry-module.sh            # build dist/module.zip
#   ./tools/package-foundry-module.sh --release  # build, then publish a GitHub release
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODULE_DIR="$REPO_ROOT/foundry/crits-fumbles"
# Build output. Also committed, because raw.githubusercontent served this directory
# while GitHub's release API was down, and an install pointed at those URLs still
# checks them for updates. Release assets are the real channel now.
DIST_DIR="$REPO_ROOT/foundry/releases"
ZIP_PATH="$DIST_DIR/module.zip"

cd "$REPO_ROOT"

# Regenerate the data file so a build can never ship stale tables.
python3 tools/build-foundry-tables.py

# Then check the logic against it, so a release cannot ship a module whose tables,
# labels, turn rule or localization keys are broken in a way Node can see.
node tools/check-foundry-module.mjs

VERSION="$(python3 -c "import json;print(json.load(open('$MODULE_DIR/module.json'))['version'])")"
TAG="v$VERSION"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"
(cd "$MODULE_DIR" && zip -rq "$ZIP_PATH" . -x '*.DS_Store')
cp "$MODULE_DIR/module.json" "$DIST_DIR/module.json"

if [[ ! -s "$ZIP_PATH" ]]; then
  echo "zip step produced nothing at $ZIP_PATH" >&2
  exit 1
fi

# Listed once into a variable rather than piped per check: `grep -q` exits on its first
# match, and the SIGPIPE that gives the still-writing `unzip` fails the whole pipeline
# under `set -o pipefail` even though the match succeeded.
entries="$(unzip -Z1 "$ZIP_PATH")"

# Guard the packaging mistake that silently produces Data/modules/<id>/<id>/.
if ! grep -qx 'module.json' <<<"$entries"; then
  echo "module.json is not at the zip root — Foundry would install this one level too deep." >&2
  exit 1
fi

echo "Built $TAG:"
sed 's/^/  /' <<<"$entries"

if [[ "${1:-}" == "--release" ]]; then
  # Release assets are version-pinned, so the manifest must point at this tag.
  ACTUAL_DOWNLOAD="$(python3 -c "import json;print(json.load(open('$MODULE_DIR/module.json'))['download'])")"
  EXPECTED_DOWNLOAD="https://github.com/adamwitwer/crits-fumbles/releases/download/$TAG/module.zip"
  if [[ "$ACTUAL_DOWNLOAD" != "$EXPECTED_DOWNLOAD" ]]; then
    echo "Manifest still points at the raw.githubusercontent fallback, not release $TAG:" >&2
    echo "  expected: $EXPECTED_DOWNLOAD" >&2
    echo "  actual:   $ACTUAL_DOWNLOAD" >&2
    exit 1
  fi

  gh release create "$TAG" "$ZIP_PATH" "$DIST_DIR/module.json" \
    --title "Crits & Fumbles $TAG" \
    --notes "Install in Foundry with this manifest URL:

\`https://github.com/adamwitwer/crits-fumbles/releases/latest/download/module.json\`

See \`foundry/crits-fumbles/README.md\` for setup and current limitations."
  echo
  echo "Manifest URL: https://github.com/adamwitwer/crits-fumbles/releases/latest/download/module.json"
fi
