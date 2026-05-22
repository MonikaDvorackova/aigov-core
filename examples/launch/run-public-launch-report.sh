#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec python3 scripts/generate_public_launch_report.py --input examples/launch/sample-standardization-readiness-snapshot.json "$@"
