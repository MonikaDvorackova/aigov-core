"""Static checks on workflow YAML (text-based; no PyYAML dependency)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _workflow_job_declaration_body(lines: list[str], job_key: str) -> str:
    start = lines.index(f"  {job_key}:")
    parts: list[str] = []
    for j in range(start + 1, len(lines)):
        line = lines[j]
        if (
            len(line) >= 2
            and line.startswith("  ")
            and not line.startswith("    ")
            and line.rstrip().endswith(":")
        ):
            break
        parts.append(line)
    return "\n".join(parts)


def test_govai_compliance_gate_allows_same_repo_pr_and_workspace_cli() -> None:
    p = REPO_ROOT / ".github/workflows/compliance.yml"
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    segment = _workflow_job_declaration_body(lines, "govai-compliance-gate")
    assert "github.event_name != 'pull_request' && github.ref == 'refs/heads/main'" not in segment
    assert "python -m pip install -e ./python" in segment
    assert "github.event.pull_request.head.repo.full_name" in segment
    assert "github.repository" in segment


def test_govai_compliance_gate_not_skipped_for_all_pull_requests() -> None:
    p = REPO_ROOT / ".github/workflows/compliance.yml"
    text = p.read_text(encoding="utf-8")
    assert "if: ${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main'" not in text


def test_govai_ci_waits_on_ready() -> None:
    p = REPO_ROOT / ".github/workflows/govai-ci.yml"
    t = p.read_text(encoding="utf-8")
    assert "8088/ready" in t
    assert "Wait for audit readiness" in t


def test_compliance_workflow_uses_ready_for_local_audit() -> None:
    p = REPO_ROOT / ".github/workflows/compliance.yml"
    t = p.read_text(encoding="utf-8")
    assert "expected HTTP 200 from GET /ready" in t or '"/ready"' in t


def test_workflows_treat_duplicate_event_id_409_via_shared_helper() -> None:
    for rel in (".github/workflows/compliance.yml", ".github/workflows/govai-smoke.yml"):
        t = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "is_duplicate_event_id_idempotent_acceptance" in t
        assert "idempotent duplicate accepted" in t
