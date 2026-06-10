#!/usr/bin/env bash
# Resolve repo root and exec the AIGov MCP stdio server (no stdout capture).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 mcp/aigov_mcp_server.py mcp-stdio
