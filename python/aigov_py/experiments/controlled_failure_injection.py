from __future__ import annotations

import csv
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import aigov_py.experiments.gate_model as gate_model_mod

from aigov_py.experiments import scenario_fields as sf
from aigov_py.experiments.gate_model import (
    FAILURE_TAXONOMY,
    GateAblation,
    RunRecord,
    build_run,
    decision_gate_verdict_from_fields,
    get_rubric_row,
    load_scenario_rubric,
    rubric_scenarios,
    run_id_for_cfi,
)


REPLICATES_PER_SCENARIO = 100


def failure_taxonomy() -> list[str]:
    return list(FAILURE_TAXONOMY)


def generate_runs(*, replicates: int = REPLICATES_PER_SCENARIO) -> list[RunRecord]:
    runs: list[RunRecord] = []
    idx = 1
    for row in rubric_scenarios():
        name = str(row["scenario_name"])
        is_inj = bool(row["injected_violation"])
        should_pass = bool(row["should_pass"])
        for _ in range(replicates):
            fields = sf.fields_for_scenario(name)
            runs.append(
                build_run(
                    run_id=run_id_for_cfi(idx),
                    condition=name,
                    is_injected_failure=is_inj,
                    should_pass=should_pass,
                    fields=fields,
                )
            )
            idx += 1
    return runs


def rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _ablation_presets() -> dict[str, GateAblation]:
    return {
        "full_gate": GateAblation(),
        "no_digest_checks": GateAblation(skip_events_digest=True, skip_export_digest=True),
        "no_export_digest_check": GateAblation(skip_export_digest=True),
        "no_artifact_bound_verification": GateAblation(skip_artifact_bound=True),
        "no_approval_check": GateAblation(skip_approval=True),
        "no_trace_consistency": GateAblation(skip_trace=True),
        "no_policy_version_check": GateAblation(skip_policy_version=True),
    }


def _ablated_verdict(fields: dict[str, object], ablation: GateAblation) -> str:
    return decision_gate_verdict_from_fields(fields, ablation=ablation)


