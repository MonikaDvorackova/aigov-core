"""
Planning-only models for deterministic agent-action signing envelopes.

No signing, no verifier wiring, no I/O. Intended for future multi-agent trace
cryptographic attribution (Phase 4 planning).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from aigov_py.canonical_json import canonical_bytes

# Asymmetric schemes suitable for detached signatures over a digest envelope.
SIGNATURE_ALGORITHMS = frozenset({"ED25519", "ECDSA_P256_SHA256"})

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def normalize_payload_digest(raw: str) -> str:
    """
    Normalize a payload digest token to ``sha256:<64 lowercase hex>``.

    Accepts either 64 hex digits or ``sha256:<64 hex>`` (hex case-insensitive).
    """
    s = raw.strip()
    if not s:
        raise ValueError("payload_digest must be non-empty")
    body = s[7:] if s.lower().startswith("sha256:") else s
    hx = body.strip().lower()
    if not _HEX64.fullmatch(hx):
        raise ValueError(
            "payload_digest must be 64 hex chars or sha256:<64 hex>"
        )
    return f"sha256:{hx}"


@dataclass(frozen=True)
class AgentSigningKeyRef:
    """Opaque reference to the signing key material (no secrets, no PEM)."""

    ref: str

    def __post_init__(self) -> None:
        r = self.ref.strip()
        if not r:
            raise ValueError("signing_key_ref must be non-empty")
        object.__setattr__(self, "ref", r)


@dataclass(frozen=True)
class AgentActionDigest:
    """Validated payload digest; models hash-over-payload only (no raw payload)."""

    normalized: str

    @classmethod
    def parse(cls, raw: str) -> AgentActionDigest:
        return cls(normalized=normalize_payload_digest(raw))


def _canonical_envelope_payload(
    *,
    tenant_id: str,
    agent_id: str,
    principal_id: str,
    action_id: str,
    capability_id: str,
    delegation_id: str | None,
    trace_id: str | None,
    policy_snapshot_id: str,
    payload_digest: str,
    signing_key_ref: str,
    signature_algorithm: str,
) -> dict[str, str]:
    """Canonical preimage for envelope_digest (excludes envelope_digest itself)."""
    return {
        "action_id": action_id,
        "agent_id": agent_id,
        "capability_id": capability_id,
        "delegation_id": "" if delegation_id is None else delegation_id,
        "payload_digest": payload_digest,
        "policy_snapshot_id": policy_snapshot_id,
        "principal_id": principal_id,
        "signature_algorithm": signature_algorithm,
        "signing_key_ref": signing_key_ref,
        "tenant_id": tenant_id,
        "trace_id": "" if trace_id is None else trace_id,
    }


def compute_envelope_digest(preimage: dict[str, str]) -> str:
    """SHA-256 hex over canonical JSON of the envelope preimage (sorted keys)."""
    return hashlib.sha256(canonical_bytes(preimage)).hexdigest()


def _require_id(name: str, value: str) -> str:
    v = value.strip()
    if not v:
        raise ValueError(f"{name} is required")
    return v


@dataclass(frozen=True)
class AgentActionSigningEnvelope:
    """Canonical signing envelope content; ``envelope_digest`` binds all fields except itself."""

    tenant_id: str
    agent_id: str
    principal_id: str
    action_id: str
    capability_id: str
    delegation_id: str | None
    trace_id: str | None
    policy_snapshot_id: str
    payload_digest: AgentActionDigest
    signing_key_ref: AgentSigningKeyRef
    signature_algorithm: str
    envelope_digest: str


@dataclass(frozen=True)
class SignatureVerificationExpectation:
    """What a verifier would check against (planning-only; no crypto operations)."""

    envelope_digest: str
    signature_algorithm: str
    signing_key_ref: AgentSigningKeyRef
    expected_signature_ref: str | None


@dataclass(frozen=True)
class AgentActionSignaturePlan:
    """Envelope plus verification expectation for a single agent action."""

    envelope: AgentActionSigningEnvelope
    verification: SignatureVerificationExpectation


def build_agent_action_signing_envelope(
    *,
    tenant_id: str,
    agent_id: str,
    principal_id: str,
    action_id: str,
    capability_id: str,
    policy_snapshot_id: str,
    payload_digest: str | AgentActionDigest,
    signing_key_ref: str | AgentSigningKeyRef,
    signature_algorithm: str,
    delegation_id: str | None = None,
    trace_id: str | None = None,
) -> AgentActionSigningEnvelope:
    """Validate identifiers and compute deterministic ``envelope_digest``."""
    tid = _require_id("tenant_id", tenant_id)
    aid = _require_id("agent_id", agent_id)
    pid = _require_id("principal_id", principal_id)
    act = _require_id("action_id", action_id)
    cap = _require_id("capability_id", capability_id)
    pol = _require_id("policy_snapshot_id", policy_snapshot_id)

    dig = (
        payload_digest
        if isinstance(payload_digest, AgentActionDigest)
        else AgentActionDigest.parse(payload_digest)
    )

    sk = (
        signing_key_ref
        if isinstance(signing_key_ref, AgentSigningKeyRef)
        else AgentSigningKeyRef(ref=signing_key_ref)
    )

    alg = signature_algorithm.strip()
    if alg not in SIGNATURE_ALGORITHMS:
        raise ValueError(
            f"unsupported signature_algorithm {alg!r}; "
            f"allowed: {sorted(SIGNATURE_ALGORITHMS)}"
        )

    del_ref: str | None
    if delegation_id is None:
        del_ref = None
    else:
        d = delegation_id.strip()
        if not d:
            raise ValueError("delegation_id, when provided, must be non-empty")
        del_ref = d

    tr_ref: str | None
    if trace_id is None:
        tr_ref = None
    else:
        t = trace_id.strip()
        if not t:
            raise ValueError("trace_id, when provided, must be non-empty")
        tr_ref = t

    preimage = _canonical_envelope_payload(
        tenant_id=tid,
        agent_id=aid,
        principal_id=pid,
        action_id=act,
        capability_id=cap,
        delegation_id=del_ref,
        trace_id=tr_ref,
        policy_snapshot_id=pol,
        payload_digest=dig.normalized,
        signing_key_ref=sk.ref,
        signature_algorithm=alg,
    )
    env_digest = compute_envelope_digest(preimage)

    return AgentActionSigningEnvelope(
        tenant_id=tid,
        agent_id=aid,
        principal_id=pid,
        action_id=act,
        capability_id=cap,
        delegation_id=del_ref,
        trace_id=tr_ref,
        policy_snapshot_id=pol,
        payload_digest=dig,
        signing_key_ref=sk,
        signature_algorithm=alg,
        envelope_digest=env_digest,
    )


def build_signature_verification_expectation(
    envelope: AgentActionSigningEnvelope,
    *,
    expected_signature_ref: str | None = None,
) -> SignatureVerificationExpectation:
    """Derive verification expectation from a built envelope."""
    esr: str | None
    if expected_signature_ref is None:
        esr = None
    else:
        e = expected_signature_ref.strip()
        if not e:
            raise ValueError(
                "expected_signature_ref, when provided, must be non-empty"
            )
        esr = e

    return SignatureVerificationExpectation(
        envelope_digest=envelope.envelope_digest,
        signature_algorithm=envelope.signature_algorithm,
        signing_key_ref=envelope.signing_key_ref,
        expected_signature_ref=esr,
    )


def build_agent_action_signature_plan(
    *,
    tenant_id: str,
    agent_id: str,
    principal_id: str,
    action_id: str,
    capability_id: str,
    policy_snapshot_id: str,
    payload_digest: str | AgentActionDigest,
    signing_key_ref: str | AgentSigningKeyRef,
    signature_algorithm: str,
    delegation_id: str | None = None,
    trace_id: str | None = None,
    expected_signature_ref: str | None = None,
) -> AgentActionSignaturePlan:
    """Build envelope + verification expectation in one step."""
    env = build_agent_action_signing_envelope(
        tenant_id=tenant_id,
        agent_id=agent_id,
        principal_id=principal_id,
        action_id=action_id,
        capability_id=capability_id,
        policy_snapshot_id=policy_snapshot_id,
        payload_digest=payload_digest,
        signing_key_ref=signing_key_ref,
        signature_algorithm=signature_algorithm,
        delegation_id=delegation_id,
        trace_id=trace_id,
    )
    ver = build_signature_verification_expectation(
        env, expected_signature_ref=expected_signature_ref
    )
    return AgentActionSignaturePlan(envelope=env, verification=ver)
