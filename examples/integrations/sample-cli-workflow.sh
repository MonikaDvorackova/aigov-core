#!/usr/bin/env bash
# GovAI Phase 16 sample: sequential Makefile targets from repository root.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"
make developer-integrations
make developer-integrations-manifest
make automation-pack
make automation-pack-summary
