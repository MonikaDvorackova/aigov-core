#!/usr/bin/env bash
# Read-only localhost probes for the GovAI audit service (no secrets, no evidence POST).
set -euo pipefail

BASE_URL="${GOVAI_AUDIT_BASE_URL:-http://127.0.0.1:8088}"
BASE_URL="${BASE_URL%/}"

echo "## curl: GET ${BASE_URL}/health"
curl -sS -o /tmp/govai_local_demo_health_body -w "HTTP %{http_code}\n" "${BASE_URL}/health" || true
echo "--- body (first 400 bytes) ---"
head -c 400 /tmp/govai_local_demo_health_body 2>/dev/null || true
echo ""
echo ""

echo "## curl: GET ${BASE_URL}/ready"
curl -sS -o /tmp/govai_local_demo_ready_body -w "HTTP %{http_code}\n" "${BASE_URL}/ready" || true
echo "--- body (first 400 bytes) ---"
head -c 400 /tmp/govai_local_demo_ready_body 2>/dev/null || true
echo ""
echo ""

echo "## curl: GET ${BASE_URL}/status"
curl -sS -o /tmp/govai_local_demo_status_body -w "HTTP %{http_code}\n" "${BASE_URL}/status" || true
echo "--- body (first 400 bytes) ---"
head -c 400 /tmp/govai_local_demo_status_body 2>/dev/null || true
echo ""
