"""
Exit codes for the ``govai`` CLI (Terminal SDK v0.2).

0 — Success (command completed; ``check`` / artifact verify when verdict VALID).
1 — ERROR: transport, HTTP failure, parse failure, hash continuity mismatch, unexpected exception.
2 — INVALID: compliance verdict INVALID (policy/evaluation says not valid).
3 — BLOCKED: compliance verdict BLOCKED (requirements not satisfied / not yet eligible).
4 — USAGE: missing required flags/args, invalid CLI invocation (including argparse errors).
"""

from __future__ import annotations

EX_OK = 0
EX_ERR = 1
EX_INVALID = 2
EX_BLOCKED = 3
EX_USAGE = 4
