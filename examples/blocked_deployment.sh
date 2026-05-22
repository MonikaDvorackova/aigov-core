#!/usr/bin/env bash
# Contract: exit 3 (GovAI BLOCKED) when incomplete evidence remains for RUN_ID on the ledger.
#
# Prerequisites (same shape as govai-ci / local onboarding):
#   GOVAI_AUDIT_BASE_URL, GOVAI_API_KEY — required
# Optional: GOVAI_PROJECT (default: github-actions)
#
# Uses only curl + govai; events mirror the deterministic demo "incomplete phase" payloads.

set -euo pipefail

: "${GOVAI_AUDIT_BASE_URL:?missing GOVAI_AUDIT_BASE_URL}"
: "${GOVAI_API_KEY:?missing GOVAI_API_KEY}"

BASE="${GOVAI_AUDIT_BASE_URL%/}"
PROJ="${GOVAI_PROJECT:-github-actions}"
AUTH="Authorization: Bearer ${GOVAI_API_KEY}"

RUN_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
AI_SYSTEM_ID="blocked-demo-ai-system"
DATASET_ID="blocked-demo-dataset-v1"

post_evidence() {
  local name="$1"
  local body="$2"
  local response status
  response="$(mktemp)"
  status="$(
    curl -sS -o "${response}" -w "%{http_code}" \
      -X POST "${BASE}/evidence" \
      -H "${AUTH}" \
      -H "X-GovAI-Project: ${PROJ}" \
      -H "Content-Type: application/json" \
      --data "${body}" \
      || echo "000"
  )"
  printf 'POST evidence %s -> HTTP %s\n' "${name}" "${status}" >&2
  if [[ "${status}" =~ ^2 ]]; then
    rm -f "${response}"
    return 0
  fi
  cat "${response}" >&2 || true
  rm -f "${response}"
  echo "error: expected 2xx from POST /evidence (${name}); fix audit URL, API key project mapping, or service readiness (GET ${BASE}/ready)." >&2
  exit 1
}

MODEL_VERSION_ID="model_version_01_${RUN_ID}"

post_evidence data_registered "{\"event_id\":\"demo_data_registered_${RUN_ID}\",\"event_type\":\"data_registered\",\"ts_utc\":\"${TS}\",\"actor\":\"blocked_demo\",\"system\":\"blocked_demo_cli\",\"run_id\":\"${RUN_ID}\",\"payload\":{\"ai_system_id\":\"${AI_SYSTEM_ID}\",\"dataset_id\":\"${DATASET_ID}\",\"dataset\":\"blocked_demo_dataset\",\"dataset_version\":\"v1\",\"dataset_fingerprint\":\"sha256:blocked_demo\",\"dataset_governance_id\":\"gov_blocked_v1\",\"dataset_governance_commitment\":\"basic_compliance\",\"source\":\"internal\",\"intended_use\":\"blocked deployment example\",\"limitations\":\"demo only\",\"quality_summary\":\"demo only\",\"governance_status\":\"registered\"}}"
post_evidence model_trained "{\"event_id\":\"demo_model_trained_${RUN_ID}\",\"event_type\":\"model_trained\",\"ts_utc\":\"${TS}\",\"actor\":\"blocked_demo\",\"system\":\"blocked_demo_cli\",\"run_id\":\"${RUN_ID}\",\"payload\":{\"model_version_id\":\"${MODEL_VERSION_ID}\",\"ai_system_id\":\"${AI_SYSTEM_ID}\",\"dataset_id\":\"${DATASET_ID}\",\"model_type\":\"LogisticRegression\",\"artifact_path\":\"registry://blocked-demo/model/${MODEL_VERSION_ID}\",\"artifact_sha256\":\"blocked_placeholder\"}}"

govai_check_out="$(mktemp)"
set +e
govai --project "${PROJ}" check --run-id "${RUN_ID}" 2>&1 | tee "${govai_check_out}"
exit_code="$?"
set -e
first="$(head -n 1 "${govai_check_out}" | tr -d '\r')"
rm -f "${govai_check_out}"

if [[ "${exit_code}" -ne 3 ]]; then
  echo "error: expected govai check to exit with code 3 (BLOCKED); got exit_code=${exit_code} first_line=${first}" >&2
  exit 1
fi
echo "blocked_deployment_example: OK (EXIT 3 BLOCKED as expected for incomplete evidence)" >&2
exit 0
