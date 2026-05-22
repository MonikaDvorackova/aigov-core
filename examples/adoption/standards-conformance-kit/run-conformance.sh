#!/usr/bin/env bash
# Offline conformance check for sample-valid-artifact.json (no network).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
python3 scripts/validate_standard_conformance.py \
  examples/adoption/standards-conformance-kit/sample-valid-artifact.json >/dev/null
echo "standards-conformance-kit: OK"
