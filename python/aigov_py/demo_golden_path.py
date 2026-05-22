from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aigov_py.portable_evidence_digest import portable_evidence_digest_v1
from aigov_py.prototype_domain import (
    assessment_id_for_run,
    model_version_id_for_run,
    risk_id_for_run,
)


@dataclass(frozen=True)
class GoldenPathResult:
    run_id: str
    artefacts_path: Path
    bundle_path: Path
    manifest_path: Path


_ACTOR = "golden_path"
_SYSTEM = "golden_path"

# Fixed timestamps for deterministic artifacts (except run_id).
_T0 = "2026-01-01T00:00:01Z"
_T1 = "2026-01-01T00:00:02Z"
_T2 = "2026-01-01T00:00:03Z"
_T3 = "2026-01-01T00:00:04Z"
_T4 = "2026-01-01T00:00:05Z"
_T5 = "2026-01-01T00:00:06Z"
_T6 = "2026-01-01T00:00:07Z"
_T7 = "2026-01-01T00:00:08Z"
_T8 = "2026-01-01T00:00:09Z"

_AI_SYSTEM_ID = "golden-path-ai-system"
_DATASET_ID = "golden-path-dataset-v1"
_DATASET_COMMITMENT = "basic_compliance"
_APPROVER = "compliance_officer"
_RISK_CLASS = "high"
_RISK_SEVERITY = 4.0
_RISK_LIKELIHOOD = 0.3
_RISK_OWNER = "risk_owner"
_RISK_REVIEWER = "risk_officer"


def _event_id(kind: str, run_id: str) -> str:
    return f"gp_{kind}_{run_id}"


