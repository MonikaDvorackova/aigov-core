#!/usr/bin/env python3
"""OpenAI-style chat completion flow audited via GovAI Core POST /evidence (mocked model I/O)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "examples/reference-runtime-common"))

from flow import (  # noqa: E402
    client_from_env,
    env_config,
    execute_guard,
    post_evidence_dict,
    print_json,
    read_run,
    require_api_key,
)
from lifecycle import discovery, evaluation_reported  # noqa: E402

# Mocked OpenAI-style request/response (no OPENAI_API_KEY required).
MOCK_PROMPT = "Summarize the retention policy for this AI workflow."
MOCK_COMPLETION = (
    "Retention policy: evidence is append-only; compliance verdicts are ledger-authoritative."
)


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_events(run_id: str) -> list[dict]:
    prompt_hash = _sha256_hex(MOCK_PROMPT)
    output_hash = _sha256_hex(MOCK_COMPLETION)
    return [
        discovery(run_id),
        {
            "event_id": f"{run_id}-model-input",
            "event_type": "model_input",
            "ts_utc": "2026-01-01T00:00:10Z",
            "actor": "openai-runtime-audit",
            "system": "govai-core-examples",
            "run_id": run_id,
            "payload": {
                "provider": "openai-style-mock",
                "model": "gpt-mock-4o-mini",
                "prompt_hash": prompt_hash,
                "input_preview": MOCK_PROMPT[:120],
                "correlation_id": f"{run_id}-chat-1",
            },
        },
        {
            "event_id": f"{run_id}-model-output",
            "event_type": "model_output",
            "ts_utc": "2026-01-01T00:00:11Z",
            "actor": "openai-runtime-audit",
            "system": "govai-core-examples",
            "run_id": run_id,
            "payload": {
                "provider": "openai-style-mock",
                "model": "gpt-mock-4o-mini",
                "output_hash": output_hash,
                "completion_preview": MOCK_COMPLETION[:120],
                "input_event_id": f"{run_id}-model-input",
                "finish_reason": "stop",
            },
        },
        {
            "event_id": f"{run_id}-policy-eval",
            "event_type": "policy_evaluation",
            "ts_utc": "2026-01-01T00:00:12Z",
            "actor": "openai-runtime-audit",
            "system": "govai-core-examples",
            "run_id": run_id,
            "payload": {
                "policy_id": "govai.runtime.content-safety.dev",
                "outcome": "allow",
                "reason_codes": ["MOCK_ALLOW"],
                "linked_event_ids": [f"{run_id}-model-output"],
            },
        },
        evaluation_reported(run_id, passed=True),
    ]


def main() -> None:
    cfg = env_config()
    run_id = str(cfg["run_id"])
    print("OpenAI-style GovAI Core reference (mocked model; no OpenAI API key).")
    print(f"base_url={cfg['base']} run_id={run_id}")
    print(f"mock_prompt={MOCK_PROMPT!r}")

    events = build_events(run_id)
    print(f"\nPlanned evidence events ({len(events)}):")
    for ev in events:
        print(f"  - {ev['event_type']} ({ev['event_id']})")

    if not execute_guard():
        return

    api_key = require_api_key()
    client = client_from_env()
    timeout = float(cfg["timeout"])

    for ev in events:
        print(f"\n-> POST /evidence ({ev['event_type']})")
        body = post_evidence_dict(client, ev, timeout=timeout)
        print(json.dumps(body, indent=2))
        if body.get("ok") is not True:
            raise RuntimeError(f"ingest failed: {body}")

    summary, export, verify = read_run(
        base=str(cfg["base"]),
        api_key=api_key,
        run_id=run_id,
        project=cfg["project"],
        timeout=timeout,
    )
    print_json("GET /compliance-summary", summary)
    print_json("GET /api/export/{run_id}", export)
    print_json("GET /verify", verify)

    if verify.get("ok") is not True:
        raise RuntimeError(f"verify failed: {verify}")

    print(
        "\nNote: verdict may remain BLOCKED until full governance lifecycle evidence "
        "(data_registered, risk review, human_approved, model_promoted) is present."
    )


if __name__ == "__main__":
    main()
