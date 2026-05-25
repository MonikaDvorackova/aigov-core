"""Tests for aigov.audit_export.v1 Ed25519 signing and verification."""

from __future__ import annotations

import base64
import copy
import json
from pathlib import Path

import pytest

from aigov_py.audit_export_signing import (
    SUPPORTED_EXPORT_SCHEMA,
    audit_export_payload_digest_sha256_hex,
    sign_audit_export_ed25519,
    verify_signed_audit_export,
)
from aigov_py.policy_bundle_signing import load_trust_from_env_json
from aigov_py.portable_evidence_digest import portable_evidence_digest_v1

_TEST_SEED = b"\x22" * 32


def _trust_for_seed(seed: bytes = _TEST_SEED) -> list:
    from nacl.signing import SigningKey

    pk_b64 = base64.b64encode(SigningKey(seed).verify_key.encode()).decode("ascii")
    return load_trust_from_env_json(
        json.dumps([{"issuer_id": "govai-export-signer", "pubkeys_base64": [pk_b64]}])
    )


def _minimal_export(*, run_id: str = "run-sign-test") -> dict:
    events = [
        {
            "event_id": f"{run_id}-e1",
            "event_type": "ai_discovery_reported",
            "ts_utc": "2026-01-01T00:00:01Z",
            "actor": "test",
            "system": "test",
            "run_id": run_id,
            "payload": {"openai": False, "transformers": False, "model_artifacts": False},
        }
    ]
    events_sha = portable_evidence_digest_v1(run_id, events)
    bundle_sha = "a" * 64
    return {
        "ok": True,
        "schema_version": SUPPORTED_EXPORT_SCHEMA,
        "policy_version": "test-policy",
        "environment": "dev",
        "exported_at_utc": "2026-01-01T00:00:01Z",
        "tenant": {"ledger_tenant_id": "t1", "billing_tenant_id": "t1"},
        "run": {
            "run_id": run_id,
            "policy_version": "test-policy",
            "log_path": "ledger/t1.jsonl",
            "model_artifact_path": None,
            "identifiers": {},
        },
        "evidence_hashes": {
            "bundle_sha256": bundle_sha,
            "events_content_sha256": events_sha,
            "chain_head_record_sha256": "b" * 64,
            "log_chain": [],
        },
        "decision": {
            "human_approval": None,
            "promotion": None,
            "evaluation_passed": None,
            "verdict": "BLOCKED",
            "blocked_reasons": [],
        },
        "evidence_requirements": {
            "required_evidence": [],
            "provided_evidence": [],
            "missing_evidence": [],
        },
        "evidence_events": events,
        "timestamps": {},
    }


def _sign_fixture(tmp_path: Path, doc: dict) -> dict:
    raw = tmp_path / "export.json"
    signed = tmp_path / "signed.json"
    raw.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    sign_audit_export_ed25519(
        raw,
        out_path=signed,
        issuer_id="govai-export-signer",
        signer="test",
        private_key_base64=base64.b64encode(_TEST_SEED).decode("ascii"),
        created_at_utc="2026-01-01T00:00:00Z",
    )
    return json.loads(signed.read_text(encoding="utf-8"))


def test_valid_signed_export(tmp_path: Path) -> None:
    signed = _sign_fixture(tmp_path, _minimal_export())
    payload = verify_signed_audit_export(signed, trust=_trust_for_seed())
    assert payload.run_id == "run-sign-test"
    assert payload.decision_verdict == "BLOCKED"
    digest = audit_export_payload_digest_sha256_hex(signed)
    assert signed["signatures"][0]["payload_digest_sha256"] == digest


def test_tampered_event_fails(tmp_path: Path) -> None:
    signed = _sign_fixture(tmp_path, _minimal_export())
    tampered = copy.deepcopy(signed)
    tampered["evidence_events"][0]["payload"]["openai"] = True
    with pytest.raises(ValueError, match="events_content_sha256 mismatch"):
        verify_signed_audit_export(tampered, trust=_trust_for_seed())


def test_tampered_verdict_fails(tmp_path: Path) -> None:
    signed = _sign_fixture(tmp_path, _minimal_export())
    tampered = copy.deepcopy(signed)
    tampered["decision"]["verdict"] = "VALID"
    with pytest.raises(ValueError, match="payload digest mismatch"):
        verify_signed_audit_export(tampered, trust=_trust_for_seed())


def test_wrong_public_key_fails(tmp_path: Path) -> None:
    signed = _sign_fixture(tmp_path, _minimal_export())
    other_seed = b"\x33" * 32
    with pytest.raises(ValueError):
        verify_signed_audit_export(signed, trust=_trust_for_seed(other_seed))


def test_unsupported_schema_version_fails(tmp_path: Path) -> None:
    doc = _minimal_export()
    doc["schema_version"] = "aigov.audit_export.v99"
    raw = tmp_path / "bad.json"
    raw.write_text(json.dumps(doc) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported export schema"):
        sign_audit_export_ed25519(
            raw,
            out_path=tmp_path / "out.json",
            issuer_id="govai-export-signer",
            signer="test",
            private_key_base64=base64.b64encode(_TEST_SEED).decode("ascii"),
            created_at_utc="2026-01-01T00:00:00Z",
        )
