"""
Ed25519 signing and verification for ``aigov.audit_export.v1`` documents.

Signing is a post-export step: it does not modify append-only ledger semantics.
The canonical signing payload binds schema version, run_id, content hashes, and verdict.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from nacl.signing import SigningKey, VerifyKey

from aigov_py.canonical_json import canonical_bytes
from aigov_py.policy_bundle_signing import TrustEd25519, _iter_verify_keys, load_trust_from_env_json
from aigov_py.portable_evidence_digest import portable_evidence_digest_v1

SUPPORTED_EXPORT_SCHEMA = "aigov.audit_export.v1"
SIGNATURE_KIND_ED25519 = "ed25519"


@dataclass(frozen=True)
class AuditExportSigningPayload:
    """Deterministic preimage fields for an export signature (excludes ``signatures``)."""

    schema_version: str
    run_id: str
    policy_version: str
    environment: str
    bundle_sha256: str
    events_content_sha256: str
    chain_head_record_sha256: str
    decision_verdict: str

    def as_dict(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "policy_version": self.policy_version,
            "environment": self.environment,
            "bundle_sha256": self.bundle_sha256,
            "events_content_sha256": self.events_content_sha256,
            "chain_head_record_sha256": self.chain_head_record_sha256,
            "decision_verdict": self.decision_verdict,
        }


def export_run_id(export_doc: dict[str, Any]) -> str:
    run = export_doc.get("run")
    if not isinstance(run, dict):
        return ""
    return str(run.get("run_id") or "").strip()


def canonical_audit_export_signing_payload(export_doc: dict[str, Any]) -> AuditExportSigningPayload:
    """Build the deterministic preimage used for Ed25519 signing and verification."""

    doc = dict(export_doc)
    doc.pop("signatures", None)
    eh = doc.get("evidence_hashes")
    if not isinstance(eh, dict):
        eh = {}
    decision = doc.get("decision")
    if not isinstance(decision, dict):
        decision = {}
    chain_head = eh.get("chain_head_record_sha256")
    return AuditExportSigningPayload(
        schema_version=str(doc.get("schema_version") or "").strip(),
        run_id=export_run_id(doc),
        policy_version=str(doc.get("policy_version") or "").strip(),
        environment=str(doc.get("environment") or "").strip(),
        bundle_sha256=str(eh.get("bundle_sha256") or "").strip().lower(),
        events_content_sha256=str(eh.get("events_content_sha256") or "").strip().lower(),
        chain_head_record_sha256=str(chain_head or "").strip().lower()
        if chain_head is not None
        else "",
        decision_verdict=str(decision.get("verdict") or "").strip(),
    )


def audit_export_payload_digest_sha256_hex(export_doc: dict[str, Any]) -> str:
    """SHA-256 hex digest over canonical JSON of the signing payload."""

    payload = canonical_audit_export_signing_payload(export_doc)
    return hashlib.sha256(canonical_bytes(payload.as_dict())).hexdigest()


def _require_sha256_hex(label: str, value: str) -> str:
    v = (value or "").strip().lower()
    if len(v) != 64 or not all(c in "0123456789abcdef" for c in v):
        raise ValueError(f"{label} must be 64 lowercase hex characters")
    return v


def validate_export_schema_version(export_doc: dict[str, Any]) -> None:
    schema = str(export_doc.get("schema_version") or "").strip()
    if schema != SUPPORTED_EXPORT_SCHEMA:
        raise ValueError(
            f"unsupported export schema {schema!r} (expected {SUPPORTED_EXPORT_SCHEMA})"
        )


def validate_export_run_id_consistency(export_doc: dict[str, Any]) -> str:
    run_id = export_run_id(export_doc)
    if not run_id:
        raise ValueError("run.run_id is missing or empty")
    events = export_doc.get("evidence_events")
    if not isinstance(events, list):
        raise ValueError("evidence_events must be an array")
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            raise ValueError(f"evidence_events[{i}] must be an object")
        ev_run = str(ev.get("run_id") or "").strip()
        if ev_run != run_id:
            raise ValueError(
                f"evidence_events[{i}].run_id {ev_run!r} inconsistent with run.run_id {run_id!r}"
            )
    return run_id


def validate_events_content_sha256(export_doc: dict[str, Any], *, run_id: str) -> None:
    eh = export_doc.get("evidence_hashes")
    if not isinstance(eh, dict):
        raise ValueError("evidence_hashes must be an object")
    declared = _require_sha256_hex(
        "evidence_hashes.events_content_sha256",
        str(eh.get("events_content_sha256") or ""),
    )
    events = export_doc.get("evidence_events")
    if not isinstance(events, list):
        raise ValueError("evidence_events must be an array")
    recomputed = portable_evidence_digest_v1(run_id, [dict(e) for e in events if isinstance(e, dict)])
    if recomputed != declared:
        raise ValueError(
            "events_content_sha256 mismatch: export evidence does not match recomputed digest"
        )


def validate_bundle_sha256_field(export_doc: dict[str, Any]) -> str:
    eh = export_doc.get("evidence_hashes")
    if not isinstance(eh, dict):
        raise ValueError("evidence_hashes must be an object")
    return _require_sha256_hex(
        "evidence_hashes.bundle_sha256",
        str(eh.get("bundle_sha256") or ""),
    )


def validate_signed_audit_export_integrity(export_doc: dict[str, Any]) -> AuditExportSigningPayload:
    """
    Structural and digest checks before signature verification.

    Does not verify Ed25519 signatures; use :func:`verify_signed_audit_export`.
    """

    validate_export_schema_version(export_doc)
    run_id = validate_export_run_id_consistency(export_doc)
    validate_events_content_sha256(export_doc, run_id=run_id)
    validate_bundle_sha256_field(export_doc)
    payload = canonical_audit_export_signing_payload(export_doc)
    if payload.run_id != run_id:
        raise ValueError("canonical signing payload run_id mismatch")
    return payload


def sign_audit_export_ed25519(
    export_path: str | Path,
    *,
    out_path: str | Path,
    issuer_id: str,
    signer: str,
    private_key_base64: str,
    created_at_utc: str,
    expires_at_utc: str | None = None,
) -> dict[str, Any]:
    """Sign an audit export JSON file and write the document with a ``signatures`` array."""

    p = Path(export_path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("audit export must be a JSON object")
    validate_signed_audit_export_integrity(doc)

    digest = audit_export_payload_digest_sha256_hex(doc)
    sk = SigningKey(base64.b64decode(private_key_base64.strip()))
    sig_bytes = sk.sign(digest.encode("utf-8")).signature
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")
    payload = canonical_audit_export_signing_payload(doc)

    sig_record: dict[str, Any] = {
        "kind": SIGNATURE_KIND_ED25519,
        "issuer_id": issuer_id.strip(),
        "signer": signer.strip(),
        "created_at_utc": created_at_utc,
        "expires_at_utc": expires_at_utc,
        "payload_digest_sha256": digest,
        "canonical_payload": payload.as_dict(),
        "signature": {"encoding": "base64", "value": sig_b64},
    }

    sigs = doc.get("signatures")
    if sigs is None:
        doc["signatures"] = [sig_record]
    elif isinstance(sigs, list):
        doc["signatures"] = list(sigs) + [sig_record]
    else:
        raise ValueError("export.signatures must be an array when present")

    out = Path(out_path)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def verify_audit_export_ed25519_signature(
    export_doc: dict[str, Any],
    *,
    trust: Iterable[TrustEd25519],
) -> None:
    """Verify at least one valid Ed25519 signature on the export canonical digest."""

    validate_signed_audit_export_integrity(export_doc)
    digest = audit_export_payload_digest_sha256_hex(export_doc)

    sigs = export_doc.get("signatures")
    if not isinstance(sigs, list) or not sigs:
        raise ValueError("export is unsigned (signatures missing or empty)")

    last_err: str | None = None
    for s in sigs:
        if not isinstance(s, dict):
            last_err = "signature record must be an object"
            continue
        if str(s.get("kind") or "") != SIGNATURE_KIND_ED25519:
            last_err = "unsupported signature kind"
            continue
        if str(s.get("payload_digest_sha256") or "").strip().lower() != digest:
            last_err = "payload digest mismatch"
            continue
        issuer_id = str(s.get("issuer_id") or "").strip()
        if not issuer_id:
            last_err = "signature issuer_id missing"
            continue
        sig = s.get("signature")
        if not isinstance(sig, dict) or str(sig.get("encoding") or "") != "base64":
            last_err = "unsupported signature encoding"
            continue
        sig_b64 = str(sig.get("value") or "").strip()
        if not sig_b64:
            last_err = "signature value empty"
            continue
        try:
            sig_bytes = base64.b64decode(sig_b64)
        except Exception as e:  # noqa: BLE001
            last_err = f"invalid signature base64: {e}"
            continue

        ok = False
        for vk in _iter_verify_keys(trust, issuer_id):
            try:
                vk.verify(digest.encode("utf-8"), sig_bytes)
                ok = True
                break
            except Exception as e:  # noqa: BLE001
                last_err = str(e) or "verify failed"
        if ok:
            return
    raise ValueError(last_err or "no valid export signature found")


def verify_signed_audit_export(
    export_doc: dict[str, Any],
    *,
    trust: Iterable[TrustEd25519],
) -> AuditExportSigningPayload:
    """Full verification: integrity checks + Ed25519 signature."""

    verify_audit_export_ed25519_signature(export_doc, trust=trust)
    return canonical_audit_export_signing_payload(export_doc)


__all__ = [
    "SUPPORTED_EXPORT_SCHEMA",
    "SIGNATURE_KIND_ED25519",
    "AuditExportSigningPayload",
    "TrustEd25519",
    "load_trust_from_env_json",
    "export_run_id",
    "canonical_audit_export_signing_payload",
    "audit_export_payload_digest_sha256_hex",
    "validate_export_schema_version",
    "validate_export_run_id_consistency",
    "validate_events_content_sha256",
    "validate_bundle_sha256_field",
    "validate_signed_audit_export_integrity",
    "sign_audit_export_ed25519",
    "verify_audit_export_ed25519_signature",
    "verify_signed_audit_export",
]
