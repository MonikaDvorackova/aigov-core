#!/usr/bin/env python3
"""Validate auditability-failures benchmark metadata (stdlib only; no network).

Exits 0 when scenarios.json and expected-results.json are internally consistent.
This is a documentation and teaching harness — not a second verdict engine.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_SCENARIO_CATEGORIES = frozenset(
    {
        "broken_digest_continuity",
        "duplicate_event_id",
        "incomplete_evidence_pack",
        "invalid_evaluation",
        "missing_approval",
        "missing_audit_context",
        "missing_evidence",
        "tenant_isolation_spoofing",
    }
)


def _die(msg: str) -> None:
    print(f"auditability-failures benchmark: FAIL: {msg}", file=sys.stderr)


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"{path}: {e}") from e


def main() -> int:
    here = Path(__file__).resolve().parent
    scenarios_path = here / "scenarios.json"
    expected_path = here / "expected-results.json"

    try:
        scenarios_doc = _load_json(scenarios_path)
        expected_doc = _load_json(expected_path)
    except ValueError as e:
        _die(str(e))
        return 2

    if not isinstance(scenarios_doc, dict):
        _die("scenarios.json root must be an object")
        return 2
    if scenarios_doc.get("schema_version") != 1:
        _die("scenarios.json: unsupported schema_version")
        return 2
    if scenarios_doc.get("suite_id") != "auditability-failures":
        _die("scenarios.json: suite_id mismatch")
        return 2

    scenarios = scenarios_doc.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        _die("scenarios.json: scenarios must be a non-empty array")
        return 2

    seen: set[str] = set()
    categories: set[str] = set()
    for i, item in enumerate(scenarios):
        if not isinstance(item, dict):
            _die(f"scenarios[{i}] must be an object")
            return 2
        sid = item.get("id")
        title = item.get("title")
        desc = item.get("description")
        cat = item.get("category")
        sigs = item.get("signals")
        if not isinstance(sid, str) or not sid.strip():
            _die(f"scenarios[{i}].id invalid")
            return 2
        if sid in seen:
            _die(f"duplicate scenario id: {sid!r}")
            return 2
        seen.add(sid)
        if not isinstance(title, str) or not title.strip():
            _die(f"scenario {sid!r}: title invalid")
            return 2
        if not isinstance(desc, str) or not desc.strip():
            _die(f"scenario {sid!r}: description invalid")
            return 2
        if not isinstance(cat, str) or cat != sid:
            _die(f"scenario {sid!r}: category must equal id for this suite")
            return 2
        categories.add(cat)
        if not isinstance(sigs, list) or not sigs or not all(isinstance(s, str) and s.strip() for s in sigs):
            _die(f"scenario {sid!r}: signals must be a non-empty array of strings")
            return 2

    if categories != REQUIRED_SCENARIO_CATEGORIES:
        missing = sorted(REQUIRED_SCENARIO_CATEGORIES - categories)
        extra = sorted(categories - REQUIRED_SCENARIO_CATEGORIES)
        _die(f"scenario category set mismatch; missing={missing!r} extra={extra!r}")
        return 2

    if not isinstance(expected_doc, dict):
        _die("expected-results.json root must be an object")
        return 2
    if expected_doc.get("schema_version") != 1:
        _die("expected-results.json: unsupported schema_version")
        return 2
    if expected_doc.get("suite_id") != "auditability-failures":
        _die("expected-results.json: suite_id mismatch")
        return 2

    expected = expected_doc.get("expected")
    if not isinstance(expected, dict) or not expected:
        _die("expected-results.json: expected must be a non-empty object")
        return 2

    allowed_signals = frozenset({"VALID", "INVALID", "BLOCKED"})
    for sid in sorted(REQUIRED_SCENARIO_CATEGORIES):
        row = expected.get(sid)
        if not isinstance(row, dict):
            _die(f"expected[{sid!r}] missing or not an object")
            return 2
        ps = row.get("primary_signal")
        rat = row.get("rationale")
        if ps not in allowed_signals:
            _die(f"expected[{sid!r}].primary_signal must be one of {sorted(allowed_signals)}")
            return 2
        if not isinstance(rat, str) or not rat.strip():
            _die(f"expected[{sid!r}].rationale invalid")
            return 2

    unexpected_keys = set(expected.keys()) - set(REQUIRED_SCENARIO_CATEGORIES)
    if unexpected_keys:
        _die(f"expected-results.json has unknown keys: {sorted(unexpected_keys)!r}")
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "scenario_count": len(scenarios),
                "suite_id": "auditability-failures",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
