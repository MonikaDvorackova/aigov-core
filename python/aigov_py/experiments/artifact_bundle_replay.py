"""
Experiment 2: end-to-end artifact-bound replay.

Writes concrete ``{run_id}.json`` bundles, ``evidence_digest_manifest.json``,
and ``audit_export.json`` under per-run directories, computes
``portable_evidence_digest_v1`` from on-disk bundle bytes, and evaluates the
closed-schema decision gate against ``artifact_bundle_replay_rubric.json``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aigov_py.experiments.gate_model import decision_gate_verdict_from_fields
from aigov_py.portable_evidence_digest import portable_evidence_digest_v1

_RUBRIC_PATH = Path(__file__).resolve().with_name("artifact_bundle_replay_rubric.json")

REPLICATES_PER_SCENARIO = 25
SCENARIO_ORDER: tuple[str, ...] = (
    "valid_complete_trace",
    "digest_mismatch_events_only",
    "digest_mismatch_export_only",
    "missing_evidence_pack",
    "failed_compliance_evaluation",
    "missing_approval_record",
    "reordered_required_events",
    "policy_version_mismatch",
)


def load_replay_rubric() -> dict[str, Any]:
    raw = json.loads(_RUBRIC_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("scenarios"), list):
        raise TypeError("artifact_bundle_replay_rubric.json")
    return raw


def expected_for_replay(scenario_name: str) -> str:
    for row in load_replay_rubric()["scenarios"]:
        if str(row["scenario_name"]) == scenario_name:
            ev = str(row["expected_verdict"])
            if ev not in ("VALID", "INVALID", "BLOCKED"):
                raise TypeError(ev)
            return ev
    raise KeyError(scenario_name)


def _event(
    *,
    event_id: str,
    event_type: str,
    ts_utc: str,
    run_id: str,
    payload: dict[str, Any],
    environment: str = "ci",
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "ts_utc": ts_utc,
        "actor": "ci",
        "system": "replay_harness",
        "run_id": run_id,
        "environment": environment,
        "payload": payload,
    }


def _base_events_good(run_id: str) -> list[dict[str, Any]]:
    return [
        _event(
            event_id=f"{run_id}-disc",
            event_type="ai_discovery_reported",
            ts_utc="2026-01-01T00:00:01Z",
            run_id=run_id,
            payload={"openai": False, "transformers": True},
        ),
        _event(
            event_id=f"{run_id}-eval",
            event_type="evaluation_reported",
            ts_utc="2026-01-01T00:00:02Z",
            run_id=run_id,
            payload={"passed": True},
        ),
        _event(
            event_id=f"{run_id}-hum",
            event_type="human_approved",
            ts_utc="2026-01-01T00:00:03Z",
            run_id=run_id,
            payload={"decision": "approve"},
        ),
    ]


def _events_failed_eval(run_id: str) -> list[dict[str, Any]]:
    return [
        _event(
            event_id=f"{run_id}-disc",
            event_type="ai_discovery_reported",
            ts_utc="2026-01-01T00:00:01Z",
            run_id=run_id,
            payload={"openai": False},
        ),
        _event(
            event_id=f"{run_id}-eval",
            event_type="evaluation_reported",
            ts_utc="2026-01-01T00:00:02Z",
            run_id=run_id,
            payload={"passed": False},
        ),
        _event(
            event_id=f"{run_id}-hum",
            event_type="human_approved",
            ts_utc="2026-01-01T00:00:03Z",
            run_id=run_id,
            payload={"decision": "approve"},
        ),
    ]


def _events_missing_approval(run_id: str) -> list[dict[str, Any]]:
    return [
        _event(
            event_id=f"{run_id}-disc",
            event_type="ai_discovery_reported",
            ts_utc="2026-01-01T00:00:01Z",
            run_id=run_id,
            payload={"openai": False},
        ),
        _event(
            event_id=f"{run_id}-eval",
            event_type="evaluation_reported",
            ts_utc="2026-01-01T00:00:02Z",
            run_id=run_id,
            payload={"passed": True},
        ),
    ]


def _events_reordered_pair(run_id: str) -> list[dict[str, Any]]:
    a = _event(
        event_id=f"{run_id}-a",
        event_type="ai_discovery_reported",
        ts_utc="2026-01-01T00:00:01Z",
        run_id=run_id,
        payload={"slot": "a"},
    )
    b = _event(
        event_id=f"{run_id}-b",
        event_type="evaluation_reported",
        ts_utc="2026-01-01T00:00:02Z",
        run_id=run_id,
        payload={"passed": True},
    )
    c = _event(
        event_id=f"{run_id}-hum",
        event_type="human_approved",
        ts_utc="2026-01-01T00:00:03Z",
        run_id=run_id,
        payload={"decision": "approve"},
    )
    return [b, a, c]


def _bundle_doc(
    run_id: str, events: list[dict[str, Any]], *, policy_version: str = "v1"
) -> dict[str, Any]:
    return {
        "ok": True,
        "run_id": run_id,
        "policy_version": policy_version,
        "events": events,
    }


def _write_manifest(artifact_dir: Path, run_id: str, events_hex: str) -> None:
    manifest = {
        "schema": "aigov.evidence_digest_manifest.v1",
        "run_id": run_id,
        "events_content_sha256": events_hex.lower(),
    }
    (artifact_dir / "evidence_digest_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_export(
    artifact_dir: Path,
    run_id: str,
    *,
    events_hex: str,
    bundle_sha256: str,
    root_policy_version: str,
    run_policy_version: str,
) -> None:
    export = {
        "schema_version": "aigov.audit_export.v1",
        "policy_version": root_policy_version,
        "run": {"run_id": run_id, "policy_version": run_policy_version},
        "evidence_hashes": {
            "bundle_sha256": bundle_sha256.lower(),
            "events_content_sha256": events_hex.lower(),
        },
    }
    (artifact_dir / "audit_export.json").write_text(
        json.dumps(export, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _bundle_sha256_file(bundle_path: Path) -> str:
    return hashlib.sha256(bundle_path.read_bytes()).hexdigest()


def materialize_scenario(
    *,
    scenario: str,
    artifact_dir: Path,
    run_id: str,
) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)

    if scenario == "missing_evidence_pack":
        evs = _base_events_good(run_id)
        digest = portable_evidence_digest_v1(run_id, evs)
        _write_manifest(artifact_dir, run_id, digest)
        bogus = _bundle_sha256_file(Path(__file__))
        _write_export(
            artifact_dir,
            run_id,
            events_hex=digest,
            bundle_sha256=bogus,
            root_policy_version="v1",
            run_policy_version="v1",
        )
        return

    if scenario == "failed_compliance_evaluation":
        evs = _events_failed_eval(run_id)
    elif scenario == "missing_approval_record":
        evs = _events_missing_approval(run_id)
    elif scenario == "reordered_required_events":
        evs = _events_reordered_pair(run_id)
    else:
        evs = _base_events_good(run_id)

    bundle_policy = "v1"
    bundle = _bundle_doc(run_id, evs, policy_version=bundle_policy)
    bundle_path = artifact_dir / f"{run_id}.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
    digest = portable_evidence_digest_v1(run_id, evs)

    if scenario == "digest_mismatch_events_only":
        _write_manifest(artifact_dir, run_id, "0" * 64)
    else:
        _write_manifest(artifact_dir, run_id, digest)

    bsha = _bundle_sha256_file(bundle_path)

    if scenario == "digest_mismatch_export_only":
        export_hex = ("ff" * 32) if digest != ("ff" * 32) else ("ee" * 32)
        export_root_pol = "v1"
        export_run_pol = "v1"
    elif scenario == "policy_version_mismatch":
        export_hex = digest
        export_root_pol = "v2"
        export_run_pol = "v2"
    else:
        export_hex = digest
        export_root_pol = "v1"
        export_run_pol = "v1"

    _write_export(
        artifact_dir,
        run_id,
        events_hex=export_hex,
        bundle_sha256=bsha,
        root_policy_version=export_root_pol,
        run_policy_version=export_run_pol,
    )


def derive_fields_from_artifacts(scenario: str, artifact_dir: Path, run_id: str) -> dict[str, Any]:
    bundle_path = artifact_dir / f"{run_id}.json"
    evidence_pack_present = bundle_path.is_file()
    events: list[dict[str, Any]] = []
    if evidence_pack_present:
        doc = json.loads(bundle_path.read_text(encoding="utf-8"))
        raw = doc.get("events")
        if isinstance(raw, list):
            events = [dict(e) for e in raw if isinstance(e, dict)]

    computed = portable_evidence_digest_v1(run_id, events) if events else ""
    manifest_hex = ""
    mp = artifact_dir / "evidence_digest_manifest.json"
    if mp.is_file():
        man = json.loads(mp.read_text(encoding="utf-8"))
        manifest_hex = str(man.get("events_content_sha256") or "").strip().lower()

    events_content_sha256_match = bool(computed) and computed == manifest_hex

    export_hex = ""
    export_policy = ""
    bundle_policy = ""
    bundle_sha256_exp = ""
    if bundle_path.is_file():
        bundle_policy = str(
            json.loads(bundle_path.read_text(encoding="utf-8")).get("policy_version") or "v1"
        )
    ep = artifact_dir / "audit_export.json"
    if ep.is_file():
        ex = json.loads(ep.read_text(encoding="utf-8"))
        eh = ex.get("evidence_hashes") if isinstance(ex.get("evidence_hashes"), dict) else {}
        export_hex = str(eh.get("events_content_sha256") or "").strip().lower()
        bundle_sha256_exp = str(eh.get("bundle_sha256") or "").strip().lower()
        export_policy = str((ex.get("run") or {}).get("policy_version") or "").strip()

    export_digest_match = (
        bool(manifest_hex)
        and bool(export_hex)
        and export_hex == manifest_hex
        and export_hex == computed
    )

    policy_version_match = bundle_policy == export_policy if bundle_policy and export_policy else True

    actual_bundle_sha = _bundle_sha256_file(bundle_path) if evidence_pack_present else ""
    artifact_bound_verification = (
        evidence_pack_present
        and events_content_sha256_match
        and export_digest_match
        and bool(bundle_sha256_exp)
        and actual_bundle_sha == bundle_sha256_exp
    )

    eval_pass = True
    for e in events:
        if e.get("event_type") == "evaluation_reported":
            eval_pass = bool(e.get("payload", {}).get("passed", False))

    approval = "missing"
    for e in reversed(events):
        if e.get("event_type") == "human_approved":
            if str(e.get("payload", {}).get("decision")) == "approve":
                approval = "granted"
            else:
                approval = "denied"
            break

    ai_discovery_present = any(e.get("event_type") == "ai_discovery_reported" for e in events)
    evidence_complete = ai_discovery_present and any(
        e.get("event_type") == "evaluation_reported" for e in events
    )

    return {
        "model_validation": "passed",
        "evidence_complete": evidence_complete,
        "ai_discovery_present": ai_discovery_present,
        "evaluation_result": "fail" if not eval_pass else "pass",
        "evaluation_internal_consistent": True,
        "approval": approval,
        "trace_consistent": True,
        "run_available": True,
        "evidence_pack_present": evidence_pack_present,
        "events_content_sha256_match": events_content_sha256_match,
        "export_digest_match": export_digest_match,
        "artifact_bound_verification": artifact_bound_verification,
        "policy_version_match": policy_version_match,
        "approval_is_stale": False,
        "causal_evaluation_before_approval": True,
        "run_id_matches_decision_scope": True,
    }


@dataclass(frozen=True)
class ReplayRun:
    run_id: str
    scenario: str
    artifact_dir: str
    gate_verdict: str
    expected_verdict: str
    gate_matches_rubric: bool


def generate_replay_runs(*, root: Path, replicates: int = REPLICATES_PER_SCENARIO) -> list[ReplayRun]:
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    out: list[ReplayRun] = []
    idx = 0
    for scenario in SCENARIO_ORDER:
        expected = expected_for_replay(scenario)
        for rep in range(replicates):
            idx += 1
            run_id = f"abr-{scenario[:8]}-{idx:04d}"
            adir = root / scenario / f"rep_{rep:02d}_{run_id}"
            materialize_scenario(scenario=scenario, artifact_dir=adir, run_id=run_id)
            fields = derive_fields_from_artifacts(scenario, adir, run_id)
            gate = decision_gate_verdict_from_fields(fields)
            out.append(
                ReplayRun(
                    run_id=run_id,
                    scenario=scenario,
                    artifact_dir=str(adir),
                    gate_verdict=gate,
                    expected_verdict=expected,
                    gate_matches_rubric=(gate == expected),
                )
            )
    return out


def write_latex_replay_table(out_dir: Path, runs: list[ReplayRun]) -> Path:
    """NeurIPS-ready compact table: scenario, expected verdict, gate metric, per-scenario accuracy."""

    def esc(s: str) -> str:
        return (
            s.replace("\\", "\\textbackslash{}")
            .replace("_", "\\_")
            .replace("%", "\\%")
            .replace("&", "\\&")
        )

    by_scen: dict[str, list[ReplayRun]] = defaultdict(list)
    for r in runs:
        by_scen[r.scenario].append(r)

    lines: list[str] = []
    lines.append("\\begin{tabular}{lccc}")
    lines.append("\\toprule")
    lines.append("Scenario & Expected & Gate det./ret. & Acc. \\\\")
    lines.append("\\midrule")

    for scen in SCENARIO_ORDER:
        xs = by_scen[scen]
        if not xs:
            continue
        exp = xs[0].expected_verdict
        n = len(xs)
        if exp == "VALID":
            retention = sum(1 for r in xs if r.gate_verdict == "VALID") / n
            metric = f"{retention:.2f}"
        else:
            detection = sum(1 for r in xs if r.gate_verdict != "VALID") / n
            metric = f"{detection:.2f}"
        acc = sum(1 for r in xs if r.gate_matches_rubric) / n
        lines.append(
            f"{esc(scen)} & {esc(exp)} & {metric} & {acc:.2f} \\\\"
        )

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    path = out_dir / "artifact_bundle_replay_table.tex"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def summarize_replay(runs: list[ReplayRun]) -> dict[str, Any]:
    correct = sum(1 for r in runs if r.gate_matches_rubric)
    return {
        "total_runs": len(runs),
        "verdict_classification_accuracy": correct / len(runs) if runs else 0.0,
        "scenario_count": len(SCENARIO_ORDER),
        "replicates_per_scenario": REPLICATES_PER_SCENARIO,
    }


def write_outputs(
    *,
    out_dir: Path,
    artifact_root: Path | None = None,
    runs: list[ReplayRun] | None = None,
) -> dict[str, str]:
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    art_root = artifact_root or (out_dir / "artifact_bundle_replay_artifacts")
    if runs is None:
        if art_root.exists():
            shutil.rmtree(art_root)
        runs = generate_replay_runs(root=art_root)

    summary = summarize_replay(runs)
    payload = {
        "runs": [asdict(r) for r in runs],
        "summary": summary,
        "rubric": load_replay_rubric(),
    }
    json_path = out_dir / "artifact_bundle_replay.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")

    csv_path = out_dir / "artifact_bundle_replay.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(
            handle,
            fieldnames=list(asdict(runs[0]).keys()) if runs else [],
        )
        if runs:
            w.writeheader()
            for r in runs:
                w.writerow(asdict(r))

    shutil.copyfile(_RUBRIC_PATH, out_dir / "artifact_bundle_replay_rubric.json")

    tex_replay = write_latex_replay_table(out_dir, runs)

    summary_csv = out_dir / "artifact_bundle_replay_summary.csv"
    with open(summary_csv, "w", encoding="utf-8", newline="") as handle:
        wr = csv.DictWriter(handle, fieldnames=["metric", "value"])
        wr.writeheader()
        for k, v in summary.items():
            wr.writerow({"metric": k, "value": str(v)})

    return {
        "json": str(json_path),
        "csv": str(csv_path),
        "summary_csv": str(summary_csv),
        "artifacts": str(art_root),
        "rubric_copy": str(out_dir / "artifact_bundle_replay_rubric.json"),
        "tex_replay_table": str(tex_replay),
    }


def main_cli(*, output: Path, clean: bool = True) -> int:
    art = output / "artifact_bundle_replay_artifacts"
    if clean and art.exists():
        shutil.rmtree(art)
    paths = write_outputs(out_dir=output, artifact_root=art)
    print("Wrote:")
    for v in paths.values():
        print(f"  - {v}")
    return 0
