#!/usr/bin/env bash
# GovAI Phase 16 example: emit developer integrations diagnostics as JSON (repo root).
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/developer_integrations_check.py --json
