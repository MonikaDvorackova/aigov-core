import base64
import json
from pathlib import Path

import pytest

from aigov_py.policy_bundle_signing import (
    load_trust_from_env_json,
    policy_payload_digest_sha256_hex,
    sign_policy_bundle_ed25519,
    verify_policy_bundle_ed25519,
)


def _minimal_policy(tmp_path: Path) -> Path:
    doc = {
        "schema": "govai.policy.v1",
        "policy_id": "p1",
        "version": "1",
        "created_at_utc": "2026-01-01T00:00:00Z",
        "issuer": {"issuer_id": "issuer1", "display_name": "Issuer"},
        "selectors": {"tenants": ["*"], "environments": ["dev"]},
        "inherits": [],
        "ingest_rules": {"unknown_event_types": {"behavior": "reject"}, "event_types": {}},
        "verdict_rules": {"required_evidence_codes": [], "invalid_conditions": []},
        "signatures": [],
    }
    p = tmp_path / "policy.json"
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return p


def test_policy_payload_digest_stable(tmp_path: Path) -> None:
    p = _minimal_policy(tmp_path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    d1 = policy_payload_digest_sha256_hex(doc)
    d2 = policy_payload_digest_sha256_hex(doc)
    assert d1 == d2
    assert len(d1) == 64


def test_sign_and_verify_ed25519(tmp_path: Path) -> None:
    p = _minimal_policy(tmp_path)
    out = tmp_path / "signed.json"

    # Deterministic test key: 32 bytes seed.
    seed = b"\x11" * 32
    priv_b64 = base64.b64encode(seed).decode("ascii")

    sign_policy_bundle_ed25519(
        p,
        out_path=out,
        issuer_id="issuer1",
        signer="tester",
        private_key_base64=priv_b64,
        created_at_utc="2026-01-01T00:00:00Z",
        expires_at_utc=None,
    )

    signed = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(signed.get("signatures"), list)
    assert signed["signatures"], "expected at least one signature"

    # Build trust JSON from the corresponding public key.
    from nacl.signing import SigningKey

    pk_b64 = base64.b64encode(SigningKey(seed).verify_key.encode()).decode("ascii")
    trust = load_trust_from_env_json(
        json.dumps([{"issuer_id": "issuer1", "pubkeys_base64": [pk_b64]}])
    )
    verify_policy_bundle_ed25519(signed, trust=trust)


def test_verify_fails_without_trust(tmp_path: Path) -> None:
    p = _minimal_policy(tmp_path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    with pytest.raises(ValueError):
        verify_policy_bundle_ed25519(doc, trust=[])

