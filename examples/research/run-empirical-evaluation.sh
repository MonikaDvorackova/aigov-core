#!/usr/bin/env bash
# Run empirical benchmark suite (stdlib Python) and validate JSON artefacts.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"
export GOVAI_EMPIRICAL_QUICK="${GOVAI_EMPIRICAL_QUICK:-1}"
make empirical-evaluation-run empirical-evaluation-check
