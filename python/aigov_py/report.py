from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    ts_utc: str
    actor: str
    system: str
    run_id: str
    payload: Dict[str, Any]


def _load_bundle(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _events(bundle: Dict[str, Any]) -> List[Event]:
    out: List[Event] = []
    for e in bundle.get("events", []):
        out.append(
            Event(
                event_id=str(e.get("event_id", "")),
                event_type=str(e.get("event_type", "")),
                ts_utc=str(e.get("ts_utc", "")),
                actor=str(e.get("actor", "")),
                system=str(e.get("system", "")),
                run_id=str(e.get("run_id", "")),
                payload=dict(e.get("payload", {}) or {}),
            )
        )
    return out


def _pick_last(events: List[Event], t: str) -> Optional[Event]:
    for e in reversed(events):
        if e.event_type == t:
            return e
    return None


def _md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def main() -> None:
    run_id = os.environ.get("RUN_ID", "").strip()
    if not run_id:
        raise SystemExit("RUN_ID is required")

    repo_root = Path(__file__).resolve().parents[2]

    bundle_path = repo_root / "docs" / "evidence" / f"{run_id}.json"
    if not bundle_path.exists():
        raise SystemExit(f"bundle not found: {bundle_path}")

    bundle = _load_bundle(bundle_path)
    events = _events(bundle)

    run_started = _pick_last(events, "run_started")
    data_registered = _pick_last(events, "data_registered")
    evaluation_reported = _pick_last(events, "evaluation_reported")
    risk_recorded = _pick_last(events, "risk_recorded")
    risk_mitigated = _pick_last(events, "risk_mitigated")
    risk_reviewed = _pick_last(events, "risk_reviewed")
    human_approved = _pick_last(events, "human_approved")
    model_promoted = _pick_last(events, "model_promoted")

    system = run_started.system if run_started else (events[0].system if events else "")
    actor = run_started.actor if run_started else (events[0].actor if events else "")
    policy_version = str(bundle.get("policy_version", "")).strip()
    log_path = str(bundle.get("log_path", "")).strip()
    artifact_path = str(bundle.get("model_artifact_path", "")).strip()

    bundle_sha256 = str(bundle.get("bundle_sha256", "")).strip()
    if not bundle_sha256:
        bundle_sha256 = _sha256_file(bundle_path)

    dataset = ""
    dataset_fp = ""
    dataset_version = ""
    dataset_governance_commitment = ""
    governance_status = ""
    n_rows = ""
    n_features = ""
    if data_registered:
        dataset = str(data_registered.payload.get("dataset", ""))
        dataset_fp = str(data_registered.payload.get("dataset_fingerprint", ""))
        dataset_version = str(data_registered.payload.get("dataset_version", ""))
        dataset_governance_commitment = str(
            data_registered.payload.get("dataset_governance_commitment", "")
        )
        governance_status = str(data_registered.payload.get("governance_status", ""))
        n_rows = str(data_registered.payload.get("n_rows", ""))
        n_features = str(data_registered.payload.get("n_features", ""))

    metric = ""
    value = ""
    threshold = ""
    passed = ""
    if evaluation_reported:
        metric = str(evaluation_reported.payload.get("metric", ""))
        value = str(evaluation_reported.payload.get("value", ""))
        threshold = str(evaluation_reported.payload.get("threshold", ""))
        passed = str(evaluation_reported.payload.get("passed", ""))

    risk_id = ""
    risk_class = ""
    severity = ""
    likelihood = ""
    risk_status = ""
    mitigation = ""
    owner = ""
    risk_decision = ""
    risk_reviewer = ""
    risk_justification = ""

    if risk_recorded:
        risk_id = str(risk_recorded.payload.get("risk_id", ""))
        risk_class = str(risk_recorded.payload.get("risk_class", ""))
        severity = str(risk_recorded.payload.get("severity", ""))
        likelihood = str(risk_recorded.payload.get("likelihood", ""))
        risk_status = str(risk_recorded.payload.get("status", ""))
        mitigation = str(risk_recorded.payload.get("mitigation", ""))
        owner = str(risk_recorded.payload.get("owner", ""))

    if risk_mitigated:
        risk_status = str(risk_mitigated.payload.get("status", risk_status))
        mitigation = str(risk_mitigated.payload.get("mitigation", mitigation))

    if risk_reviewed:
        risk_decision = str(risk_reviewed.payload.get("decision", ""))
        risk_reviewer = str(risk_reviewed.payload.get("reviewer", ""))
        risk_justification = str(risk_reviewed.payload.get("justification", ""))

    approver = ""
    decision = ""
    justification = ""
    scope = ""
    assessment_id = ""
    approved_risk_id = ""
    approved_dataset_commitment = ""
    if human_approved:
        scope = str(human_approved.payload.get("scope", ""))
        decision = str(human_approved.payload.get("decision", ""))
        approver = str(human_approved.payload.get("approver", ""))
        justification = str(human_approved.payload.get("justification", ""))
        assessment_id = str(human_approved.payload.get("assessment_id", ""))
        approved_risk_id = str(human_approved.payload.get("risk_id", ""))
        approved_dataset_commitment = str(
            human_approved.payload.get("dataset_governance_commitment", "")
        )

    promoted_reason = ""
    promoted_artifact_path = ""
    approved_human_event_id = ""
    if model_promoted:
        promoted_reason = str(model_promoted.payload.get("promotion_reason", ""))
        promoted_artifact_path = str(model_promoted.payload.get("artifact_path", ""))
        approved_human_event_id = str(
            model_promoted.payload.get("approved_human_event_id", "")
        )

    report_dir = repo_root / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{run_id}.md"

    lines: List[str] = []

    lines.append(f"# Audit report for run `{run_id}`")
    lines.append("")
    lines.append("run_id=" + run_id)
    lines.append("bundle_sha256=" + bundle_sha256)
    lines.append("policy_version=" + (policy_version or ""))
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    ids = bundle.get("identifiers")
    if isinstance(ids, dict):
        ais = ids.get("ai_system_id")
        did = ids.get("dataset_id")
        mvid = ids.get("model_version_id")
        prid = ids.get("primary_risk_id")
        if not isinstance(prid, str):
            prid = ids.get("risk_id")
        rlist = ids.get("risk_ids")
        if isinstance(prid, str) or isinstance(ais, str) or isinstance(did, str) or isinstance(mvid, str):
            lines.append("### Canonical identifiers (bundle)")
            lines.append("")
            if isinstance(ais, str) and ais:
                lines.append(f"- `ai_system_id`: `{_md_escape(ais)}`")
            if isinstance(did, str) and did:
                lines.append(f"- `dataset_id`: `{_md_escape(did)}`")
            if isinstance(mvid, str) and mvid:
                lines.append(f"- `model_version_id`: `{_md_escape(mvid)}`")
            if isinstance(prid, str) and prid:
                lines.append(f"- `primary_risk_id`: `{_md_escape(prid)}`")
            if isinstance(rlist, list) and rlist:
                lines.append(f"- `risk_ids`: `{_md_escape(', '.join(str(x) for x in rlist))}`")
            lines.append("")
    lines.append(f"- System: `{_md_escape(system)}`")
    lines.append(f"- Actor: `{_md_escape(actor)}`")
    lines.append(f"- Policy version: `{_md_escape(policy_version)}`")
    lines.append(f"- Evidence bundle: `docs/evidence/{run_id}.json`")
    lines.append(f"- Evidence bundle SHA256: `{_md_escape(bundle_sha256)}`")
    if artifact_path:
        lines.append(f"- Model artifact (reported): `{_md_escape(artifact_path)}`")
    lines.append("")

    lines.append("## Traceability")
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Dataset | `{_md_escape(dataset)}` |")
    lines.append(f"| Dataset fingerprint | `{_md_escape(dataset_fp)}` |")
    if dataset_version:
        lines.append(f"| Dataset version | `{_md_escape(dataset_version)}` |")
    if dataset_governance_commitment:
        lines.append(
            f"| Dataset governance commitment | `{_md_escape(dataset_governance_commitment)}` |"
        )
    if governance_status:
        lines.append(f"| Governance status | `{_md_escape(governance_status)}` |")
    lines.append(f"| Rows | `{_md_escape(n_rows)}` |")
    lines.append(f"| Features | `{_md_escape(n_features)}` |")
    lines.append("")

    lines.append("## Risk review register")
    lines.append("")
    lines.append(
        "| Risk ID | Risk class | Severity | Likelihood | Status | Owner | Mitigation | Review decision | Reviewer | Justification |"
    )
    lines.append("|---|---|---:|---:|---|---|---|---|---|---|")
    lines.append(
        f"| `{_md_escape(risk_id)}` | `{_md_escape(risk_class)}` | `{_md_escape(severity)}` | `{_md_escape(likelihood)}` | `{_md_escape(risk_status)}` | `{_md_escape(owner)}` | `{_md_escape(mitigation)}` | `{_md_escape(risk_decision)}` | `{_md_escape(risk_reviewer)}` | `{_md_escape(risk_justification)}` |"
    )
    lines.append("")

    lines.append("## Evaluation gate")
    lines.append("")
    lines.append("| Metric | Value | Threshold | Passed |")
    lines.append("|---|---:|---:|---|")
    lines.append(
        f"| `{_md_escape(metric)}` | `{_md_escape(value)}` | `{_md_escape(threshold)}` | `{_md_escape(passed)}` |"
    )
    lines.append("")

    lines.append("## Human approval gate")
    lines.append("")
    lines.append("| Scope | Decision | Approver | Justification |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| `{_md_escape(scope)}` | `{_md_escape(decision)}` | `{_md_escape(approver)}` | `{_md_escape(justification)}` |"
    )
    lines.append("")

    if assessment_id or approved_risk_id or approved_dataset_commitment:
        lines.append("### Approval linkage fields")
        lines.append("")
        lines.append(f"- Assessment ID: `{_md_escape(assessment_id)}`")
        lines.append(f"- Risk ID: `{_md_escape(approved_risk_id)}`")
        lines.append(f"- Dataset governance commitment: `{_md_escape(approved_dataset_commitment)}`")
        lines.append("")

    lines.append("## Promotion")
    lines.append("")
    lines.append(f"- Promotion reason: `{_md_escape(promoted_reason)}`")
    if promoted_artifact_path:
        lines.append(f"- Artifact path: `{_md_escape(promoted_artifact_path)}`")
    if approved_human_event_id:
        lines.append(f"- Approved human event id: `{_md_escape(approved_human_event_id)}`")
    lines.append("")

    lines.append("## Event timeline")
    lines.append("")
    lines.append("| Time (UTC) | Event | Event id |")
    lines.append("|---|---|---|")
    for e in sorted(events, key=lambda x: x.ts_utc):
        lines.append(
            f"| `{_md_escape(e.ts_utc)}` | `{_md_escape(e.event_type)}` | `{_md_escape(e.event_id)}` |"
        )
    lines.append("")

    if log_path:
        lines.append("## Audit log reference")
        lines.append("")
        lines.append(f"- Log path (reported by server): `{_md_escape(log_path)}`")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"saved {report_path}")


if __name__ == "__main__":
    main()
