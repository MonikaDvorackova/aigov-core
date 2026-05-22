#!/usr/bin/env python3
"""Show how to call GovAI from LangChain-style tool hooks without importing LangChain."""

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
    client = RuntimeGovernanceClient(
        base,
        api_key=os.environ.get("GOVAI_API_KEY"),
        project=os.environ.get("GOVAI_PROJECT"),
        timeout_sec=15.0,
    )
    run_id = os.environ.get("GOVAI_RUN_ID", "example-run-id")

    hook = make_tool_evidence_hook(
        client.submit_evidence,
        run_id=run_id,
        actor="langchain-example",
        system="examples.runtime_governance",
    )
    # In a real agent, call hook(tool_name, digest) from your tool callback.
    if os.environ.get("GOVAI_EXAMPLE_EXECUTE") != "1":
        print("Dry run: set GOVAI_EXAMPLE_EXECUTE=1 to POST evidence to the audit service.", file=sys.stderr)
        return
    hook("lookup_docs", "sha256:" + "ab" * 32)
    print("submitted tool evidence (see audit service logs)")


if __name__ == "__main__":
    main()
