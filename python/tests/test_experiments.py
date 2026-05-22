from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from aigov_py.experiments import aggregate as agg_mod
from aigov_py.experiments import artifact_bound_enforcement as abe_mod
from aigov_py.experiments import controlled_failure_injection as cfi_mod
from aigov_py.experiments import real_world_ci_injection as rwci_mod
from aigov_py.experiments import real_world_ci_runner as rwci_runner_mod
from aigov_py.experiments import scenario_fields as sf_mod
from aigov_py.experiments.gate_model import (
    FAILURE_TAXONOMY,
    decision_gate_verdict_from_fields,
    expected_verdict_from_rubric,
    rubric_scenarios,
)


def test_cfi_deterministic_row_count() -> None:
    runs = cfi_mod.generate_runs()
    assert len(runs) == 2200
    assert runs[0].run_id == "cfi-0001"
    assert runs[-1].run_id == "cfi-2200"


def test_cfi_rubric_oracle_matches_gate_on_all_runs() -> None:
    for r in cfi_mod.generate_runs():
        assert r.expected_gate_verdict == expected_verdict_from_rubric(r.condition)
        assert r.gate_verdict == r.expected_gate_verdict
        assert r.gate_matches_rubric is True


def test_failure_taxonomy_is_injected_violation_only() -> None:
    assert len(FAILURE_TAXONOMY) == 17
    injected_names = {str(x["scenario_name"]) for x in rubric_scenarios() if x.get("injected_violation")}
    assert set(FAILURE_TAXONOMY) == injected_names


def test_scenario_constructors_satisfy_rubric() -> None:
    for row in rubric_scenarios():
        name = str(row["scenario_name"])
        fields = sf_mod.fields_for_scenario(name)
        got = decision_gate_verdict_from_fields(fields)
        assert got == str(row["expected_verdict"]), name


