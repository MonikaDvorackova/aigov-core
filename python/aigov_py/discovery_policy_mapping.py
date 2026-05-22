from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class DiscoverySignals:
    """
    Stable, deterministic inputs for discovery → required_evidence mapping.

    This is intentionally small and boolean-ish; all signals are derived via deterministic
    heuristics (no scoring, no ML, no randomness).
    """

    ai_detected: bool = False
    llm_used: bool = False
    user_facing: bool = False
    pii_possible: bool = False

    # From scan_repo() model_types array; callers may set explicitly.
    model_types: tuple[str, ...] = ()


def _as_bool(d: dict[str, Any], key: str) -> bool:
    return bool(d.get(key, False))


def _as_str_tuple(d: dict[str, Any], key: str) -> tuple[str, ...]:
    raw = d.get(key)
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for x in raw:
        s = str(x or "").strip()
        if not s:
            continue
        if s not in seen:
            seen.add(s)
            out.append(s)
    return tuple(out)


def coerce_discovery_signals(scan: Any) -> DiscoverySignals:
    """
    Accepts either the `scan_repo()` dict or any mapping-like object.
    Unknown keys are ignored; missing keys default to False.
    """
    if isinstance(scan, dict):
        return DiscoverySignals(
            ai_detected=_as_bool(scan, "ai_detected"),
            llm_used=_as_bool(scan, "llm_used"),
            user_facing=_as_bool(scan, "user_facing"),
            pii_possible=_as_bool(scan, "pii_possible"),
            model_types=_as_str_tuple(scan, "model_types"),
        )
    # Best-effort attribute access
    d = {
        "ai_detected": bool(getattr(scan, "ai_detected", False)),
        "llm_used": bool(getattr(scan, "llm_used", False)),
        "user_facing": bool(getattr(scan, "user_facing", False)),
        "pii_possible": bool(getattr(scan, "pii_possible", False)),
        "model_types": getattr(scan, "model_types", ()),
    }
    if not isinstance(d["model_types"], (list, tuple)):
        d["model_types"] = ()
    return coerce_discovery_signals(d)


def discovery_required_evidence_additions(signals: DiscoverySignals) -> set[str]:
    """
    Deterministic mapping: discovery signals → required_evidence codes.

    IMPORTANT:
    - This does NOT replace policy modules.
    - It only augments (set union) the flat required_evidence set upstream.
    """
    req: set[str] = set()

    # LLM usage implies an evaluation gate + usage policy.
    if signals.llm_used:
        req.update({"evaluation_reported", "usage_policy_defined"})

    # User-facing exposure implies human approval.
    if signals.user_facing:
        req.add("human_approved")

    # PII implies privacy review.
    if signals.pii_possible:
        req.add("privacy_review_completed")

    # Training / model lifecycle is *not* inferred here (no dynamic analysis).
    # However, if the project declares classifier/embedding usage, we require evaluation registration.
    model_types = {str(x).strip().lower() for x in (signals.model_types or ()) if str(x or "").strip()}
    if "classifier" in model_types or "embedding" in model_types:
        req.add("evaluation_reported")

    return req


def triggered_by_discovery(signals: DiscoverySignals) -> list[str]:
    """
    Return stable, deterministic trigger labels for summary/reporting.
    Only includes signals that are true and that map to at least one requirement.
    """
    mapping = {
        "llm_used": bool(signals.llm_used),
        "user_facing": bool(signals.user_facing),
        "pii_possible": bool(signals.pii_possible),
    }
    out = [k for k, v in mapping.items() if v]
    out.sort()
    return out


def merge_required_evidence(
    policy_required_evidence: Iterable[str],
    discovery_signals: DiscoverySignals,
) -> set[str]:
    """
    Convenience helper: policy + discovery-driven → flat required_evidence set.
    """
    merged: set[str] = {str(x).strip() for x in policy_required_evidence if str(x or "").strip()}
    merged.update(discovery_required_evidence_additions(discovery_signals))
    return merged


def merge_policy_and_discovery_required_evidence(
    policy_required_evidence: Iterable[str],
    discovery_required_evidence: Iterable[str],
) -> set[str]:
    """
    Deterministic union helper (compile-only).

    This is intentionally separate from runtime discovery signal processing so callers can
    union two already-compiled evidence lists without introducing dynamic policy behavior.
    """
    merged: set[str] = {str(x).strip() for x in policy_required_evidence if str(x or "").strip()}
    merged.update({str(x).strip() for x in discovery_required_evidence if str(x or "").strip()})
    return merged

