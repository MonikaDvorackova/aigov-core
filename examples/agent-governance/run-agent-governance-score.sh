#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"
python3 scripts/agent_governance_score.py --input examples/agent-governance/sample-agent-delegation-snapshot.json --json
