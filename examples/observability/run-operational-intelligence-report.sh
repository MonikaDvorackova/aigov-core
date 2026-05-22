#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"
python3 scripts/generate_operational_intelligence_report.py \
  --input examples/observability/sample-operational-snapshot.json \
  --manifest docs/observability/observability-manifest.json
