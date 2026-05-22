from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from nacl.signing import SigningKey, VerifyKey


def _sort_json_value(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _sort_json_value(v[k]) for k in sorted(v.keys())}
    if isinstance(v, list):
        return [_sort_json_value(x) for x in v]
    return v


def canonical_policy_payload_bytes(policy_doc: Dict[str, Any]) -> bytes:
    """
    Canonical bytes for policy signature payload:
    - JSON with keys sorted recursively
    - `signatures` field removed
    """
    doc = dict(policy_doc)
    doc.pop("signatures", None)
    canon = _sort_json_value(doc)
    return json.dumps(canon, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def policy_payload_digest_sha256_hex(policy_doc: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_policy_payload_bytes(policy_doc)).hexdigest()


@dataclass(frozen=True)
class TrustEd25519:
    issuer_id: str
    pubkeys_base64: tuple[str, ...]


def load_trust_from_env_json(raw: str) -> list[TrustEd25519]:
    t = (raw or "").strip()
    if not t:
        return []
    items = json.loads(t)
    if not isinstance(items, list):
        raise ValueError("trust JSON must be a list")
    out: list[TrustEd25519] = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise ValueError(f"trust[{i}] must be an object")
        issuer_id = str(it.get("issuer_id") or "").strip()
        if not issuer_id:
            raise ValueError(f"trust[{i}].issuer_id must be non-empty")
        pks = it.get("pubkeys_base64")
        if not isinstance(pks, list) or not pks:
            raise ValueError(f"trust[{i}].pubkeys_base64 must be a non-empty list")
        out.append(TrustEd25519(issuer_id=issuer_id, pubkeys_base64=tuple(str(x).strip() for x in pks)))
    return out


def _iter_verify_keys(trust: Iterable[TrustEd25519], issuer_id: str) -> Iterable[VerifyKey]:
    for t in trust:
        if t.issuer_id != issuer_id:
            continue
        for pk_b64 in t.pubkeys_base64:
            pk_bytes = base64.b64decode(pk_b64)
            yield VerifyKey(pk_bytes)


def sign_policy_bundle_ed25519(
    policy_path: str | Path,
    *,
    out_path: str | Path,
    issuer_id: str,
    signer: str,
    private_key_base64: str,
    created_at_utc: str,
    expires_at_utc: Optional[str] = None,
) -> None:
    p = Path(policy_path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("policy bundle must be a JSON object")
    if str(doc.get("schema") or "").strip() != "govai.policy.v1":
        raise ValueError("unsupported policy schema (expected govai.policy.v1)")
    issuer_obj = doc.get("issuer")
    if not isinstance(issuer_obj, dict) or str(issuer_obj.get("issuer_id") or "").strip() != issuer_id:
        raise ValueError("policy.issuer.issuer_id does not match --issuer-id")

    digest = policy_payload_digest_sha256_hex(doc)

    sk = SigningKey(base64.b64decode(private_key_base64.strip()))
    sig_bytes = sk.sign(digest.encode("utf-8")).signature
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

    sig_record: Dict[str, Any] = {
        "kind": "ed25519",
        "signer": signer,
        "created_at_utc": created_at_utc,
        "expires_at_utc": expires_at_utc,
        "payload_digest_sha256": digest,
        "signature": {"encoding": "base64", "value": sig_b64},
        "sigstore": None,
    }

    sigs = doc.get("signatures")
    if sigs is None:
        doc["signatures"] = [sig_record]
    elif isinstance(sigs, list):
        doc["signatures"] = list(sigs) + [sig_record]
    else:
        raise ValueError("policy.signatures must be an array when present")

    out = Path(out_path)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_policy_bundle_ed25519(
    policy_doc: Dict[str, Any],
    *,
    trust: Iterable[TrustEd25519],
) -> None:
    if str(policy_doc.get("schema") or "").strip() != "govai.policy.v1":
        raise ValueError("unsupported policy schema (expected govai.policy.v1)")
    issuer = policy_doc.get("issuer")
    if not isinstance(issuer, dict):
        raise ValueError("policy.issuer must be an object")
    issuer_id = str(issuer.get("issuer_id") or "").strip()
    if not issuer_id:
        raise ValueError("policy.issuer.issuer_id must be non-empty")

    sigs = policy_doc.get("signatures")
    if not isinstance(sigs, list) or not sigs:
        raise ValueError("policy is unsigned (signatures missing/empty)")

    digest = policy_payload_digest_sha256_hex(policy_doc)

    last_err: Optional[str] = None
    for s in sigs:
        if not isinstance(s, dict):
            last_err = "signature record must be an object"
            continue
        if str(s.get("kind") or "") != "ed25519":
            last_err = "unsupported signature kind"
            continue
        if str(s.get("payload_digest_sha256") or "").strip().lower() != digest:
            last_err = "payload digest mismatch"
            continue
        sig = s.get("signature")
        if not isinstance(sig, dict) or str(sig.get("encoding") or "") != "base64":
            last_err = "unsupported signature encoding"
            continue
        sig_b64 = str(sig.get("value") or "").strip()
        if not sig_b64:
            last_err = "signature value empty"
            continue
        sig_bytes = base64.b64decode(sig_b64)

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
    raise ValueError(last_err or "no valid signature found")