def _ablation_metrics(runs_list: list[RunRecord]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for label, ab in _ablation_presets().items():
        correct = 0
        for r in runs_list:
            row = get_rubric_row(r.condition)
            expected = str(row["expected_verdict"])
            fields = sf.fields_for_scenario(r.condition)
            got = _ablated_verdict(fields, ab)
            if got == expected:
                correct += 1
        out[label] = {
            "verdict_classification_accuracy": rate(correct, len(runs_list)),
        }
    return out


def compute_overall_metrics(runs_list: list[RunRecord]) -> dict[str, Any]:
    injected = [r for r in runs_list if r.is_injected_failure]
    should_pass = [r for r in runs_list if r.should_pass]

    b1_fn = sum(1 for r in injected if r.baseline_verdict == "VALID")
    b2_fn = sum(1 for r in injected if r.pipeline_baseline_verdict == "VALID")
    gate_detect = sum(1 for r in injected if r.gate_verdict != "VALID")
    valid_ret = sum(1 for r in should_pass if r.gate_verdict == "VALID")
    false_block = sum(1 for r in should_pass if r.gate_verdict != "VALID")
    vclass = sum(1 for r in runs_list if r.gate_verdict == r.expected_gate_verdict)

    inv_block_subset = [r for r in runs_list if r.expected_gate_verdict in ("INVALID", "BLOCKED")]
    inv_block_match = sum(1 for r in inv_block_subset if r.gate_verdict == r.expected_gate_verdict)

    art_subset = [
        r
        for r in injected
        if bool(get_rubric_row(r.condition).get("artifact_continuity_related"))
    ]
    art_detect = sum(1 for r in art_subset if r.gate_verdict != "VALID")

    dig_subset = [
        r for r in injected if bool(get_rubric_row(r.condition).get("digest_related"))
    ]
    dig_detect = sum(1 for r in dig_subset if r.gate_verdict != "VALID")

    ord_subset = [
        r for r in injected if bool(get_rubric_row(r.condition).get("approval_ordering_related"))
    ]
    ord_detect = sum(1 for r in ord_subset if r.gate_verdict != "VALID")

    return {
        "total_runs": len(runs_list),
        "baseline_1_false_negative_rate": rate(b1_fn, len(injected)),
        "baseline_2_false_negative_rate": rate(b2_fn, len(injected)),
        "gate_detection_rate": rate(gate_detect, len(injected)),
        "valid_retention_rate": rate(valid_ret, len(should_pass)),
        "false_blocking_rate": rate(false_block, len(should_pass)),
        "verdict_classification_accuracy": rate(vclass, len(runs_list)),
        "invalid_vs_blocked_match_rate": rate(inv_block_match, len(inv_block_subset)),
        "artifact_continuity_failure_detection_rate": rate(art_detect, len(art_subset)),
        "digest_mismatch_detection_rate": rate(dig_detect, len(dig_subset)),
        "approval_ordering_violation_detection_rate": rate(ord_detect, len(ord_subset)),
        "replicates_per_scenario": REPLICATES_PER_SCENARIO,
        "scenario_count": len(rubric_scenarios()),
        "ablations": _ablation_metrics(runs_list),
    }


def summarize_by_condition(runs_list: list[RunRecord]) -> list[dict[str, Any]]:
    names = sorted({r.condition for r in runs_list}, key=lambda x: scenario_names_order_index(x))
    rows: list[dict[str, Any]] = []
    for name in names:
        subset = [r for r in runs_list if r.condition == name]
        inj = [r for r in subset if r.is_injected_failure]
        sp = [r for r in subset if r.should_pass]

        b1_fn = sum(1 for r in inj if r.baseline_verdict == "VALID")
        b2_fn = sum(1 for r in inj if r.pipeline_baseline_verdict == "VALID")
        gate_detect = sum(1 for r in inj if r.gate_verdict != "VALID")
        valid_ret = sum(1 for r in sp if r.gate_verdict == "VALID")
        false_block = sum(1 for r in sp if r.gate_verdict != "VALID")

        b1s = "---" if not inj else f"{rate(b1_fn, len(inj)):.3f}"
        b2s = "---" if not inj else f"{rate(b2_fn, len(inj)):.3f}"
        gds = "---" if not inj else f"{rate(gate_detect, len(inj)):.3f}"
        vrs = "---" if not sp else f"{rate(valid_ret, len(sp)):.3f}"
        fbs = "---" if not sp else f"{rate(false_block, len(sp)):.3f}"
        rows.append(
            {
                "condition": name,
                "runs": len(subset),
                "injected_violation_runs": len(inj),
                "should_pass_runs": len(sp),
                "baseline_1_false_negative_rate": b1s,
                "baseline_2_false_negative_rate": b2s,
                "gate_detection_rate": gds,
                "valid_retention_rate": vrs,
                "false_blocking_rate": fbs,
                "verdict_classification_accuracy": f"{rate(sum(1 for r in subset if r.gate_matches_rubric), len(subset)):.3f}",
                "expected_verdict": subset[0].expected_gate_verdict if subset else "",
            }
        )
    return rows


def scenario_names_order_index(name: str) -> int:
    order = [str(r["scenario_name"]) for r in rubric_scenarios()]
    try:
        return order.index(name)
    except ValueError:
        return 9999


def write_latex_scenario_table(path: Path) -> None:
    rubric = load_scenario_rubric()
    scenarios = rubric["scenarios"]
    lines: list[str] = []
    lines.append("\\begin{tabular}{llll}")
    lines.append("\\toprule")
    lines.append(
        "Scenario & Family & Invariant & Expected \\\\"
    )
    lines.append("\\midrule")

    def esc(s: str) -> str:
        return (
            s.replace("\\", "\\textbackslash{}")
            .replace("_", "\\_")
            .replace("%", "\\%")
            .replace("&", "\\&")
        )

    for row in scenarios:
        if not isinstance(row, dict):
            continue
        nm = esc(str(row.get("scenario_name", "")))
        fam = esc(str(row.get("failure_family", "")))
        inv = row.get("primary_violated_invariant")
        inv_s = esc(str(inv)) if inv is not None else "---"
        exp = esc(str(row.get("expected_verdict", "")))
        lines.append(f"{nm} & {fam} & {inv_s} & {exp} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex_outcome_table(path: Path, rows: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    lines.append("\\begin{tabular}{lrrrr}")
    lines.append("\\toprule")
    lines.append(
        "Scenario & B1 FN & B2 FN & Gate det. & Val. retain. \\\\"
    )
    lines.append("\\midrule")

    def esc(s: str) -> str:
        return (
            s.replace("\\", "\\textbackslash{}")
            .replace("_", "\\_")
            .replace("%", "\\%")
            .replace("&", "\\&")
        )

    for r in rows:
        lines.append(
            f"{esc(r['condition'])} & {r['baseline_1_false_negative_rate']} & "
            f"{r['baseline_2_false_negative_rate']} & {r['gate_detection_rate']} & "
            f"{r['valid_retention_rate']} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex_ablation_table(path: Path, ablations: dict[str, dict[str, float]]) -> None:
    lines: list[str] = []
    lines.append("\\begin{tabular}{lr}")
    lines.append("\\toprule")
    lines.append("Ablation & Verdict accuracy \\\\")
    lines.append("\\midrule")

    def esc(s: str) -> str:
        return (
            s.replace("\\", "\\textbackslash{}")
            .replace("_", "\\_")
            .replace("%", "\\%")
            .replace("&", "\\&")
        )

    for k, v in ablations.items():
        acc = v.get("verdict_classification_accuracy", 0.0)
        lines.append(f"{esc(k)} & {acc:.3f} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_csv(path: Path, rows: list[dict[str, Any]], overall: dict[str, Any]) -> None:
    if not rows:
        raise ValueError("no rows")
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        overall_row = {k: "" for k in fieldnames}
        overall_row["condition"] = "OVERALL"
        overall_row["runs"] = str(overall.get("total_runs", ""))
        overall_row["verdict_classification_accuracy"] = f"{overall.get('verdict_classification_accuracy', 0.0):.3f}"
        overall_row["baseline_1_false_negative_rate"] = f"{overall.get('baseline_1_false_negative_rate', 0.0):.3f}"
        overall_row["baseline_2_false_negative_rate"] = f"{overall.get('baseline_2_false_negative_rate', 0.0):.3f}"
        overall_row["gate_detection_rate"] = f"{overall.get('gate_detection_rate', 0.0):.3f}"
        overall_row["valid_retention_rate"] = f"{overall.get('valid_retention_rate', 0.0):.3f}"
        overall_row["false_blocking_rate"] = f"{overall.get('false_blocking_rate', 0.0):.3f}"
        writer.writerow(overall_row)


def write_outputs(out_dir: Path, *, runs: list[RunRecord] | None = None) -> dict[str, str]:
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if runs is None:
        runs = generate_runs()

    rows = summarize_by_condition(runs)
    overall = compute_overall_metrics(runs)
    by_condition = {r["condition"]: r for r in rows}

    minimal_runs: list[dict[str, str]] = []
    for r in runs:
        minimal_runs.append(
            {
                "run_id": r.run_id,
                "condition": r.condition,
                "expected_label": r.expected_gate_verdict,
                "gate_label": r.gate_verdict,
                "pipeline_baseline_label": r.pipeline_baseline_verdict,
                "gate_matches_rubric": str(r.gate_matches_rubric),
            }
        )

    summary_obj = {
        "by_condition": by_condition,
        "overall": overall,
        "condition_tables": rows,
        "rubric": load_scenario_rubric(),
    }

    payload = {
        "runs": [asdict(r) for r in runs],
        "summary": summary_obj,
    }

    json_path = out_dir / "controlled_failure_injection.json"
    csv_path = out_dir / "controlled_failure_injection.csv"
    full_csv_path = out_dir / "controlled_failure_injection_full.csv"
    summary_csv = out_dir / "controlled_failure_injection_summary.csv"
    tex_scenarios = out_dir / "failure_injection_scenarios_table.tex"
    tex_outcomes = out_dir / "failure_injection_outcomes_table.tex"
    tex_ablation = out_dir / "failure_injection_ablation_table.tex"

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)

    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "run_id",
                "condition",
                "expected_label",
                "gate_label",
                "pipeline_baseline_label",
                "gate_matches_rubric",
            ],
        )
        writer.writeheader()
        writer.writerows(minimal_runs)

    if runs:
        fieldnames = list(asdict(runs[0]).keys())
        with open(full_csv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for run in runs:
                writer.writerow(asdict(run))

    write_summary_csv(summary_csv, rows, overall)
    write_latex_scenario_table(tex_scenarios)
    write_latex_outcome_table(tex_outcomes, rows)
    ablations = overall.get("ablations")
    if isinstance(ablations, dict):
        write_latex_ablation_table(tex_ablation, ablations)  # type: ignore[arg-type]

    rubric_copy = out_dir / "scenario_rubric.json"
    shutil.copyfile(
        Path(gate_model_mod.__file__).resolve().with_name("scenario_rubric.json"),
        rubric_copy,
    )

    legacy_json = out_dir / "failure_injection_runs.json"
    with open(legacy_json, "w", encoding="utf-8") as handle:
        json.dump([asdict(r) for r in runs], handle, indent=2, sort_keys=False)

    legacy_csv = out_dir / "failure_injection_runs.csv"
    if runs:
        with open(legacy_csv, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(asdict(runs[0]).keys()))
            writer.writeheader()
            for run in runs:
                writer.writerow(asdict(run))

    legacy_summary = out_dir / "failure_injection_summary.csv"
    write_summary_csv(legacy_summary, rows, overall)

    legacy_table = out_dir / "failure_injection_table.tex"
    write_latex_outcome_table(legacy_table, rows)

    results_csv = out_dir / "failure_injection_results.csv"
    shutil.copyfile(csv_path, results_csv)

    summary_json_path = out_dir / "failure_injection_summary.json"
    summary_json_payload = {
        "experiment": "controlled_failure_injection",
        "schema": "aigov.failure_injection_summary.v1",
        "total_runs": len(runs),
        "replicates_per_scenario": REPLICATES_PER_SCENARIO,
        "scenario_count": len(rubric_scenarios()),
        "overall": overall,
        "rubric_path": "scenario_rubric.json",
    }
    with open(summary_json_path, "w", encoding="utf-8") as handle:
        json.dump(summary_json_payload, handle, indent=2, sort_keys=False)

    return {
        "json": str(json_path),
        "csv": str(csv_path),
        "csv_full": str(full_csv_path),
        "summary_csv": str(summary_csv),
        "tex_scenarios": str(tex_scenarios),
        "tex_outcomes": str(tex_outcomes),
        "tex_ablation": str(tex_ablation),
        "legacy_failure_injection_runs_json": str(legacy_json),
        "legacy_failure_injection_runs_csv": str(legacy_csv),
        "legacy_failure_injection_summary_csv": str(legacy_summary),
        "legacy_failure_injection_table_tex": str(legacy_table),
        "scenario_rubric_json": str(rubric_copy),
        "failure_injection_results_csv": str(results_csv),
        "failure_injection_summary_json": str(summary_json_path),
    }


def main_cli(output: Path) -> int:
    paths = write_outputs(output)
    print("Wrote:")
    for _k, v in paths.items():
        print(f"  - {v}")
    return 0
