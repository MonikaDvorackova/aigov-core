#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec python3 scripts/generate_model_assurance_report.py --input examples/model-risk/sample-model-evaluation-snapshot.json
