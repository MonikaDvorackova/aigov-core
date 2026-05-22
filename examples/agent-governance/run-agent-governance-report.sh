#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"
python3 scripts/generate_agent_governance_report.py --input examples/agent-governance/sample-agent-delegation-snapshot.json
