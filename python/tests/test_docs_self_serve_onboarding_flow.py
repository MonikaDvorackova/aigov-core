from __future__ import annotations

import re
from pathlib import Path


def _read_canonical_onboarding_doc() -> str:
    # tests run with cwd "python/" via: cd python && python -m pytest -q
    repo_root = Path(__file__).resolve().parents[2]
    doc_path = repo_root / "docs" / "customer-onboarding-10min.md"
    return doc_path.read_text(encoding="utf-8")


def test_canonical_onboarding_doc_includes_supported_evidence_pack_flow() -> None:
    doc = _read_canonical_onboarding_doc()

    assert "govai evidence-pack init" in doc
    assert "govai submit-evidence-pack" in doc
    assert "govai verify-evidence-pack --require-export" in doc
    assert "govai check" in doc


def test_canonical_onboarding_doc_reuses_same_run_id_across_steps() -> None:
    doc = _read_canonical_onboarding_doc()

    # Require a single obvious variable name and ensure it is used across init/submit/verify/check.
    assert "export RUN_ID=" in doc
    for cmd in [
        r"govai\s+evidence-pack\s+init\b.*--run-id\s+\"\$RUN_ID\"",
        r"govai\s+submit-evidence-pack\b.*--run-id\s+\"\$RUN_ID\"",
        r"govai\s+verify-evidence-pack\b.*--run-id\s+\"\$RUN_ID\"",
        r"govai\s+check\b.*--run-id\s+\"\$RUN_ID\"",
    ]:
        assert re.search(cmd, doc), f"missing RUN_ID usage in: {cmd}"


def test_canonical_onboarding_doc_has_required_troubleshooting_terms() -> None:
    doc = _read_canonical_onboarding_doc()

    required_terms = [
        "APPEND_ERROR",
        "RUN_NOT_FOUND",
        "digest mismatch",
        "BLOCKED",
    ]
    for term in required_terms:
        assert term in doc, f"missing troubleshooting term: {term}"

