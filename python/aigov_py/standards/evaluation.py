from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from aigov_py.standards import common
from aigov_py.standards.capability_policy import validate_capability_policy_document
from aigov_py.standards.delegation_graph import validate_delegation_graph_document
from aigov_py.standards.decision_trace import validate_governance_decision_trace_document
from aigov_py.standards.evidence_pack import validate_governance_evidence_pack_document
from aigov_py.standards.policy_module import validate_governance_policy_module_document
from aigov_py.standards.trace_verification import validate_trace_verification_plan_document

_CORPUS: tuple[tuple[str, Callable[[Any], Any]], ...] = (
    ("capability_policy.valid.json", validate_capability_policy_document),
    ("delegation_graph.valid.json", validate_delegation_graph_document),
    ("trace_verification_plan.valid.json", validate_trace_verification_plan_document),
    ("governance_evidence_pack.valid.json", validate_governance_evidence_pack_document),
    ("evidence-pack.valid.json", validate_governance_evidence_pack_document),
    ("policy-module.valid.json", validate_governance_policy_module_document),
    ("decision-trace.valid.json", validate_governance_decision_trace_document),
)


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[2]


def evaluate_standards_corpus(*, repo_root: Path | None = None) -> dict[str, Any]:
    """
    Deterministic evaluation over ``examples/standards/*.valid.json``.

    Does not perform network I/O. Uses the same validators as the CLI.
    """
    root = _repo_root(repo_root)
    examples = root / "examples" / "standards"
    validators: list[str] = []
    per_doc: list[dict[str, Any]] = []
    total = 0
    valid = 0
    invalid = 0
    issue_total = 0
    digest_stable = True

    for fname, validate_fn in _CORPUS:
        validators.append(validate_fn.__name__)
        p = examples / fname
        total += 1
        entry: dict[str, Any] = {"file": fname, "validator": validate_fn.__name__}
        try:
            data = common.load_standard_document(p)
        except common.StandardsLoadError as e:
            invalid += 1
            digest_stable = False
            issue_total += 1
            entry.update({"ok": False, "load_error": e.code, "message": e.message})
            per_doc.append(entry)
            continue
        if not isinstance(data, dict):
            invalid += 1
            digest_stable = False
            issue_total += 1
            entry.update({"ok": False, "load_error": "malformed_root"})
            per_doc.append(entry)
            continue

        r1 = validate_fn(data)
        r2 = validate_fn(data)
        stable = r1.digest == r2.digest and r1.ok == r2.ok
        if not stable:
            digest_stable = False
        issues = len(r1.issues)
        issue_total += issues
        ok = bool(r1.ok)
        if ok:
            valid += 1
        else:
            invalid += 1
        entry.update(
            {
                "ok": ok,
                "digest": r1.digest,
                "digest_repeat_match": stable,
                "issue_count": issues,
            }
        )
        per_doc.append(entry)

    verdict = "VALID" if invalid == 0 and digest_stable else "INVALID"
    return {
        "schema_version": "govai.standards.evaluation.v1",
        "total_documents": total,
        "valid_documents": valid,
        "invalid_documents": invalid,
        "validators": validators,
        "digest_stability": digest_stable,
        "issue_count": issue_total,
        "verdict": verdict,
        "documents": per_doc,
    }


def evaluation_json(*, repo_root: Path | None = None) -> str:
    return common.canonical_json(evaluate_standards_corpus(repo_root=repo_root))
