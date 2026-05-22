#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 scripts/generate_dataset_governance_report.py --input examples/evidence-quality/sample-dataset-provenance-snapshot.json