def _bundle_doc(*, run_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    # Keep envelope compatible with submit-evidence-pack and existing docs.
    return {"ok": True, "run_id": run_id, "events": events}


def _deterministic_artifact_sha256(*, run_id: str, output_dir: Path) -> str:
    """
    Phase 1 requires `model_promoted` to be artifact-bound via a stable digest.

    - If a local artifact file exists under the generated golden-path directory, hash it.
    - Otherwise, derive a deterministic SHA256 from stable fixture content.
    """

    # Optional real artifact: for deployments that materialize a file during golden path.
    candidate = (output_dir / f"artifact_{run_id}.bin").resolve()
    if candidate.is_file():
        h = hashlib.sha256()
        with candidate.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    # Keep digest deterministic across runs to preserve "except run_id" fixtures.
    seed = b"aigov.golden_path_artifact.v1"
    return hashlib.sha256(seed).hexdigest()


def generate_demo_golden_path(*, run_id: str, output_dir: Path) -> GoldenPathResult:
    """
    Deterministic golden-path evidence artifacts for local/CI onboarding.

    Events satisfy default ingest policy (`rust/src/policy.rs`) and discovery requirements
    (`rust/src/projection.rs`: `ai_discovery_completed` via `ai_discovery_reported`; no extra
    discovery-driven codes when OpenAI/transformers/model_artifacts are false).

    Writes:
    - <output_dir>/<run_id>.json
    - <output_dir>/evidence_digest_manifest.json
    """
    rid = run_id.strip()
    if not rid:
        raise ValueError("run_id is required")

    out = output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    model_version_id = model_version_id_for_run(rid)
    assessment_id = assessment_id_for_run(rid)
    risk_id = risk_id_for_run(rid)
    human_event_id = _event_id("human_approved", rid)
    artifact_sha256 = _deterministic_artifact_sha256(run_id=rid, output_dir=out)

    # Optional: align discovery event id with naming; ingestion does not gate on ai_discovery_* id prefix.
    discovery_event_id = _event_id("ai_discovery_reported", rid)

    events: list[dict[str, Any]] = [
        {
            "event_id": discovery_event_id,
            "event_type": "ai_discovery_reported",
            "ts_utc": _T0,
            "actor": _ACTOR,
            "system": _SYSTEM,
            "run_id": rid,
            "payload": {
                "status": "completed",
                "openai": False,
                "transformers": False,
                "model_artifacts": False,
                "source": "demo_golden_path",
                "notes": "deterministic golden path; no extra discovery-derived requirements",
            },
        },
        {
            "event_id": _event_id("data_registered", rid),
            "event_type": "data_registered",
            "ts_utc": _T1,
            "actor": _ACTOR,
            "system": _SYSTEM,
            "run_id": rid,
            "payload": {
                "ai_system_id": _AI_SYSTEM_ID,
                "dataset_id": _DATASET_ID,
                "dataset": "golden_path_dataset",
                "dataset_version": "v1",
                "dataset_fingerprint": "sha256:golden_path_demo",
                "dataset_governance_id": "gov_golden_path_v1",
                "dataset_governance_commitment": _DATASET_COMMITMENT,
                "source": "internal",
                "intended_use": "golden path artefact-bound demo",
                "limitations": "synthetic onboarding evidence only",
                "quality_summary": "synthetic onboarding evidence only",
                "governance_status": "registered",
            },
        },
        {
            "event_id": _event_id("model_trained", rid),
            "event_type": "model_trained",
            "ts_utc": _T2,
            "actor": _ACTOR,
            "system": _SYSTEM,
            "run_id": rid,
            "payload": {
                "model_version_id": model_version_id,
                "ai_system_id": _AI_SYSTEM_ID,
                "dataset_id": _DATASET_ID,
                "model_type": "LogisticRegression",
                "artifact_path": f"registry://golden-path/model/{model_version_id}",
                "artifact_sha256": artifact_sha256,
            },
        },
        {
            "event_id": _event_id("evaluation_reported", rid),
            "event_type": "evaluation_reported",
            "ts_utc": _T3,
            "actor": _ACTOR,
            "system": _SYSTEM,
            "run_id": rid,
            "payload": {
                "ai_system_id": _AI_SYSTEM_ID,
                "dataset_id": _DATASET_ID,
                "model_version_id": model_version_id,
                "metric": "accuracy",
                "value": 0.95,
                "threshold": 0.8,
                "passed": True,
            },
        },
        {
            "event_id": _event_id("risk_recorded", rid),
            "event_type": "risk_recorded",
            "ts_utc": _T4,
            "actor": _ACTOR,
            "system": _SYSTEM,
            "run_id": rid,
            "payload": {
                "assessment_id": assessment_id,
                "ai_system_id": _AI_SYSTEM_ID,
                "dataset_id": _DATASET_ID,
                "model_version_id": model_version_id,
                "risk_id": risk_id,
                "risk_class": _RISK_CLASS,
                "severity": _RISK_SEVERITY,
                "likelihood": _RISK_LIKELIHOOD,
                "status": "submitted",
                "mitigation": "Golden path: enforce evaluation gate and human approval before promotion.",
                "owner": _RISK_OWNER,
                "dataset_governance_commitment": _DATASET_COMMITMENT,
            },
        },
        {
            "event_id": _event_id("risk_mitigated", rid),
            "event_type": "risk_mitigated",
            "ts_utc": _T5,
            "actor": _ACTOR,
            "system": _SYSTEM,
            "run_id": rid,
            "payload": {
                "assessment_id": assessment_id,
                "ai_system_id": _AI_SYSTEM_ID,
                "dataset_id": _DATASET_ID,
                "model_version_id": model_version_id,
                "risk_id": risk_id,
                "status": "mitigated",
                "mitigation": "Golden path mitigation recorded.",
                "dataset_governance_commitment": _DATASET_COMMITMENT,
            },
        },
        {
            "event_id": _event_id("risk_reviewed", rid),
            "event_type": "risk_reviewed",
            "ts_utc": _T6,
            "actor": _ACTOR,
            "system": _SYSTEM,
            "run_id": rid,
            "payload": {
                "assessment_id": assessment_id,
                "ai_system_id": _AI_SYSTEM_ID,
                "dataset_id": _DATASET_ID,
                "model_version_id": model_version_id,
                "risk_id": risk_id,
                "decision": "approve",
                "reviewer": _RISK_REVIEWER,
                "justification": "Golden path: acceptable residual risk for synthetic onboarding bundle.",
                "dataset_governance_commitment": _DATASET_COMMITMENT,
            },
        },
        {
            "event_id": human_event_id,
            "event_type": "human_approved",
            "ts_utc": _T7,
            "actor": _ACTOR,
            "system": _SYSTEM,
            "run_id": rid,
            "payload": {
                "scope": "model_promoted",
                "decision": "approve",
                "approved": True,
                "approver": _APPROVER,
                "justification": "Golden path: approve promotion after evaluation and risk review.",
                "ai_system_id": _AI_SYSTEM_ID,
                "dataset_id": _DATASET_ID,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": _DATASET_COMMITMENT,
            },
        },
        {
            "event_id": _event_id("model_promoted", rid),
            "event_type": "model_promoted",
            "ts_utc": _T8,
            "actor": _ACTOR,
            "system": _SYSTEM,
            "run_id": rid,
            "payload": {
                "artifact_path": f"registry://golden-path/artifacts/model/{model_version_id}",
                "artifact_sha256": artifact_sha256,
                "promotion_reason": "approved_by_human",
                "ai_system_id": _AI_SYSTEM_ID,
                "dataset_id": _DATASET_ID,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": _DATASET_COMMITMENT,
                "approved_human_event_id": human_event_id,
            },
        },
    ]

    bundle = _bundle_doc(run_id=rid, events=events)
    digest = portable_evidence_digest_v1(rid, events)

    manifest = {
        "schema": "aigov.evidence_digest_manifest.v1",
        "run_id": rid,
        "events_content_sha256": digest.lower(),
        "evidence_digest_schema": "aigov.evidence_digest.v1",
        "bundle_sha256": "",
        "policy_version": "",
    }

    bundle_path = out / f"{rid}.json"
    manifest_path = out / "evidence_digest_manifest.json"

    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return GoldenPathResult(
        run_id=rid,
        artefacts_path=out,
        bundle_path=bundle_path,
        manifest_path=manifest_path,
    )
