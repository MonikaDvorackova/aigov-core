#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"
python3 scripts/runtime_safety_score.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json
