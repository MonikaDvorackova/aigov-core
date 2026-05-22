#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 scripts/evidence_quality_score.py --input examples/evidence-quality/sample-dataset-provenance-snapshot.json
