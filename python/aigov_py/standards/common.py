from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Hard cap to reduce parser / memory abuse on untrusted paths (fail-closed for tooling).
MAX_STANDARDS_DOCUMENT_BYTES = 4 * 1024 * 1024


_SCHEMA_KIND_PREFIXES: tuple[tuple[str, str], ...] = (
    ("govai.standards.capability_policy.", "capability-policy"),
    ("govai.standards.delegation_graph.", "delegation-graph"),
    ("govai.standards.trace_verification_plan.", "trace-verification-plan"),
    ("govai.standards.governance_evidence_pack.", "evidence-pack"),
    ("govai.standards.governance_policy_module.", "policy-module"),
    ("govai.standards.governance_decision_trace.", "decision-trace"),
)


def infer_standards_document_kind(data: Mapping[str, Any]) -> str | None:
    """
    Best-effort kind inference for ``wrong_standard_kind`` detection.

    Returns one of: capability-policy, delegation-graph, trace-verification-plan, evidence-pack,
    policy-module, decision-trace, or None if unknown.
    """
    sv = data.get("schema_version")
    if isinstance(sv, str):
        s = sv.strip()
        for prefix, kind in _SCHEMA_KIND_PREFIXES:
            if s.startswith(prefix):
                return kind
    if isinstance(data.get("capabilities"), list) and "policy_id" in data:
        return "capability-policy"
    if isinstance(data.get("nodes"), list) and isinstance(data.get("edges"), list):
        return "delegation-graph"
    if isinstance(data.get("requirements"), list) and isinstance(data.get("findings"), list):
        return "trace-verification-plan"
    if isinstance(data.get("artifacts"), list) and isinstance(data.get("digest_manifest"), Mapping):
        return "evidence-pack"
    pol = data.get("policy")
    if (
        isinstance(pol, Mapping)
        and isinstance(data.get("requirements"), list)
        and "capabilities" not in data
        and {"id", "name", "version"} <= set(pol.keys())
    ):
        return "policy-module"
    if isinstance(data.get("gate_inputs"), Mapping) and "recorded_gate_verdict" in data:
        return "decision-trace"
    return None


class StandardsLoadError(Exception):
    """Expected user or filesystem error while loading a standards document."""

    def __init__(self, code: str, message: str, path: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code}: {self.message}"

# Phase 5 explicit non-goal: do not ingest or store raw text/prompt payloads in standards docs.
_RAW_FIELD_NAMES = frozenset(
    {
        "prompt",
        "content",
        "raw_payload",
        "input_text",
        "output_text",
        "message_body",
    }
)


def canonical_json(value: Any) -> str:
    """
    Deterministic JSON serialization for canonical digest preimages.

    - UTF-8 safe (ensure_ascii=False)
    - sorted keys
    - no whitespace
    """
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_digest(value: Any) -> str:
    """Return a sha256 digest token over canonical JSON: ``sha256:<64 hex>``."""
    hx = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{hx}"


def validate_digest_token(value: str) -> bool:
    """True for exactly 64 hex digits or ``sha256:<64 hex>`` (case-insensitive hex)."""
    try:
        _ = normalize_digest_token(value)
        return True
    except ValueError:
        return False


def normalize_digest_token(value: str) -> str:
    """
    Normalize digest token to ``sha256:<64 lowercase hex>``.

    Accepts either 64 hex digits or ``sha256:<64 hex>`` (hex case-insensitive).
    """
    s = (value or "").strip()
    if not s:
        raise ValueError("digest token must be non-empty")
    body = s[7:] if s.lower().startswith("sha256:") else s
    hx = body.strip().lower()
    if not _HEX64.fullmatch(hx):
        raise ValueError("digest token must be 64 hex or sha256:<64 hex>")
    return f"sha256:{hx}"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str = ""


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    issues: tuple[ValidationIssue, ...] = ()
    digest: str | None = None

    def sorted_issues(self) -> tuple[ValidationIssue, ...]:
        return tuple(sorted(self.issues, key=lambda i: (i.path, i.code, i.message)))


