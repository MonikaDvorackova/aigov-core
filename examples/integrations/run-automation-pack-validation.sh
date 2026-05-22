#!/usr/bin/env bash
# GovAI Phase 16 example: validate sample-automation-pack.json (JSON on stdout).
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/validate_automation_pack.py --json --pack examples/integrations/sample-automation-pack.json
