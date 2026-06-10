#!/usr/bin/env bash
# AIGov MCP stdio launcher for Cursor and other MCP clients.
#
# Contract:
# - stdin/stdout pass through unchanged (newline-delimited JSON-RPC only on stdout)
# - diagnostics belong on stderr only
# - never tee, log, or redirect stdout (breaks MCP framing)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec python3 mcp/aigov_mcp_server.py mcp-stdio
