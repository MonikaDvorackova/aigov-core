#!/usr/bin/env python3
"""Merge gateway metadata into an evidence payload before submit."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python"))

from aigov_py.runtime import EvidenceEvent, RuntimeGovernanceClient
from aigov_py.runtime.adapters.langchain import utc_ts
from aigov_py.runtime.adapters.openai_gateway import gateway_request_metadata, merge_payload


def main() -> None:
    base = os.environ.get("GOVAI_AUDIT_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    client = RuntimeGovernanceClient(
        base,
        api_key=os.environ.get("GOVAI_API_KEY"),
        project=os.environ.get("GOVAI_PROJECT"),
        timeout_sec=15.0,
    )
    run_id = os.environ.get("GOVAI_RUN_ID", "example-run-id")
    gw = gateway_request_metadata(
        route_id="primary",
        upstream_model="gpt-example",
        correlation_id="corr-001",
    )
    payload = merge_payload({"step": "completion"}, gw)
    event = EvidenceEvent(
        event_id="gw_example_1",
        event_type="model_inference",
        ts_utc=utc_ts(),
        actor="openai-gateway-example",
        system="examples.runtime_governance",
        run_id=run_id,
        payload=payload,
    )
    if os.environ.get("GOVAI_EXAMPLE_EXECUTE") != "1":
        print("Dry run: set GOVAI_EXAMPLE_EXECUTE=1 to POST evidence.", file=sys.stderr)
        return
    client.submit_evidence(event)
    print("submitted gateway-tagged evidence")


if __name__ == "__main__":
    main()