def test_cfi_csv_json_structure(tmp_path: Path) -> None:
    paths = cfi_mod.write_outputs(tmp_path)
    assert "csv" in paths and "json" in paths

    with open(paths["csv"], newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2200
    for row in rows:
        assert set(row.keys()) == {
            "run_id",
            "condition",
            "expected_label",
            "gate_label",
            "pipeline_baseline_label",
            "gate_matches_rubric",
        }
        assert row["expected_label"] == row["gate_label"]
        assert row["gate_matches_rubric"] == "True"

    payload = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert "runs" in payload and "summary" in payload
    assert len(payload["runs"]) == 2200
    assert "overall" in payload["summary"]


def test_cfi_reproducible_digest(tmp_path: Path) -> None:
    cfi_mod.write_outputs(tmp_path)
    a = hashlib.sha256(Path(tmp_path / "controlled_failure_injection.csv").read_bytes()).hexdigest()
    cfi_mod.write_outputs(tmp_path)
    b = hashlib.sha256(Path(tmp_path / "controlled_failure_injection.csv").read_bytes()).hexdigest()
    assert a == b


def test_abe_csv_columns(tmp_path: Path) -> None:
    abe_mod.write_outputs(tmp_path)
    with open(tmp_path / "artifact_bound_enforcement.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert {r["scenario"] for r in rows} == {
        "valid_correct_digest",
        "modified_event_body_digest_mismatch",
        "missing_artifact_bundle",
        "reordered_events_same_digest",
    }
    assert all(set(r.keys()) == {"scenario", "artifact_integrity", "gate_result"} for r in rows)


def test_rwci_dataset_static_file() -> None:
    repos = rwci_mod.load_repos()
    assert len(repos) >= 30
    for key in ("selection_reason", "ml_ai_relevance", "github_actions_present"):
        assert key in repos[0]


def test_rwci_runner_parse_verdict() -> None:
    assert rwci_runner_mod._parse_verdict_from_logs("step\nBLOCKED\n") == "BLOCKED"
    st, _, src = rwci_runner_mod._resolve_govai_verdict("RWCI_GOVAI_EXIT_CODE=3\n")
    assert st == "BLOCKED" and src == "exit_code_fallback"
    st2, _, src2 = rwci_runner_mod._resolve_govai_verdict("step\nBLOCKED\n")
    assert st2 == "BLOCKED" and src2 == "stdout"
    st3, _, src3 = rwci_runner_mod._resolve_govai_verdict("RWCI_GOVAI_VERDICT_LINE=INVALID\n")
    assert st3 == "INVALID" and src3 == "stdout"


def test_rwci_runner_govai_workflow_pinned_and_has_check() -> None:
    yml = rwci_runner_mod.govai_audit_workflow_yaml("missing_evidence")
    assert "GovAI Audit Injection" in yml
    assert "pip install aigov-py==0.2.1" in yml
    assert "govai check" in yml
    assert "emit_scenario.py" in yml
    assert "pip install aigov-py\n" not in yml


def test_rwci_runner_native_workflow_clean() -> None:
    yml = rwci_runner_mod.native_workflow_yaml("missing_evidence")
    assert "govai check" not in yml.lower()
    assert "GOVAI_API_KEY" not in yml
    assert "GOVAI_AUDIT_BASE_URL" not in yml
    assert "/evidence" not in yml


def test_rwci_pip_snippet_default_version(monkeypatch) -> None:
    monkeypatch.delenv("RWCI_GOVAI_PIP_SPEC", raising=False)
    monkeypatch.delenv("RWCI_AIGOV_GIT_COMMIT", raising=False)
    s = rwci_runner_mod.govai_pip_install_snippet()
    assert "aigov-py==0.2.1" in s


def test_rwci_pip_snippet_git_option(monkeypatch) -> None:
    monkeypatch.delenv("RWCI_GOVAI_PIP_SPEC", raising=False)
    monkeypatch.setenv("RWCI_AIGOV_GIT_COMMIT", "abcdef1234567890abcdef1234567890abcdef12")
    s = rwci_runner_mod.govai_pip_install_snippet()
    assert "git+https://github.com/MonikaDvorackova/aigov-compliance-engine.git@" in s
    assert "#subdirectory=python" in s


def test_rwci_csv_fieldnames() -> None:
    assert rwci_runner_mod.RWCI_CSV_FIELDNAMES == (
        "repo",
        "scenario",
        "baseline_type",
        "baseline_method",
        "native_ci_status",
        "govai_ci_status",
        "govai_status",
        "native_run_url",
        "govai_run_url",
        "native_log_path",
        "govai_log_path",
        "error",
    )


def test_rwci_summary_metrics_structure() -> None:
    rows = [
        {
            "scenario": "missing_evidence",
            "baseline_type": "native_ci_detected",
            "native_ci_status": "success",
            "govai_ci_status": "failure",
            "govai_status": "BLOCKED",
            "error": "",
            "govai_verdict_source": "stdout",
        },
        {
            "scenario": "missing_approval",
            "baseline_type": "fallback_minimal",
            "native_ci_status": "success",
            "govai_ci_status": "failure",
            "govai_status": "INVALID",
            "error": "",
            "govai_verdict_source": "stdout",
        },
    ]
    s = rwci_runner_mod._summarize(rows)
    assert s["completed_rows"] == 2
    assert "native_false_acceptance_rate_all" in s
    assert "native_false_acceptance_rate_native_ci_only" in s
    assert "native_false_acceptance_rate_fallback_only" in s
    assert "govai_detection_rate_all" in s
    assert "baseline_type_counts" in s and "scenario_counts" in s
    assert "metric_definitions" in s and "native_false_acceptance_rate" in s["metric_definitions"]
    assert s["verdict_source_counts"] == {"stdout": 2, "exit_code_fallback": 0}


def test_rwci_paper_table_and_case_studies(tmp_path: Path) -> None:
    art = tmp_path / "artifacts" / "govai"
    art.mkdir(parents=True)
    log_body = "preface\nBLOCKED\nRWCI_GOVAI_EXIT_CODE=3\n"
    (art / "r__missing_evidence.log.txt").write_text(log_body, encoding="utf-8")
    rows = [
        {
            "repo": "r",
            "scenario": "missing_evidence",
            "baseline_type": "native_ci_detected",
            "native_ci_status": "success",
            "govai_ci_status": "failure",
            "govai_status": "BLOCKED",
            "native_run_url": "https://native",
            "govai_run_url": "https://govai",
            "govai_log_path": "artifacts/govai/r__missing_evidence.log.txt",
            "error": "",
            "govai_verdict_source": "stdout",
        },
    ]
    cs = rwci_runner_mod._select_case_studies(rows, tmp_path)
    assert len(cs) == 1
    assert "BLOCKED" in cs[0]["log_excerpt"]
    assert cs[0]["repo"] == "r"
    completed_native = [rows[0]]
    p = rwci_runner_mod._write_paper_table_csv(tmp_path, completed_native)
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "missing_evidence,1.00,1.00" in text.replace("\n", " ")


def test_rwci_paper_json_summary_contract() -> None:
    row = {
        "scenario": "missing_evidence",
        "baseline_type": "native_ci_detected",
        "native_ci_status": "success",
        "govai_ci_status": "failure",
        "govai_status": "BLOCKED",
        "error": "",
        "govai_verdict_source": "stdout",
    }
    s = rwci_runner_mod._summarize([row])
    for k in (
        "metric_definitions",
        "verdict_source_counts",
        "verdict_source_stdout_ratio",
        "warnings",
    ):
        assert k in s, k
    assert s["verdict_source_counts"]["stdout"] == 1


def test_rwci_paper_consistency_smoke() -> None:
    summary = {"govai_detection_rate_native_ci_only": 0.99}
    vc = {"stdout": 10, "exit_code_fallback": 0}
    native_ok = [{"scenario": "missing_evidence"}] * 10
    cs = [{"repo": "x"}]
    assert rwci_runner_mod._paper_consistency_errors(
        summary=summary,
        case_studies=cs,
        native_only_completed=native_ok,
        verdict_counts=vc,
    ) == []
    bad = rwci_runner_mod._paper_consistency_errors(
        summary={"govai_detection_rate_native_ci_only": 0.5},
        case_studies=[],
        native_only_completed=native_ok[:3],
        verdict_counts={"stdout": 2, "exit_code_fallback": 8},
    )
    assert bad and any("0.95" in m for m in bad)
    assert any("case_studies" in m for m in bad)
    assert any("10" in m for m in bad)


def test_rwci_runner_no_offline_gate_import() -> None:
    src = Path(rwci_runner_mod.__file__).read_text(encoding="utf-8")
    assert "aigov_py.experiments.gate_model" not in src
    assert "from aigov_py.experiments import gate_model" not in src


def test_native_baseline_emits_method_and_type(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Makefile").write_text("test:\n\t@echo rwci_make_ok\n", encoding="utf-8")
    monkeypatch.setenv("SCENARIO", "missing_evidence")
    import subprocess
    import sys

    script = Path(rwci_runner_mod.__file__).resolve().parent / "scripts" / "native_baseline.py"
    p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=60)
    out = p.stdout + p.stderr
    assert "RWCI_BASELINE_METHOD=make_test" in out
    assert "RWCI_BASELINE_TYPE=native_ci_detected" in out


def _write_minimal_rwci_json(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "runs": [
            {
                "repo": "demo",
                "scenario": "missing_evidence",
                "baseline_type": "native_ci_detected",
                "baseline_method": "pytest",
                "native_ci_status": "success",
                "govai_ci_status": "failure",
                "govai_status": "BLOCKED",
            }
        ],
        "summary": {
            "total_rows": 1,
            "completed_rows": 1,
            "native_false_acceptance_rate_all": 1.0,
            "govai_detection_rate_all": 1.0,
            "note": "fixture",
        },
    }
    (out / "real_world_ci_injection.json").write_text(json.dumps(payload), encoding="utf-8")


def test_aggregate_merges(tmp_path: Path) -> None:
    cfi = tmp_path / "cfi"
    abe = tmp_path / "abe"
    rwci = tmp_path / "rwci"
    cfi_mod.write_outputs(cfi)
    abe_mod.write_outputs(abe)
    _write_minimal_rwci_json(rwci)

    out = tmp_path / "final"
    paths = agg_mod.aggregate(out_final_dir=out, cfi_dir=cfi, abe_dir=abe, rwci_dir=rwci)
    assert Path(paths["summary_json"]).is_file()
    assert Path(paths["table_csv"]).is_file()

    summary = json.loads(Path(paths["summary_json"]).read_text(encoding="utf-8"))
    assert "controlled_failure_injection" in summary
    assert "real_world_ci_injection" in summary
