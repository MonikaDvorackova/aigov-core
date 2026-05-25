#!/usr/bin/env python3
"""LangChain-style tool hook via existing GovAI stdlib adapter (no LangChain import)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python"))

from aigov_py.runtime import RuntimeGovernanceClient
from aigov_py.runtime.adapters.langchain import make_tool_evidence_hook


def main() -> None:
    base = os.environ.get("GOVAI_AUDIT_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    api_key = (os.environ.get("GOVAI_API_KEY") or "").strip()
    if not api_key:
        print("GOVAI_API_KEY is required.", file=sys.stderr)
        sys.exit(1)
    run_id = os.environ.get("GOVAI_RUN_ID", "langchain-hook-example")
    project = (os.environ.get("GOVAI_PROJECT") or "").strip() or None

    client = RuntimeGovernanceClient(base, api_key=api_key, project=project, timeout_sec=15.0)
    hook = make_tool_evidence_hook(
        client.submit_evidence,
        run_id=run_id,
        actor="python-runtime-client",
        system="examples.python_runtime_client",
    )

    if os.environ.get("GOVAI_EXAMPLE_EXECUTE") != "1":
        print(
            "Dry run: set GOVAI_EXAMPLE_EXECUTE=1 to POST /evidence from a tool callback pattern.",
            file=sys.stderr,
        )
        return

    hook("lookup_docs", "sha256:" + "ab" * 32)
    summary = client.get_compliance_summary(run_id)
    print(f"verdict={summary.verdict}")


if __name__ == "__main__":
    main()
