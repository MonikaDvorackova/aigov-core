#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 scripts/policy_coverage_score.py --input examples/policy-intelligence/sample-governance-control-snapshot.json --json
