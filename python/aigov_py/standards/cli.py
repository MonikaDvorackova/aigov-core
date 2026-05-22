from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

from aigov_py import cli_exit
from aigov_py.standards import common
from aigov_py.standards.capability_policy import validate_capability_policy_document
from aigov_py.standards.delegation_graph import validate_delegation_graph_document
from aigov_py.standards.evidence_pack import validate_governance_evidence_pack_document
from aigov_py.standards.trace_verification import validate_trace_verification_plan_document

# Exit codes for standards tooling (deterministic; no tracebacks on stdout for expected errors).
EXIT_VALIDATION_FAILED = cli_exit.EX_INVALID  # 2 — document parsed but fails schema rules
EXIT_LOAD_OR_INPUT = cli_exit.EX_USAGE  # 4 — missing file, parse error, malformed root, unknown digest kind


def _emit_result(obj: dict[str, Any]) -> None:
    sys.stdout.write(common.canonical_json(obj) + "\n")


def _emit_load_error(err: common.StandardsLoadError) -> None:
    _emit_result(
        {
            "ok": False,
            "error": err.code,
            "message": err.message,
            "path": err.path,
        }
    )


def _load_document(path: str) -> tuple[Any | None, common.StandardsLoadError | None]:
    try:
        data = common.load_standard_document(Path(path))
    except common.StandardsLoadError as e:
        return None, e
    if not isinstance(data, dict):
        return None, common.StandardsLoadError(
            "malformed_root",
            "standards document root must be a JSON object (mapping)",
            str(path),
        )
    return data, None


def _ensure_expected_kind(data: Mapping[str, Any], *, expected: str, path: str) -> int | None:
    """
    When the document shape is clearly another standard, fail before deep validation.

    Returns an exit code when the check fails, else None.
    """
    inferred = common.infer_standards_document_kind(data)
    if inferred is not None and inferred != expected:
        _emit_result(
            {
                "ok": False,
                "error": "wrong_standard_kind",
                "message": (
                    f"document appears to be {inferred!r}; this command validates {expected!r}"
                ),
                "path": path,
                "expected_kind": expected,
                "inferred_kind": inferred,
            }
        )
        return EXIT_LOAD_OR_INPUT
    return None


def _cmd_validate_capability_policy(path: str) -> int:
    data, err = _load_document(path)
    if err:
        _emit_load_error(err)
        return EXIT_LOAD_OR_INPUT
    bad = _ensure_expected_kind(data, expected="capability-policy", path=path)
    if bad is not None:
        return bad
    res = validate_capability_policy_document(data)
    _emit_result({"digest": res.digest, "issues": [i.__dict__ for i in res.sorted_issues()], "ok": res.ok})
    return cli_exit.EX_OK if res.ok else EXIT_VALIDATION_FAILED


def _cmd_validate_delegation_graph(path: str) -> int:
    data, err = _load_document(path)
    if err:
        _emit_load_error(err)
        return EXIT_LOAD_OR_INPUT
    bad = _ensure_expected_kind(data, expected="delegation-graph", path=path)
    if bad is not None:
        return bad
    res = validate_delegation_graph_document(data)
    _emit_result({"digest": res.digest, "issues": [i.__dict__ for i in res.sorted_issues()], "ok": res.ok})
    return cli_exit.EX_OK if res.ok else EXIT_VALIDATION_FAILED


def _cmd_validate_trace_verification_plan(path: str) -> int:
    data, err = _load_document(path)
    if err:
        _emit_load_error(err)
        return EXIT_LOAD_OR_INPUT
    bad = _ensure_expected_kind(data, expected="trace-verification-plan", path=path)
    if bad is not None:
        return bad
    res = validate_trace_verification_plan_document(data)
    _emit_result({"digest": res.digest, "issues": [i.__dict__ for i in res.sorted_issues()], "ok": res.ok})
    return cli_exit.EX_OK if res.ok else EXIT_VALIDATION_FAILED


def _cmd_validate_evidence_pack(path: str) -> int:
    data, err = _load_document(path)
    if err:
        _emit_load_error(err)
        return EXIT_LOAD_OR_INPUT
    bad = _ensure_expected_kind(data, expected="evidence-pack", path=path)
    if bad is not None:
        return bad
    res = validate_governance_evidence_pack_document(data)
    _emit_result({"digest": res.digest, "issues": [i.__dict__ for i in res.sorted_issues()], "ok": res.ok})
    return cli_exit.EX_OK if res.ok else EXIT_VALIDATION_FAILED


