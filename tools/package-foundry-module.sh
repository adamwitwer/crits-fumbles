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
# Committed on purpose: this directory *is* the distribution channel. The Foundry
# server is web-admin only, so the module must install from a URL, and serving the
# manifest and zip from raw.githubusercontent needs them in the tree. Move to GitHub
# release assets once that is an option and this can go back to being ignored.
DIST_DIR="$REPO_ROOT/foundry/releases"
ZIP_PATH="$DIST_DIR/module.zip"

cd "$REPO_ROOT"

# Regenerate the data file so a build can never ship stale tables.
python3 tools/build-foundry-tables.py

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

# Guard the packaging mistake that silently produces Data/modules/<id>/<id>/.
if ! unzip -Z1 "$ZIP_PATH" | grep -qx 'module.json'; then
  echo "module.json is not at the zip root — Foundry would install this one level too deep." >&2
  exit 1
fi

echo "Built $TAG:"
unzip -Z1 "$ZIP_PATH" | sed 's/^/  /'

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
