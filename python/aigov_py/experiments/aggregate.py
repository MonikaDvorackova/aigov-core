from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise TypeError(path)
    return obj


def aggregate(
    *,
    out_final_dir: Path,
    cfi_dir: Path,
    abe_dir: Path | None,
    rwci_dir: Path,
) -> dict[str, Any]:
    cfi = _read_json(cfi_dir / "controlled_failure_injection.json")
    rwci = _read_json(rwci_dir / "real_world_ci_injection.json")

    summary_cfi = cfi.get("summary")
    if not isinstance(summary_cfi, dict):
        raise ValueError("CFI JSON missing summary")

    overall = summary_cfi.get("overall")
    if not isinstance(overall, dict):
        raise ValueError("CFI summary missing overall")

    rwci_summary = rwci.get("summary")
    if not isinstance(rwci_summary, dict):
        raise ValueError("RWCI JSON missing summary")

    abe_payload: dict[str, Any] | None = None
    abe_path = (abe_dir / "artifact_bound_enforcement.json") if abe_dir else None
    if abe_path and abe_path.is_file():
        abe_payload = _read_json(abe_path)

    cfi_flat: dict[str, Any] = {
        "total_runs": overall.get("total_runs"),
        "baseline_1_false_negative_rate": overall.get("baseline_1_false_negative_rate"),
        "baseline_2_false_negative_rate": overall.get("baseline_2_false_negative_rate"),
        "gate_detection_rate": overall.get("gate_detection_rate"),
        "valid_retention_rate": overall.get("valid_retention_rate"),
        "false_blocking_rate": overall.get("false_blocking_rate"),
        "verdict_classification_accuracy": overall.get("verdict_classification_accuracy"),
        "invalid_vs_blocked_match_rate": overall.get("invalid_vs_blocked_match_rate"),
        "artifact_continuity_failure_detection_rate": overall.get(
            "artifact_continuity_failure_detection_rate"
        ),
        "digest_mismatch_detection_rate": overall.get("digest_mismatch_detection_rate"),
        "approval_ordering_violation_detection_rate": overall.get(
            "approval_ordering_violation_detection_rate"
        ),
        "replicates_per_scenario": overall.get("replicates_per_scenario"),
        "scenario_count": overall.get("scenario_count"),
    }
    ablations = overall.get("ablations")
    if isinstance(ablations, dict):
        for ab_name, ab_metrics in ablations.items():
            if isinstance(ab_metrics, dict):
                for mk, mv in ab_metrics.items():
                    cfi_flat[f"ablation__{ab_name}__{mk}"] = mv

    final: dict[str, Any] = {
        "controlled_failure_injection": cfi_flat,
        "real_world_ci_injection": rwci_summary,
        "artifact_bound_enforcement": abe_payload,
    }

    out_final_dir = out_final_dir.expanduser().resolve()
    out_final_dir.mkdir(parents=True, exist_ok=True)

    final_json = out_final_dir / "final_summary.json"
    final_json.write_text(json.dumps(final, indent=2), encoding="utf-8")

    table_rows: list[dict[str, str]] = []

    def add_row(experiment: str, metric: str, value: str) -> None:
        table_rows.append({"experiment": experiment, "metric": metric, "value": value})

    def fmt(v: object) -> str:
        if isinstance(v, float):
            s = f"{v:.6f}".rstrip("0").rstrip(".")
            return s if s else "0"
        return f"{v}"

    for key, val in final["controlled_failure_injection"].items():
        if val is None:
            continue
        if isinstance(val, (dict, list)):
            continue
        add_row("controlled_failure_injection", key, fmt(val))

    for key, val in rwci_summary.items():
        if key == "note":
            continue
        if isinstance(val, (dict, list)):
            continue
        add_row("real_world_ci_injection", key, fmt(val))

    if abe_payload and isinstance(abe_payload.get("scenarios"), list):
        scenarios = abe_payload["scenarios"]
        blocked = sum(
            1
            for s in scenarios
            if isinstance(s, dict) and str(s.get("gate_result")) == "BLOCKED"
        )
        add_row("artifact_bound_enforcement", "scenario_count", str(len(scenarios)))
        add_row("artifact_bound_enforcement", "blocked_scenarios", str(blocked))

    final_csv = out_final_dir / "final_table.csv"
    with open(final_csv, "w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=["experiment", "metric", "value"])
        w.writeheader()
        w.writerows(table_rows)

    return {"summary_json": str(final_json), "table_csv": str(final_csv)}


def main_cli(*, output: Path, cfi: Path, abe: Path | None, rwci: Path) -> int:
    paths = aggregate(out_final_dir=output, cfi_dir=cfi, abe_dir=abe, rwci_dir=rwci)
    print("Wrote:")
    print(f"  - {paths['summary_json']}")
    print(f"  - {paths['table_csv']}")
    return 0
