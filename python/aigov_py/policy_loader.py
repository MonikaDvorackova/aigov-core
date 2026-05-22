from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def load_policy_required_evidence(policy_path: str | Path) -> set[str]:
    """
    Load a policy module YAML and return the flat required_evidence set.

    This is a static mapping helper:
    - No runtime logic
    - Deterministic: YAML → union(required_evidence)
    - No GovAI engine integration (utility only)
    """

    # Backward-compatible helper: keep existing name/behavior, but implement via
    # the structured PolicyModule helpers.
    policy = load_policy_module(policy_path)
    return required_evidence_from_policy(policy)


@dataclass(frozen=True)
class PolicyRequirement:
    code: str
    required_evidence: tuple[str, ...]


@dataclass(frozen=True)
class PolicyIdentity:
    id: str
    name: str
    version: str


@dataclass(frozen=True)
class PolicyModule:
    policy: PolicyIdentity
    requirements: tuple[PolicyRequirement, ...]


def _require_nonempty_str(obj: dict[str, Any], key: str, *, where: str) -> str:
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{where}.{key} must be a non-empty string")
    return v.strip()


def _require_nonempty_list(obj: dict[str, Any], key: str, *, where: str) -> list[Any]:
    v = obj.get(key)
    if not isinstance(v, list) or not v:
        raise ValueError(f"{where}.{key} must be a non-empty list")
    return v


def load_policy_module(path: str | Path) -> PolicyModule:
    """
    Load and validate a customer policy module YAML.

    Policy modules must compile into a flat deterministic required_evidence set.
    """
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("policy module must be a YAML object at the top level")

    policy_raw = raw.get("policy")
    if not isinstance(policy_raw, dict):
        raise ValueError("policy module missing required object: policy")

    ident = PolicyIdentity(
        id=_require_nonempty_str(policy_raw, "id", where="policy"),
        name=_require_nonempty_str(policy_raw, "name", where="policy"),
        version=_require_nonempty_str(policy_raw, "version", where="policy"),
    )

    reqs_raw = raw.get("requirements")
    if not isinstance(reqs_raw, list) or not reqs_raw:
        raise ValueError("policy module requirements must be a non-empty list")

    reqs: list[PolicyRequirement] = []
    for i, r in enumerate(reqs_raw):
        if not isinstance(r, dict):
            raise ValueError(f"requirements[{i}] must be an object")
        code = _require_nonempty_str(r, "code", where=f"requirements[{i}]")
        ev_raw = _require_nonempty_list(r, "required_evidence", where=f"requirements[{i}]")
        ev: list[str] = []
        for j, item in enumerate(ev_raw):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(
                    f"requirements[{i}].required_evidence[{j}] must be a non-empty string"
                )
            ev.append(item.strip())
        reqs.append(PolicyRequirement(code=code, required_evidence=tuple(ev)))

    return PolicyModule(policy=ident, requirements=tuple(reqs))


def required_evidence_from_policy(policy: PolicyModule) -> set[str]:
    """
    Compile a policy module into a flat deterministic required_evidence set.
    """
    out: set[str] = set()
    for req in policy.requirements:
        for item in req.required_evidence:
            s = str(item or "").strip()
            if s:
                out.add(s)
    return out


def policy_identity(policy: PolicyModule) -> dict[str, str]:
    return {"id": policy.policy.id, "name": policy.policy.name, "version": policy.policy.version}

