#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 scripts/generate_governance_control_report.py --input examples/policy-intelligence/sample-governance-control-snapshot.json
