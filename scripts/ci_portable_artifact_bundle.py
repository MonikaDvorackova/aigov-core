#!/usr/bin/env python3
"""
Build CI evidence artefacts offline for GovAI Core (no HTTP audit server).

GovAI Core does not start or poll a hosted audit runtime. This script writes
ledger-shaped evidence bundles on disk, runs portable export/pack steps, and
emits evidence_digest_manifest.json using portable_evidence_digest_v1.

Hosted ledger submission and GET /ready polling belong to the GovAI Platform
repository, not this Core CI path.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from aigov_py.portable_evidence_digest import portable_evidence_digest_v1
from aigov_py.prototype_domain import approved_human_event_id_for_run, model_version_id_for_run


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _event(
    *,
    event_id: str,
    event_type: str,
    run_id: str,
    payload: dict,
    actor: str = "ci",
    system: str = "github_actions",
) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "ts_utc": _utc_now(),
        "actor": actor,
        "system": system,
        "run_id": run_id,
        "environment": "ci",
        "payload": payload,
    }


def _ci_dataset_governance() -> dict[str, str]:
    """Static governance metadata for offline CI (no sklearn / no HTTP)."""
    return {
        "ai_system_id": "aigov_poc",
        "dataset_id": "dataset_iris_v1",
        "dataset": "iris",
        "dataset_version": "v1",
        "dataset_fingerprint": "ci_portable_static_iris_fingerprint_v1",
        "dataset_governance_id": "dataset_iris_v1",
        "dataset_governance_commitment": "ci_portable_static_iris_commitment_v1",
        "source": "govai_core_ci_portable_bundle",
        "intended_use": "Portable Core CI artefact-bound gate (offline).",
        "limitations": "Synthetic CI fixture; not a hosted ledger submission.",
        "quality_summary": "Offline bundle for digest and pack validation only.",
        "governance_status": "governed",
    }


def _portable_ci_events(run_id: str) -> tuple[list[dict], dict[str, str]]:
    """Events required by assert_ci_evidence_bundle (no ci_fallback_used)."""
    dg = _ci_dataset_governance()
    ai_system_id = dg["ai_system_id"]
    dataset_id = dg["dataset_id"]
    model_version_id = model_version_id_for_run(run_id)
    assessment_id = f"assessment_01_{run_id}"
    risk_id = f"risk_01_{run_id}"
    dataset_commitment = dg["dataset_governance_commitment"]
    risk_recorded = {
        "assessment_id": assessment_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
        "risk_class": "high",
        "severity": 4.0,
        "likelihood": 0.3,
        "status": "submitted",
        "mitigation": "Portable CI evaluation threshold and human approval required.",
        "owner": "risk_owner",
        "dataset_governance_commitment": dataset_commitment,
    }
    risk_mitigated = {
        "assessment_id": assessment_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
        "status": "mitigated",
        "dataset_governance_commitment": dataset_commitment,
    }
    risk_reviewed = {
        "assessment_id": assessment_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
        "status": "reviewed",
        "reviewer": "risk_officer",
        "justification": "Portable CI bundle for offline artefact gate.",
        "dataset_governance_commitment": dataset_commitment,
    }
    suffix = run_id.replace("-", "_")[:32]

    events = [
        _event(
            event_id=f"evt_run_started_{suffix}",
            event_type="run_started",
            run_id=run_id,
            payload={
                "purpose": "ci_portable_artifact_bundle",
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "risk_id": risk_id,
            },
        ),
        _event(
            event_id=f"evt_data_registered_{suffix}",
            event_type="data_registered",
            run_id=run_id,
            payload={
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "dataset": dg["dataset"],
                "dataset_version": dg["dataset_version"],
                "dataset_fingerprint": dg["dataset_fingerprint"],
                "dataset_governance_id": dg["dataset_governance_id"],
                "dataset_governance_commitment": dg["dataset_governance_commitment"],
                "source": dg["source"],
                "intended_use": dg["intended_use"],
                "limitations": dg["limitations"],
                "quality_summary": dg["quality_summary"],
                "governance_status": dg["governance_status"],
            },
        ),
        _event(
            event_id=f"evt_risk_recorded_{suffix}",
            event_type="risk_recorded",
            run_id=run_id,
            payload=risk_recorded,
        ),
        _event(
            event_id=f"evt_risk_mitigated_{suffix}",
            event_type="risk_mitigated",
            run_id=run_id,
            payload=risk_mitigated,
        ),
        _event(
            event_id=f"evt_risk_reviewed_{suffix}",
            event_type="risk_reviewed",
            run_id=run_id,
            payload=risk_reviewed,
        ),
        _event(
            event_id=f"evt_eval_{suffix}",
            event_type="evaluation_reported",
            run_id=run_id,
            payload={
                "passed": True,
                "accuracy": 0.95,
                "threshold": 0.8,
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
            },
        ),
        _event(
            event_id=f"evt_disc_{suffix}",
            event_type="ai_discovery_reported",
            run_id=run_id,
            payload={"openai": False, "transformers": False, "model_artifacts": False},
        ),
        _event(
            event_id=f"evt_human_{suffix}",
            event_type="human_approved",
            run_id=run_id,
            payload={
                "decision": "approve",
                "approved_by": "ci-portable",
                "approved_human_event_id": approved_human_event_id_for_run(run_id),
                "ai_system_id": ai_system_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
            },
        ),
        _event(
            event_id=f"evt_promote_{suffix}",
            event_type="model_promoted",
            run_id=run_id,
            payload={
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "artifact_sha256": "a" * 64,
                "artifact_path": "ci_portable/model.joblib",
                "promotion_reason": "portable_ci_bundle",
                "approved_human_event_id": approved_human_event_id_for_run(run_id),
            },
        ),
    ]
    ids = {
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
    }
    return events, ids


def _write_evidence_bundle(
    run_id: str,
    events: list[dict],
    ids: dict[str, str],
    policy_version: str = "v0",
) -> Path:
    root = _repo_root()
    path = root / "docs" / "evidence" / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = portable_evidence_digest_v1(run_id, events)
    body = {
        "run_id": run_id,
        "policy_version": policy_version,
        "events": events,
        "bundle_sha256": digest,
        "identifiers": {
            "ai_system_id": ids["ai_system_id"],
            "dataset_id": ids["dataset_id"],
            "model_version_id": ids["model_version_id"],
            "risk_ids": [ids["risk_id"]],
            "primary_risk_id": ids["risk_id"],
        },
    }
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _ensure_report(run_id: str, report_basename: str | None) -> None:
    root = _repo_root()
    reports = root / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    dest = reports / f"{run_id}.md"
    if dest.exists():
        return
    if report_basename:
        src = reports / f"{report_basename}.md"
        if src.is_file():
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            return
    dest.write_text(
        "\n".join(
            [
                f"run_id={run_id}",
                "bundle_sha256=",
                "policy_version=v0",
                "",
                "## Evaluation gate",
                "",
                "Portable CI bundle (offline).",
                "",
                "## Human approval gate",
                "",
                "Portable CI bundle (offline).",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        cmd,
        cwd=cwd or _repo_root(),
        check=True,
        env=env,
    )


def build(run_id: str, artifact_dir: Path, report_basename: str | None) -> None:
    run_id = run_id.strip()
    if not run_id:
        raise SystemExit("run_id is required")

    events, ids = _portable_ci_events(run_id)
    _write_evidence_bundle(run_id, events, ids)
    _ensure_report(run_id, report_basename)

    py = sys.executable
    _run([py, "-m", "aigov_py.export_bundle", run_id])
    env = {**os.environ, "RUN_ID": run_id, "AIGOV_MODE": "ci"}
    _run([py, "-m", "aigov_py.evidence_pack"], env={**os.environ, **env})

    digest = portable_evidence_digest_v1(run_id, events).lower()
    manifest = {
        "schema": "aigov.evidence_digest_manifest.v1",
        "run_id": run_id,
        "events_content_sha256": digest,
        "evidence_digest_schema": "aigov.evidence_digest.v1",
        "bundle_sha256": digest,
        "policy_version": "v0",
        "source": "portable_evidence_digest_v1",
    }
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "evidence_digest_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    root = _repo_root()
    for sub, name in (
        ("reports", f"{run_id}.md"),
        ("audit", f"{run_id}.json"),
        ("evidence", f"{run_id}.json"),
        ("packs", f"{run_id}.zip"),
    ):
        src = root / "docs" / sub / name
        if src.is_file():
            (artifact_dir / name).write_bytes(src.read_bytes())

    _run([py, "-m", "aigov_py.assert_ci_evidence_bundle", run_id])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Offline portable CI evidence artefacts for GovAI Core.")
    p.add_argument("--run-id", required=True)
    p.add_argument("--artifact-dir", required=True)
    p.add_argument("--report-basename", default="", help="Committed docs/reports/<basename>.md stem")
    args = p.parse_args(argv)
    basename = args.report_basename.strip() or None
    build(args.run_id, Path(args.artifact_dir), basename)
    print(f"ci_portable_artifact_bundle: OK run_id={args.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
