#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"
python3 scripts/operational_health_score.py \
  --input examples/observability/sample-operational-snapshot.json
