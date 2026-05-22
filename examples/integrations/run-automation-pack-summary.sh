#!/usr/bin/env bash
# GovAI Phase 16 example: print Markdown automation pack summary to stdout.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/generate_automation_pack_summary.py --pack examples/integrations/sample-automation-pack.json
