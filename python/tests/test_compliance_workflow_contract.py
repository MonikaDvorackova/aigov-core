"""Static contract checks for production compliance workflow (no YAML parser dependency)."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _compliance_yml() -> str:
    path = _repo_root() / ".github" / "workflows" / "compliance.yml"
    return path.read_text(encoding="utf-8")


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


def test_compliance_ci_does_not_define_hosted_govai_compliance_gate_job() -> None:
    """Hosted artefact gate (GOVAI_AUDIT_BASE_URL) lives in GovAI Platform, not Core CI."""
    text = _compliance_yml()
    assert "  govai-compliance-gate:" not in text
    assert "  govai-compliance-gate-fork-pr-block:" not in text


def test_evidence_pack_is_portable_offline_not_localhost_audit_server() -> None:
    text = _compliance_yml()
    idx = text.index("  evidence_pack:")
    block = text[idx : idx + 12000]
    assert "ci_portable_artifact_bundle.py" in block
    assert "verify-evidence-pack --portable-only" in block
    assert "portable_evidence_digest_once" in block
    assert "${AUDIT_URL%/}/ready" not in block
    assert "GOVAI_AUDIT_BASE_URL: http://127.0.0.1:8088" not in block
    assert "nohup" not in block
    assert "cargo build --locked --bin aigov_audit" not in block


def test_workflow_still_uses_editable_dev_for_repo_local_ci_build() -> None:
    text = _compliance_yml()
    assert 'pip install -e ".[dev]"' in text or 'pip install -e "./python[dev]"' in text


def test_govai_emit_run_id_appends_github_workflow_identity() -> None:
    """Portable CI run_id must differ per workflow run while basename PR rules stay strict."""
    text = _compliance_yml()
    assert 'echo "run_id=${only}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"' in text


def test_make_verify_does_not_start_postgres_for_portable_gate() -> None:
    lines = _compliance_yml().splitlines()
    block = _workflow_job_declaration_body(lines, "make_verify")
    assert "postgres:" not in block
    assert "DATABASE_URL" not in block


def test_makefile_ensure_evidence_strict_disables_ci_fallback() -> None:
    makefile = (_repo_root() / "Makefile").read_text(encoding="utf-8")
    assert "AIGOV_COMPLIANCE_FETCH_STRICT" in makefile
    assert "no ci_fallback" in makefile


def test_release_promotion_emit_run_id_stays_unique_per_workflow_run() -> None:
    lines = _compliance_yml().splitlines()
    body = _workflow_job_declaration_body(lines, "evidence_pack")
    assert "echo \"run_id=release-promotion-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}\"" in body


def test_dependabot_dependency_only_pr_skips_report_and_artifact_gate() -> None:
    """Lockfile-only Dependabot PRs must not require docs/reports or evidence_pack artefacts."""
    lines = _compliance_yml().splitlines()
    body = _workflow_job_declaration_body(lines, "changes")
    assert "dependency_only_dependabot" in body
    assert "is_dependency_manifest_path()" in body
    assert "is_dependabot_identity()" in body
    assert "app/dependabot" in body
    assert "rust/Cargo.lock" in body
    assert 'NEEDS_REPORT="false"' in body
    assert 'RUN_ARTIFACT_GATE="false"' in body


def test_compliance_pull_request_trigger_has_no_activity_types_filter() -> None:
    """A narrow `types:` list can skip runs so the PR head SHA never gets required check-runs."""
    text = _compliance_yml()
    on_block = text[text.index("on:") : text.index("\njobs:")]
    pr_segment = on_block.split("push:", 1)[0]
    assert "pull_request:" in pr_segment
    assert "types:" not in pr_segment


def test_required_jobs_always_run_so_branch_checks_resolve() -> None:
    """Branch protection waits forever when a required job is skipped.

    GitHub skips dependents when a needed job fails unless the dependent job uses
    `if: ${{ always() }}`. Using `always() && !cancelled()` can drop required jobs on
    cancelled/superseded runs so checks never attach to the head SHA.
    """
    lines = _compliance_yml().splitlines()
    required = (
        "reports_present",
        "report_gate",
        "report_content",
        "make_verify",
        "evidence_pack",
        "upload_evidence_packs",
    )
    for job_key in required:
        decl = _workflow_job_declaration_body(lines, job_key)
        got_name = False
        for raw in decl.splitlines():
            s = raw.strip()
            if s.startswith("name:"):
                got_name = s.split(":", 1)[1].strip() == job_key
                break
        assert got_name, f"{job_key} must set name: {job_key} as first-class required check title"
        assert "if: ${{ always() }}" in decl, job_key
        assert "!cancelled()" not in decl, job_key
        job_level_if_lines = [
            ln.rstrip() for ln in decl.splitlines() if ln.startswith("    if:") and not ln.startswith("      ")
        ]
        assert job_level_if_lines == ["    if: ${{ always() }}"], (job_key, job_level_if_lines)
        assert (
            "Branch protection prelude (upstream must succeed)" in decl
        ), job_key
