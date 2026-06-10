#!/usr/bin/env bash
# Smoke the mounted aigov_audit core routes (curl, no background polling).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE="${GOVAI_AUDIT_BASE_URL:-http://127.0.0.1:8088}"
BASE="${BASE%/}"
API_KEY="${GOVAI_API_KEY:-}"
RUN_ID="${GOVAI_RUN_ID:-smoke-$(date +%s)}"
EVENT_ID="${GOVAI_EVENT_ID:-${RUN_ID}-discovery}"

if [[ -z "${API_KEY}" ]]; then
  echo "GOVAI_API_KEY is required (must match a key in the server's GOVAI_API_KEYS / GOVAI_API_KEYS_JSON)." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required." >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to render the discovery fixture." >&2
  exit 1
fi

AUTH=(-H "Authorization: Bearer ${API_KEY}")
JSON=(-H "Content-Type: application/json")

echo "== GovAI Core runtime smoke =="
echo "base_url=${BASE}"
echo "run_id=${RUN_ID}"
echo

BODY="$(python3 - "${ROOT}" "${RUN_ID}" "${EVENT_ID}" <<'PY'
import json
import sys
from pathlib import Path

root, run_id, event_id = sys.argv[1:4]
path = Path(root) / "examples/basic-runtime-client/fixtures/discovery-event.json"
doc = json.loads(path.read_text(encoding="utf-8"))
doc["run_id"] = run_id
doc["event_id"] = event_id
print(json.dumps(doc, separators=(",", ":")))
PY
)"

echo "-> POST /evidence"
INGEST="$(curl -fsS "${AUTH[@]}" "${JSON[@]}" -d "${BODY}" "${BASE}/evidence")"
echo "${INGEST}" | python3 -m json.tool
echo "${INGEST}" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("ok") is True, d'

echo
echo "-> GET /compliance-summary/${RUN_ID}"
SUMMARY="$(curl -fsS "${AUTH[@]}" "${BASE}/compliance-summary/${RUN_ID}")"
echo "${SUMMARY}" | python3 -m json.tool
echo "${SUMMARY}" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert "verdict" in d, d'

echo
echo "-> GET /api/export/${RUN_ID}"
EXPORT="$(curl -fsS "${AUTH[@]}" "${BASE}/api/export/${RUN_ID}")"
echo "${EXPORT}" | python3 -m json.tool
echo "${EXPORT}" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("schema_version")=="aigov.audit_export.v1", d'

echo
echo "-> GET /verify/${RUN_ID}"
VERIFY="$(curl -fsS "${AUTH[@]}" "${BASE}/verify/${RUN_ID}")"
echo "${VERIFY}" | python3 -m json.tool
echo "${VERIFY}" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("ok") is True, d'

echo
echo "Smoke finished successfully."
