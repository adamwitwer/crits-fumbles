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
DIST_DIR="$REPO_ROOT/dist"
ZIP_PATH="$DIST_DIR/module.zip"

cd "$REPO_ROOT"

# Regenerate the data file so a release can never ship stale tables.
python3 tools/build-foundry-tables.py

VERSION="$(python3 -c "import json;print(json.load(open('$MODULE_DIR/module.json'))['version'])")"
TAG="v$VERSION"

# The download URL is version-pinned, so it must match the tag we are about to create.
EXPECTED_DOWNLOAD="https://github.com/adamwitwer/crits-fumbles/releases/download/$TAG/module.zip"
ACTUAL_DOWNLOAD="$(python3 -c "import json;print(json.load(open('$MODULE_DIR/module.json'))['download'])")"
if [[ "$ACTUAL_DOWNLOAD" != "$EXPECTED_DOWNLOAD" ]]; then
  echo "module.json download URL does not match version $VERSION:" >&2
  echo "  expected: $EXPECTED_DOWNLOAD" >&2
  echo "  actual:   $ACTUAL_DOWNLOAD" >&2
  exit 1
fi

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"
(cd "$MODULE_DIR" && zip -rq "$ZIP_PATH" . -x '*.DS_Store')
cp "$MODULE_DIR/module.json" "$DIST_DIR/module.json"

# Guard the packaging mistake that silently produces Data/modules/<id>/<id>/.
if ! unzip -Z1 "$ZIP_PATH" | grep -qx 'module.json'; then
  echo "module.json is not at the zip root — Foundry would install this one level too deep." >&2
  exit 1
fi

echo "Built $TAG:"
unzip -Z1 "$ZIP_PATH" | sed 's/^/  /'

if [[ "${1:-}" == "--release" ]]; then
  gh release create "$TAG" "$ZIP_PATH" "$DIST_DIR/module.json" \
    --title "Crits & Fumbles $TAG" \
    --notes "Install in Foundry with this manifest URL:

\`https://github.com/adamwitwer/crits-fumbles/releases/latest/download/module.json\`

See \`foundry/crits-fumbles/README.md\` for setup and current limitations."
  echo
  echo "Manifest URL: https://github.com/adamwitwer/crits-fumbles/releases/latest/download/module.json"
fi
