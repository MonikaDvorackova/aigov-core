#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"
python3 scripts/generate_regulatory_evidence_export.py \
  --manifest docs/regulatory/regulatory-evidence-manifest.json