def _iter_mapping_items(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for k, v in value.items():
            yield str(k), v


def _iter_sequence_items(value: Any) -> Iterable[tuple[int, Any]]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for i, v in enumerate(value):
            yield i, v


def _path_join(parent: str, child: str) -> str:
    if not parent:
        return child
    if not child:
        return parent
    return f"{parent}.{child}"


def _path_index(parent: str, idx: int) -> str:
    if not parent:
        return f"[{idx}]"
    return f"{parent}[{idx}]"


def find_raw_content_fields(value: Any, *, path: str = "") -> tuple[ValidationIssue, ...]:
    """
    Detect raw content fields anywhere in a nested document.

    We reject these field names *by key*, regardless of their value type.
    """
    issues: list[ValidationIssue] = []

    if isinstance(value, Mapping):
        for k, v in _iter_mapping_items(value):
            key = k.strip()
            p = _path_join(path, key)
            if key in _RAW_FIELD_NAMES:
                issues.append(
                    ValidationIssue(
                        code="raw_field_rejected",
                        message=f"raw content field '{key}' is not allowed in standards documents",
                        path=p,
                    )
                )
            issues.extend(find_raw_content_fields(v, path=p))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for i, v in _iter_sequence_items(value):
            issues.extend(find_raw_content_fields(v, path=_path_index(path, i)))

    return tuple(issues)


def load_standard_document(path: str | Path) -> Any:
    """
    Load a standards document from JSON (required) or YAML (optional).

    JSON is always supported. YAML is supported only when PyYAML is available.

    Raises:
        StandardsLoadError: missing file, permission, size limit, parse errors, or unsupported type.
    """
    p = Path(path).expanduser()
    try:
        p = p.resolve()
    except OSError as e:
        raise StandardsLoadError("path_resolution_failed", str(e), str(path)) from e

    if not p.exists():
        raise StandardsLoadError("file_not_found", "standards document path does not exist", str(p))
    if not p.is_file():
        raise StandardsLoadError("not_a_file", "path is not a regular file", str(p))
    try:
        size = p.stat().st_size
    except OSError as e:
        raise StandardsLoadError("stat_failed", str(e), str(p)) from e
    if size > MAX_STANDARDS_DOCUMENT_BYTES:
        raise StandardsLoadError(
            "file_too_large",
            f"document exceeds max size ({MAX_STANDARDS_DOCUMENT_BYTES} bytes)",
            str(p),
        )

    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        raise StandardsLoadError("read_failed", str(e), str(p)) from e

    suffix = p.suffix.lower()

    if suffix in {".json"}:
        stripped = text.strip()
        if not stripped or not ((stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]"))):
            raise StandardsLoadError("invalid_json", "expected JSON object", str(p))
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as e:
            raise StandardsLoadError("invalid_json", str(e), str(p)) from e

    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as e:  # pragma: no cover
            raise StandardsLoadError("yaml_unavailable", "YAML support requires PyYAML", str(p)) from e
        try:
            out = yaml.safe_load(text)
        except Exception as e:
            raise StandardsLoadError("invalid_yaml", str(e), str(p)) from e
        return out

    if suffix and suffix not in {".json", ".yaml", ".yml"}:
        raise StandardsLoadError(
            "unsupported_format",
            f"unsupported file extension {suffix!r} (use .json, .yaml, or .yml)",
            str(p),
        )

    # No extension: attempt JSON for deterministic local tooling.
    stripped = text.strip()
    if not stripped or not ((stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]"))):
        raise StandardsLoadError("invalid_json", "expected JSON object", str(p))
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as e:
        raise StandardsLoadError("invalid_json", str(e), str(p)) from e


def _require_non_empty_str(
    issues: list[ValidationIssue],
    *,
    value: Any,
    path: str,
    code: str,
    message: str,
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        issues.append(ValidationIssue(code=code, message=message, path=path))
        return None
    return value.strip()


def _require_list(
    issues: list[ValidationIssue],
    *,
    value: Any,
    path: str,
    code: str,
    message: str,
) -> list[Any] | None:
    if not isinstance(value, list):
        issues.append(ValidationIssue(code=code, message=message, path=path))
        return None
    return value

