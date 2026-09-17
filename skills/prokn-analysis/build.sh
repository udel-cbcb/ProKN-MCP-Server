#!/usr/bin/env bash
# Rebuild prokn-analysis.skill from the source in this folder.
# Run it after editing SKILL.md or references/, then commit the new .skill.
set -euo pipefail

cd "$(dirname "$0")"

# write the bundle to the parent skills/ directory so all bundles sit together
out="../prokn-analysis.skill"

# clear the old bundle so it isn't zipped into itself
rm -f "$out"

# zip the folder contents (SKILL.md at the top level of the zip)
zip -r "$out" SKILL.md references -x '*/.DS_Store' >/dev/null

echo "Built $out"
unzip -l "$out"
