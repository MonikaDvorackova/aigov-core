#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 scripts/validate_research_manifest.py --json | python3 -c "import json,sys;d=json.load(sys.stdin);assert d.get('ok')is True,d;assert not d.get('errors'),d"
python3 scripts/research_package_check.py --json | python3 -c "import json,sys;d=json.load(sys.stdin);assert d.get('ok')is True,d;assert not d.get('failures'),d"
echo "run-research-package-check.sh: OK"
