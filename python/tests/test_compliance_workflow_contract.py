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


def test_govai_compliance_gate_includes_in_repo_pull_request_path() -> None:
    lines = _compliance_yml().splitlines()
    block = _workflow_job_declaration_body(lines, "govai-compliance-gate")
    assert 'ev="${{ github.event_name }}"' in block
    assert '[ "${ev}" = "pull_request" ]' in block
    assert "github.event.pull_request.head.repo.full_name" in block
    assert "github.repository" in block


def test_evidence_pack_waits_on_ready_not_status() -> None:
    text = _compliance_yml()
    idx = text.index("  evidence_pack:")
    block = text[idx : idx + 12000]
    assert "${AUDIT_URL%/}/ready" in block or '"/ready"' in block or "/ready" in block
    assert "${AUDIT_URL%/}/status" not in block


def test_evidence_pack_prebuilds_audit_binary_before_ready_loop() -> None:
    """Avoid racing GET /ready against a cold `cargo run` compile (PR #237 evidence_pack failure)."""
    text = _compliance_yml()
    idx = text.index("  evidence_pack:")
    block = text[idx : idx + 14000]
    assert "cargo build --locked --bin aigov_audit" in block
    assert "rust/target/debug/aigov_audit" in block


def test_hosted_compliance_gate_uses_workspace_install_not_pypi_pin() -> None:
    lines = _compliance_yml().splitlines()
    block = _workflow_job_declaration_body(lines, "govai-compliance-gate")
    assert "pip install -e ./python" in block
    assert 'aigov-py==0.2.1' not in block


def test_hosted_gate_artifact_bound_submit_and_verify() -> None:
    lines = _compliance_yml().splitlines()
    block = _workflow_job_declaration_body(lines, "govai-compliance-gate")
    assert "submit-evidence-pack" in block
    assert "verify-evidence-pack" in block
    assert "evidence_digest_manifest.json" in block


def test_workflow_still_uses_editable_dev_for_repo_local_ci_build() -> None:
    text = _compliance_yml()
    assert 'pip install -e ".[dev]"' in text


def test_govai_emit_run_id_appends_github_workflow_identity() -> None:
    """Hosted ledger run_id must differ per workflow run while basename PR rules stay strict."""
    text = _compliance_yml()
    assert 'echo "run_id=${only}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"' in text
    assert 'RUN_ID="${EMITTED_RUN_ID}"' in text
    assert 'cp "docs/reports/${REPORT_BASENAME}.md" "docs/reports/${RUN_ID}.md"' in text


def test_evidence_pack_job_exports_govai_auth_for_bundle_fetch() -> None:
    text = _compliance_yml()
    idx = text.index("  evidence_pack:")
    block = text[idx : idx + 9000]
    assert "GOVAI_API_KEY: ci-test-api-key" in block
    assert "GOVAI_AUDIT_BASE_URL: http://127.0.0.1:8088" in block
    assert 'AIGOV_COMPLIANCE_FETCH_STRICT: "1"' in block


def test_evidence_pack_enforces_non_fallback_before_and_after_evidence_pack() -> None:
    text = _compliance_yml()
    assert "enforce_evidence_bundle_for_upload" in text
    assert "python -m aigov_py.assert_ci_evidence_bundle" in text
    assert text.count("enforce_evidence_bundle_for_upload") >= 4


def test_makefile_ensure_evidence_strict_disables_ci_fallback() -> None:
    makefile = (_repo_root() / "Makefile").read_text(encoding="utf-8")
    assert "AIGOV_COMPLIANCE_FETCH_STRICT" in makefile
    assert "no ci_fallback" in makefile


def test_release_promotion_evidence_path_posts_ai_discovery() -> None:
    text = _compliance_yml()
    rp = text.index('if [[ "${EMITTED_RUN_ID}" == release-promotion-* ]]; then')
    seg = text[rp : rp + 2200]
    assert 'post_local_ev "ai_discovery_reported"' in seg
    assert "enforce_evidence_bundle_for_upload" in seg
    assert "make evidence_pack RUN_ID=" in seg


def test_release_promotion_emit_run_id_stays_unique_per_workflow_run() -> None:
    lines = _compliance_yml().splitlines()
    body = _workflow_job_declaration_body(lines, "evidence_pack")
    assert "echo \"run_id=release-promotion-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}\"" in body


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
