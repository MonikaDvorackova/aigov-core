from __future__ import annotations

"""
Repository prevalence check (offline, illustrative).

Deterministic curated snapshot over exactly thirty public repositories. Signals are
manually coded in source (no network); output is illustrative only — not statistically
representative.

Graded auditability maturity is derived from five decision-facing booleans combined
linearly instead of treating decision-level readiness as one binary conjunction.
"""

import csv
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

# Exactly 30 public repositories; fixed order for deterministic outputs.
# Five-tuple shorthand in comments per row is (audit_evidence, ai_inventory, gate, record, trace).
CURATED_REPO_ROWS: tuple[dict[str, bool | str], ...] = (
    {
        "repo_name": "pytorch/pytorch",
        "repo_url": "https://github.com/pytorch/pytorch",
        "domain": "training_framework",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 00000
    {
        "repo_name": "tensorflow/tensorflow",
        "repo_url": "https://github.com/tensorflow/tensorflow",
        "domain": "training_framework",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": False,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 00000
    {
        "repo_name": "keras-team/keras",
        "repo_url": "https://github.com/keras-team/keras",
        "domain": "training_framework",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": False,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 00000
    {
        "repo_name": "huggingface/transformers",
        "repo_url": "https://github.com/huggingface/transformers",
        "domain": "model_library",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 01000
    {
        "repo_name": "huggingface/datasets",
        "repo_url": "https://github.com/huggingface/datasets",
        "domain": "data_tools",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 10000
    {
        "repo_name": "scikit-learn/scikit-learn",
        "repo_url": "https://github.com/scikit-learn/scikit-learn",
        "domain": "classical_ml",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 00100
    {
        "repo_name": "jax-ml/jax",
        "repo_url": "https://github.com/jax-ml/jax",
        "domain": "training_framework",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 01000
    {
        "repo_name": "pytorch/torchvision",
        "repo_url": "https://github.com/pytorch/vision",
        "domain": "model_library",
        "model_validation_present": True,
        "ci_present": False,
        "deployment_or_promotion_present": False,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 00000 — still model-centric via model_validation_present
    {
        "repo_name": "dmlc/xgboost",
        "repo_url": "https://github.com/dmlc/xgboost",
        "domain": "classical_ml",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 00000
    {
        "repo_name": "catboost/catboost",
        "repo_url": "https://github.com/catboost/catboost",
        "domain": "classical_ml",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 10000
    {
        "repo_name": "lightning-ai/pytorch-lightning",
        "repo_url": "https://github.com/Lightning-AI/pytorch-lightning",
        "domain": "training_framework",
        "model_validation_present": False,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 00100
    {
        "repo_name": "microsoft/LightGBM",
        "repo_url": "https://github.com/microsoft/LightGBM",
        "domain": "classical_ml",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 01000
    {
        "repo_name": "onnx/onnx",
        "repo_url": "https://github.com/onnx/onnx",
        "domain": "interoperability",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 10000
    {
        "repo_name": "apache/tvm",
        "repo_url": "https://github.com/apache/tvm",
        "domain": "compiler_runtime",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 00100
    {
        "repo_name": "open-mmlab/mmdetection",
        "repo_url": "https://github.com/open-mmlab/mmdetection",
        "domain": "applied_cv",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 11000
    {
        "repo_name": "facebookresearch/fairseq",
        "repo_url": "https://github.com/facebookresearch/fairseq",
        "domain": "applied_nlp",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 10100
    {
        "repo_name": "allenai/allennlp",
        "repo_url": "https://github.com/allenai/allennlp",
        "domain": "applied_nlp",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 01100
    {
        "repo_name": "tensorflow/models",
        "repo_url": "https://github.com/tensorflow/models",
        "domain": "model_library",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 11000
    {
        "repo_name": "huggingface/evaluate",
        "repo_url": "https://github.com/huggingface/evaluate",
        "domain": "evaluation_tools",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": False,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": True,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 10010
    {
        "repo_name": "pytorch/audio",
        "repo_url": "https://github.com/pytorch/audio",
        "domain": "model_library",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 10100
    {
        "repo_name": "ray-project/ray",
        "repo_url": "https://github.com/ray-project/ray",
        "domain": "distributed_training_or_serving",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 11000
    {
        "repo_name": "apache/airflow",
        "repo_url": "https://github.com/apache/airflow",
        "domain": "workflow_orchestration",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 11100
    {
        "repo_name": "mlflow/mlflow",
        "repo_url": "https://github.com/mlflow/mlflow",
        "domain": "mlops_tracking",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": True,
    },  # 10001
    {
        "repo_name": "kubeflow/pipelines",
        "repo_url": "https://github.com/kubeflow/pipelines",
        "domain": "ml_workflow",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 01100
    {
        "repo_name": "iterative/dvc",
        "repo_url": "https://github.com/iterative/dvc",
        "domain": "data_version_control",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": True,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 10110
    {
        "repo_name": "wandb/wandb",
        "repo_url": "https://github.com/wandb/wandb",
        "domain": "experiment_tracking",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": False,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 00100
    {
        "repo_name": "optuna/optuna",
        "repo_url": "https://github.com/optuna/optuna",
        "domain": "hyperparameter_search",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": True,
    },  # 11101 — four signals (moderate/strong boundary)
    {
        "repo_name": "ludwig-ai/ludwig",
        "repo_url": "https://github.com/ludwig-ai/ludwig",
        "domain": "applied_automl",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": False,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": True,
        "run_to_decision_traceability_present": False,
    },  # 11100
    {
        "repo_name": "pytorch/text",
        "repo_url": "https://github.com/pytorch/text",
        "domain": "data_tools",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": False,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": False,
        "decision_record_present": False,
        "run_to_decision_traceability_present": False,
    },  # 01000
    {
        "repo_name": "keras-team/keras-tuner",
        "repo_url": "https://github.com/keras-team/keras-tuner",
        "domain": "hyperparameter_search",
        "model_validation_present": True,
        "ci_present": True,
        "deployment_or_promotion_present": True,
        "audit_evidence_trace_present": True,
        "ai_discovery_or_inventory_present": True,
        "explicit_approval_gate_present": True,
        "decision_record_present": True,
        "run_to_decision_traceability_present": True,
    },  # 11111 — single curated “complete” row
)


@dataclass(frozen=True)
class RepoSignals:
    repo_name: str
    repo_url: str
    domain: str
    model_validation_present: bool
    ci_present: bool
    deployment_or_promotion_present: bool
    audit_evidence_trace_present: bool
    ai_discovery_or_inventory_present: bool
    explicit_approval_gate_present: bool
    decision_record_present: bool
    run_to_decision_traceability_present: bool
    has_model_centric_validation: bool
    decision_signal_count: int
    auditability_score: float
    auditability_maturity: int
    has_partial_auditability: bool
    has_strong_auditability: bool
    has_complete_decision_level_auditability: bool
    auditability_gap_present: bool


def _decision_signal_count(row: dict[str, bool | str]) -> int:
    keys = (
        "audit_evidence_trace_present",
        "ai_discovery_or_inventory_present",
        "explicit_approval_gate_present",
        "decision_record_present",
        "run_to_decision_traceability_present",
    )
    return sum(1 for k in keys if bool(row[k]))


def _compute_derived(row: dict[str, bool | str]) -> tuple[bool, int, float, int, bool, bool, bool, bool]:
    mv = bool(row["model_validation_present"])
    ci = bool(row["ci_present"])
    has_mc = mv or ci
    count = _decision_signal_count(row)
    score = count / 5.0
    maturity = count
    partial = count >= 2
    strong = count >= 4
    complete = count == 5
    gap = has_mc and (not complete)
    return has_mc, count, score, maturity, partial, strong, complete, gap


def build_repos(rows: Iterable[dict[str, bool | str]]) -> list[RepoSignals]:
    out: list[RepoSignals] = []
    for r in rows:
        has_mc, count, score, maturity, partial, strong, complete, gap = _compute_derived(r)
        out.append(
            RepoSignals(
                repo_name=str(r["repo_name"]),
                repo_url=str(r["repo_url"]),
                domain=str(r["domain"]),
                model_validation_present=bool(r["model_validation_present"]),
                ci_present=bool(r["ci_present"]),
                deployment_or_promotion_present=bool(r["deployment_or_promotion_present"]),
                audit_evidence_trace_present=bool(r["audit_evidence_trace_present"]),
                ai_discovery_or_inventory_present=bool(r["ai_discovery_or_inventory_present"]),
                explicit_approval_gate_present=bool(r["explicit_approval_gate_present"]),
                decision_record_present=bool(r["decision_record_present"]),
                run_to_decision_traceability_present=bool(
                    r["run_to_decision_traceability_present"]
                ),
                has_model_centric_validation=has_mc,
                decision_signal_count=count,
                auditability_score=score,
                auditability_maturity=maturity,
                has_partial_auditability=partial,
                has_strong_auditability=strong,
                has_complete_decision_level_auditability=complete,
                auditability_gap_present=gap,
            )
        )
    if len(out) != 30:
        raise RuntimeError(f"Expected 30 curated repositories, got {len(out)}")
    return out


def _count(repos: list[RepoSignals], pred) -> int:
    return sum(1 for r in repos if pred(r))


def compute_summary_metrics(repos: list[RepoSignals]) -> dict[str, float | int]:
    n = len(repos)
    if n == 0:
        raise RuntimeError("No repositories.")

    def rate(num: int) -> float:
        return num / n

    mean_score = sum(r.auditability_score for r in repos) / n

    mc_count = _count(repos, lambda r: r.has_model_centric_validation)
    partial_count = _count(repos, lambda r: r.has_partial_auditability)
    strong_count = _count(repos, lambda r: r.has_strong_auditability)
    complete_count = _count(repos, lambda r: r.has_complete_decision_level_auditability)
    gap_count = _count(repos, lambda r: r.auditability_gap_present)

    metrics: dict[str, float | int] = {
        "total_repositories": n,
        "model_centric_validation_count": mc_count,
        "model_centric_validation_rate": rate(mc_count),
        "mean_auditability_score": mean_score,
        "partial_auditability_count": partial_count,
        "partial_auditability_rate": rate(partial_count),
        "strong_auditability_count": strong_count,
        "strong_auditability_rate": rate(strong_count),
        "complete_decision_level_auditability_count": complete_count,
        "complete_decision_level_auditability_rate": rate(complete_count),
        "auditability_gap_count": gap_count,
        "auditability_gap_rate": rate(gap_count),
        "audit_evidence_trace_count": _count(repos, lambda r: r.audit_evidence_trace_present),
        "audit_evidence_trace_rate": rate(
            _count(repos, lambda r: r.audit_evidence_trace_present)
        ),
        "ai_discovery_or_inventory_count": _count(
            repos, lambda r: r.ai_discovery_or_inventory_present
        ),
        "ai_discovery_or_inventory_rate": rate(
            _count(repos, lambda r: r.ai_discovery_or_inventory_present)
        ),
        "explicit_approval_gate_count": _count(
            repos, lambda r: r.explicit_approval_gate_present
        ),
        "explicit_approval_gate_rate": rate(
            _count(repos, lambda r: r.explicit_approval_gate_present)
        ),
        "decision_record_count": _count(repos, lambda r: r.decision_record_present),
        "decision_record_rate": rate(_count(repos, lambda r: r.decision_record_present)),
        "run_to_decision_traceability_count": _count(
            repos, lambda r: r.run_to_decision_traceability_present
        ),
        "run_to_decision_traceability_rate": rate(
            _count(repos, lambda r: r.run_to_decision_traceability_present)
        ),
    }
    return metrics


def write_repos_csv(path: str, repos: list[RepoSignals]) -> None:
    fieldnames = list(asdict(repos[0]).keys())
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for repo in repos:
            row = asdict(repo)
            for k in row:
                if isinstance(row[k], bool):
                    row[k] = str(row[k])
            writer.writerow(row)


def write_repos_json(path: str, repos: list[RepoSignals]) -> None:
    serialized = [asdict(r) for r in repos]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(serialized, handle, indent=2, sort_keys=True)


def write_summary_csv(path: str, metrics: dict[str, float | int]) -> None:
    ordered_keys = [
        "total_repositories",
        "model_centric_validation_count",
        "model_centric_validation_rate",
        "mean_auditability_score",
        "partial_auditability_count",
        "partial_auditability_rate",
        "strong_auditability_count",
        "strong_auditability_rate",
        "complete_decision_level_auditability_count",
        "complete_decision_level_auditability_rate",
        "auditability_gap_count",
        "auditability_gap_rate",
        "audit_evidence_trace_count",
        "audit_evidence_trace_rate",
        "ai_discovery_or_inventory_count",
        "ai_discovery_or_inventory_rate",
        "explicit_approval_gate_count",
        "explicit_approval_gate_rate",
        "decision_record_count",
        "decision_record_rate",
        "run_to_decision_traceability_count",
        "run_to_decision_traceability_rate",
    ]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        for key in ordered_keys:
            val = metrics[key]
            if isinstance(val, float):
                value_str = f"{val:.17g}"
            else:
                value_str = str(val)
            writer.writerow({"metric": key, "value": value_str})


def write_latex_table(path: str, metrics: dict[str, float | int]) -> None:
    def tex_escape(s: str) -> str:
        return (
            s.replace("\\", "\\textbackslash{}")
            .replace("_", "\\_")
            .replace("%", "\\%")
            .replace("&", "\\&")
        )

    total = int(metrics["total_repositories"])
    mean_score = float(metrics["mean_auditability_score"])

    rows_spec: list[tuple[str, int | None, float | None]] = [
        ("Model-centric validation present", int(metrics["model_centric_validation_count"]), None),
        ("Partial auditability present", int(metrics["partial_auditability_count"]), None),
        ("Strong auditability present", int(metrics["strong_auditability_count"]), None),
        (
            "Complete decision-level auditability present",
            int(metrics["complete_decision_level_auditability_count"]),
            None,
        ),
        ("Auditability gap present", int(metrics["auditability_gap_count"]), None),
        ("Audit evidence trace present", int(metrics["audit_evidence_trace_count"]), None),
        (
            "AI discovery or inventory present",
            int(metrics["ai_discovery_or_inventory_count"]),
            None,
        ),
        ("Explicit approval gate present", int(metrics["explicit_approval_gate_count"]), None),
        ("Decision record present", int(metrics["decision_record_count"]), None),
        (
            "Run-to-decision traceability present",
            int(metrics["run_to_decision_traceability_count"]),
            None,
        ),
        ("Mean auditability score", None, mean_score),
    ]

    lines: list[str] = []
    lines.append("\\begin{tabular}{lrr}")
    lines.append("\\toprule")
    lines.append("Signal & Repositories & Rate \\\\")
    lines.append("\\midrule")

    for label, count, mean_only in rows_spec:
        if count is not None:
            r = count / total if total else 0.0
            lines.append(f"{tex_escape(label)} & {count} & {r:.3f} \\\\")
        else:
            lines.append(f"{tex_escape(label)} & --- & {mean_only:.3f} \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> None:
    repos = build_repos(CURATED_REPO_ROWS)
    metrics = compute_summary_metrics(repos)

    out_dir = os.path.join("experiments", "output")
    os.makedirs(out_dir, exist_ok=True)

    repos_csv = os.path.join(out_dir, "repository_prevalence_repos.csv")
    by_repo_csv = os.path.join(out_dir, "repository_prevalence_by_repo.csv")
    repos_json = os.path.join(out_dir, "repository_prevalence_repos.json")
    summary_csv = os.path.join(out_dir, "repository_prevalence_summary.csv")
    table_tex = os.path.join(out_dir, "repository_prevalence_table.tex")
    repro_json = os.path.join(out_dir, "repository_prevalence_repro.json")

    write_repos_csv(repos_csv, repos)
    shutil.copyfile(repos_csv, by_repo_csv)
    write_repos_json(repos_json, repos)
    write_summary_csv(summary_csv, metrics)
    write_latex_table(table_tex, metrics)

    repro = {
        "schema": "aigov.repository_prevalence_repro.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script": "experiments/repository_prevalence_check.py",
        "coding_rubric_doc": "docs/reports/repository-prevalence-coding-rubric.md",
        "total_repositories": len(repos),
        "row_order": "fixed tuple order in repository_prevalence_check.CURATED_REPO_ROWS",
        "signals_version": "2026-05-03",
    }
    with open(repro_json, "w", encoding="utf-8") as handle:
        json.dump(repro, handle, indent=2, sort_keys=False)

    print("Wrote outputs:")
    print(f"- {repos_csv}")
    print(f"- {by_repo_csv}")
    print(f"- {repos_json}")
    print(f"- {summary_csv}")
    print(f"- {table_tex}")
    print(f"- {repro_json}")
    print("")
    print("Summary:")
    print(f"- total_repositories={int(metrics['total_repositories'])}")
    print(
        f"- model_centric_validation_rate="
        f"{float(metrics['model_centric_validation_rate']):.3f}"
    )
    print(f"- mean_auditability_score={float(metrics['mean_auditability_score']):.3f}")
    print(f"- auditability_gap_rate={float(metrics['auditability_gap_rate']):.3f}")


if __name__ == "__main__":
    main()
