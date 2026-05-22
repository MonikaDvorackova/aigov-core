#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
OUT="${1:-examples/releases/sample-generated-release-notes-1.0.0.md}"
python3 scripts/generate_release_notes.py --version 1.0.0 --out "$OUT"
echo "Wrote: $OUT"
