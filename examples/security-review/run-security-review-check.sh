#!/usr/bin/env bash
# Run Phase 8 security/trust diagnostics from repo root (no network; stdlib Python only).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 scripts/security_trust_check.py --json | python3 -c "import json,sys;d=json.load(sys.stdin);assert d.get('ok')is True,d;assert d.get('score')==100,d;assert isinstance(d.get('checked_paths'),list)"
python3 scripts/validate_trust_manifest.py --json | python3 -c "import json,sys;d=json.load(sys.stdin);assert d.get('ok')is True,d;assert not d.get('errors'),d"
echo "security-review-check: OK (security_trust_check + validate_trust_manifest)"
