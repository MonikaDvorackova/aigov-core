#!/usr/bin/env bash
# Example: scrape Prometheus metrics from a local audit service (no auth on /metrics).
set -euo pipefail
BASE="${GOVAI_AUDIT_BASE_URL:-http://127.0.0.1:8088}"
curl -sS "${BASE%/}/metrics" | head -n 40
