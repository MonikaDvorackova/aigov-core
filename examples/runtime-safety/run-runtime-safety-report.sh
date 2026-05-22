#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"
python3 scripts/generate_runtime_safety_report.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json
