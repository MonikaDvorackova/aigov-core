import hashlib
import os
from typing import Any, Dict, Tuple

from .canonical_json import canonical_dumps


def _load_iris_safe():
    try:
        from sklearn.datasets import load_iris  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "scikit-learn is required for Iris demo helpers (dataset_fingerprint_iris / dataset_governance_iris)."
        ) from e
    return load_iris()


def dataset_fingerprint_iris() -> str:
    iris = _load_iris_safe()
    payload = {
        "dataset": "iris",
        "n_rows": int(iris.data.shape[0]),
        "n_features": int(iris.data.shape[1]),
        "target_names": list(iris.target_names),
    }
    raw = canonical_dumps(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def dataset_governance_iris() -> Dict[str, Any]:
    """
    Prototype dataset governance metadata.

    In a real product this would be provided by an internal governance workflow.
    """

    iris = _load_iris_safe()
    fp = dataset_fingerprint_iris()

    ai_system_id = os.environ.get("AIGOV_AI_SYSTEM_ID", "aigov_poc").strip() or "aigov_poc"
    dataset_id = os.environ.get("AIGOV_DATASET_ID", "dataset_iris_v1").strip() or "dataset_iris_v1"

    base = {
        # Explicit identifiers for thesis-safe cross-linking.
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "dataset": "iris",
        "dataset_version": "v1",
        "dataset_fingerprint": fp,
        "dataset_governance_id": "dataset_iris_v1",
        "source": "sklearn.datasets.load_iris()",
        "intended_use": "Proof-of-concept governance demo (classification on Iris features).",
        "limitations": "Synthetic demo dataset; not representative of real-world populations.",
        "quality_summary": "Rows=150, Features=4, Classes=3, Balanced labels; fingerprinted for traceability.",
        "governance_status": "governed",
        "n_rows": int(iris.data.shape[0]),
        "n_features": int(iris.data.shape[1]),
        "target_names": list(iris.target_names),
    }

    commitment_raw = canonical_dumps(base).encode("utf-8")
    base["dataset_governance_commitment"] = hashlib.sha256(commitment_raw).hexdigest()
    return base


def assessment_id_for_run(run_id: str) -> str:
    return f"assessment_01_{run_id}"


def risk_id_for_run(run_id: str) -> str:
    return f"risk_01_{run_id}"


def approved_human_event_id_for_run(run_id: str) -> str:
    # Must match the human approval event_id used by approve.py.
    return f"ha_{run_id}"


def model_version_id_for_run(run_id: str) -> str:
    return f"model_version_01_{run_id}"


def risk_lifecycle_payloads(run_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Returns (risk_recorded_payload, risk_mitigated_payload, risk_reviewed_payload).
    """

    dataset_gov = dataset_governance_iris()
    dataset_commitment = dataset_gov["dataset_governance_commitment"]
    ai_system_id = dataset_gov["ai_system_id"]
    dataset_id = dataset_gov["dataset_id"]
    assessment_id = assessment_id_for_run(run_id)
    risk_id = risk_id_for_run(run_id)
    model_version_id = model_version_id_for_run(run_id)

    risk_class = os.environ.get("AIGOV_RISK_CLASS", "high").strip() or "high"
    severity = float(os.environ.get("AIGOV_RISK_SEVERITY", "4"))
    likelihood = float(os.environ.get("AIGOV_RISK_LIKELIHOOD", "0.3"))
    owner = os.environ.get("AIGOV_RISK_OWNER", "risk_owner").strip() or "risk_owner"

    reviewer = os.environ.get("AIGOV_RISK_REVIEWER", "risk_officer").strip() or "risk_officer"
    justification = (
        "Dataset governance commitment verified; evaluation threshold and human oversight requested before promotion."
    )

    recorded = {
        "assessment_id": assessment_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
        "risk_class": risk_class,
        "severity": severity,
        "likelihood": likelihood,
        "status": "submitted",
        "mitigation": "Establish evaluation threshold and require human promotion approval.",
        "owner": owner,
        "dataset_governance_commitment": dataset_commitment,
    }

    mitigated = {
        "assessment_id": assessment_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
        "status": "mitigated",
        "mitigation": "Mitigation applied: restrict intended use to the governed demo scope + enforce passed evaluation gate.",
        "dataset_governance_commitment": dataset_commitment,
    }

    reviewed = {
        "assessment_id": assessment_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
        "decision": "approve",
        "reviewer": reviewer,
        "justification": justification,
        "dataset_governance_commitment": dataset_commitment,
    }

    return recorded, mitigated, reviewed

