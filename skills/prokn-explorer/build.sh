#!/usr/bin/env bash
# Rebuild prokn-explorer.skill from the source in this folder.
# Run it after editing SKILL.md, scripts/, or references/, then commit the new .skill.
set -euo pipefail

cd "$(dirname "$0")"

# write the bundle to the parent skills/ directory so all bundles sit together
out="../prokn-explorer.skill"

# clear the old bundle and any python cache so they don't get zipped in
rm -f "$out"
find scripts -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true

# zip the folder contents (SKILL.md at the top level of the zip)
zip -r "$out" SKILL.md scripts references -x '*/__pycache__/*' '*/.DS_Store' >/dev/null
echo "Built $out"
unzip -l "$out"
