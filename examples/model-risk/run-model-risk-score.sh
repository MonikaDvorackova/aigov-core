#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec python3 scripts/model_risk_score.py --input examples/model-risk/sample-model-evaluation-snapshot.json
