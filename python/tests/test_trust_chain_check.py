"""Tests for scripts/trust_chain_check.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "trust_chain_check.py"
    spec = importlib.util.spec_from_file_location("trust_chain_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tcc_mod():
    return _load_mod()


def test_repo_defaults_ok(tcc_mod):
    payload, code = tcc_mod.run_check(REPO_ROOT)
    assert payload["ok"] is True
    assert code == 0
    assert payload["errors"] == []
    raw = tcc_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_bad_algorithm_rejected(tcc_mod, tmp_path: Path):
    signing = {
        "algorithms": [{"digest_alg": "MD5", "id": "bad", "jose_alg": "ES256"}],
        "artifact_types": ["evidence_pack"],
        "canonicalization": "application/json+rfc8785",
        "document_role": tcc_mod.ROLE_SIGNING,
        "profile_id": "govai.signing.v1",
        "verification_profile_id": "govai.verification.v1",
        "version": 1,
    }
    (tmp_path / "trust").mkdir()
    (tmp_path / "trust" / "signing-profile.json").write_text(json.dumps(signing), encoding="utf-8")
    # minimal sibling files to avoid file_missing; cross-validate may still fail
    for name, obj in [
        (
            "verification-profile.json",
            {
                "accepted_algorithm_ids": ["es256-p256"],
                "algorithms": [{"digest_alg": "SHA-256", "id": "es256-p256", "jose_alg": "ES256"}],
                "allowed_signing_profile_ids": ["govai.signing.v1"],
                "document_role": tcc_mod.ROLE_VERIFICATION,
                "profile_id": "govai.verification.v1",
                "trust_anchor_roles": ["org_root"],
                "version": 1,
            },
        ),
        (
            "trust-chain-example.json",
            {
                "anchors": [{"kid": "k1", "role": "org_root"}],
                "chain_id": "c1",
                "document_role": tcc_mod.ROLE_TRUST_CHAIN,
                "edges": [{"child_kid": "k1", "parent_kid": "k1", "relation": "self"}],
                "signing_profile_id": "govai.signing.v1",
                "verification_profile_id": "govai.verification.v1",
                "version": 1,
            },
        ),
        (
            "key-rotation-policy.json",
            {
                "document_role": tcc_mod.ROLE_KEY_ROTATION,
                "governance_doc_reference": "docs/trust/key-rotation.md",
                "max_active_signing_key_days": 90,
                "overlap_acceptance_days": 7,
                "policy_id": "p1",
                "signing_profile_id": "govai.signing.v1",
                "version": 1,
            },
        ),
        (
            "attestation-bundle-example.json",
            {
                "attested_artifact": {
                    "digest_alg": "SHA-256",
                    "digest_hex": "00" * 32,
                    "kind": "evidence_pack",
                },
                "bundle_id": "b1",
                "document_role": tcc_mod.ROLE_ATTESTATION,
                "payload_digest_alg": "SHA-256",
                "signatures": [{"algorithm_id": "es256-p256", "kid": "k1", "signature_format": "detached-jws"}],
                "signing_profile_id": "govai.signing.v1",
                "trust_chain_id": "c1",
                "version": 1,
            },
        ),
    ]:
        (tmp_path / "trust" / name).write_text(json.dumps(obj), encoding="utf-8")
    (tmp_path / "examples" / "trust").mkdir(parents=True)
    for ex in tcc_mod.EXAMPLE_TRUST_FILES:
        rel = Path(ex)
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        if "sample-signed" in ex:
            (tmp_path / rel).write_text(
                json.dumps(
                    {
                        "canonical_payload_digest_hex": "aa" * 48,
                        "document_role": tcc_mod.ROLE_SIGNED_EVIDENCE,
                        "pack_id": "p",
                        "payload_digest_alg": "SHA-384",
                        "signatures": [{"algorithm_id": "es384-p384", "kid": "k1", "signature_format": "detached-jws"}],
                        "signing_profile_id": "govai.signing.v1",
                        "version": 1,
                    }
                ),
                encoding="utf-8",
            )
        else:
            (tmp_path / rel).write_text(
                json.dumps(
                    {
                        "document_role": tcc_mod.ROLE_VERIFICATION_RESULT,
                        "signature_checks_status": "passed",
                        "verification_id": "v",
                        "verification_profile_id": "govai.verification.v1",
                        "version": 1,
                    }
                ),
                encoding="utf-8",
            )
    # copy real key-rotation doc so rotation reference resolves
    doc_src = REPO_ROOT / "docs" / "trust" / "key-rotation.md"
    (tmp_path / "docs" / "trust").mkdir(parents=True)
    (tmp_path / "docs" / "trust" / "key-rotation.md").write_text(doc_src.read_text(encoding="utf-8"), encoding="utf-8")

    payload, code = tcc_mod.run_check(tmp_path)
    assert code == 1
    assert payload["ok"] is False
    errs = "\n".join(payload["errors"])
    assert "algorithm_invalid_digest_alg" in errs or "invalid_digest_alg" in errs
