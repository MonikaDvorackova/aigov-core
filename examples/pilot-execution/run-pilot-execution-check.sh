#!/usr/bin/env bash
# Run Phase 9 pilot execution diagnostics from repo root (no network; stdlib Python only).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 scripts/pilot_execution_check.py --json | python3 -c "import json,sys;d=json.load(sys.stdin);assert d.get('ok')is True,d;assert d.get('score')==100,d;assert isinstance(d.get('checked_paths'),list)"
python3 scripts/validate_pilot_manifest.py --json | python3 -c "import json,sys;d=json.load(sys.stdin);assert d.get('ok')is True,d;assert not d.get('errors'),d"
echo "pilot-execution-check: OK (pilot_execution_check + validate_pilot_manifest)"