def _cmd_digest(kind: str, path: str) -> int:
    data, err = _load_document(path)
    if err:
        _emit_load_error(err)
        return EXIT_LOAD_OR_INPUT
    kind_l = kind.strip().lower()
    if kind_l == "capability-policy":
        res = validate_capability_policy_document(data)
    elif kind_l == "delegation-graph":
        res = validate_delegation_graph_document(data)
    elif kind_l in {"trace-verification-plan", "trace-verification"}:
        res = validate_trace_verification_plan_document(data)
    elif kind_l in {"evidence-pack", "governance-evidence-pack"}:
        res = validate_governance_evidence_pack_document(data)
    else:
        _emit_result(
            {
                "ok": False,
                "error": "unknown_kind",
                "message": "unsupported digest kind for standards documents",
                "kind": kind,
                "supported": [
                    "capability-policy",
                    "delegation-graph",
                    "trace-verification-plan",
                    "evidence-pack",
                ],
            }
        )
        return EXIT_LOAD_OR_INPUT
    _emit_result(
        {
            "digest": res.digest,
            "issues": [i.__dict__ for i in res.sorted_issues()],
            "kind": kind_l,
            "ok": res.ok,
        }
    )
    return cli_exit.EX_OK if res.ok else EXIT_VALIDATION_FAILED


_DISPATCH: dict[str, Callable[[str], int]] = {
    "validate-capability-policy": _cmd_validate_capability_policy,
    "validate-delegation-graph": _cmd_validate_delegation_graph,
    "validate-trace-verification-plan": _cmd_validate_trace_verification_plan,
    "validate-evidence-pack": _cmd_validate_evidence_pack,
}


def run_standards_command(cmd: str, path: str) -> int:
    """Run a single standards validate command; stdout is exactly one JSON object."""
    fn = _DISPATCH.get(cmd)
    if fn is None:
        _emit_result({"ok": False, "error": "unknown_command", "message": f"unknown standards command: {cmd!r}"})
        return EXIT_LOAD_OR_INPUT
    return int(fn(path))


def dispatch_govai_standards(args: Any) -> int:
    """Entry from ``govai standards …`` after argparse."""
    cmd = getattr(args, "standards_cmd", None) or ""
    path = str(getattr(args, "standards_path", "") or "").strip()
    if not path:
        _emit_result({"ok": False, "error": "missing_path", "message": "PATH argument is required"})
        return EXIT_LOAD_OR_INPUT
    return run_standards_command(cmd, path)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m aigov_py.standards.cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("validate-capability-policy", help="Validate Open Capability Policy JSON/YAML (stdout: one JSON object).")
    s1.add_argument("path", type=str)
    s1.set_defaults(func=lambda ns: _cmd_validate_capability_policy(ns.path))

    s2 = sub.add_parser("validate-delegation-graph", help="Validate Delegation Graph JSON/YAML (stdout: one JSON object).")
    s2.add_argument("path", type=str)
    s2.set_defaults(func=lambda ns: _cmd_validate_delegation_graph(ns.path))

    s3 = sub.add_parser("validate-trace-verification-plan", help="Validate Trace Verification Plan JSON/YAML (stdout: one JSON object).")
    s3.add_argument("path", type=str)
    s3.set_defaults(func=lambda ns: _cmd_validate_trace_verification_plan(ns.path))

    s4 = sub.add_parser("validate-evidence-pack", help="Validate Governance Evidence Pack JSON/YAML (stdout: one JSON object).")
    s4.add_argument("path", type=str)
    s4.set_defaults(func=lambda ns: _cmd_validate_evidence_pack(ns.path))

    s5 = sub.add_parser("digest", help="Compute canonical digest for a standards document (stdout: one JSON object).")
    s5.add_argument(
        "kind",
        type=str,
        help="capability-policy | delegation-graph | trace-verification-plan | evidence-pack",
    )
    s5.add_argument("path", type=str)
    s5.set_defaults(func=lambda ns: _cmd_digest(ns.kind, ns.path))

    return p


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    ns = p.parse_args(argv)
    func: Callable[[Any], int] = ns.func
    return int(func(ns))


if __name__ == "__main__":
    raise SystemExit(main())
