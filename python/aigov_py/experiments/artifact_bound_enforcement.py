from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aigov_py.canonical_json import canonical_dumps
from aigov_py.experiments.gate_model import decision_gate_verdict_from_fields, make_base_fields


@dataclass(frozen=True)
class ArtifactScenario:
    name: str
    artifact_integrity: str
    field_overrides: dict[str, object]


def _digest(obj: object) -> str:
    return hashlib.sha256(canonical_dumps(obj).encode("utf-8")).hexdigest()


def _synthetic_events(*, run_id: str) -> list[dict[str, object]]:
    return [
        {
            "event_id": f"ev_reg_{run_id}",
            "event_type": "evidence_registered",
            "run_id": run_id,
            "payload": {"slot": "primary"},
        },
        {
            "event_id": f"ev_app_{run_id}",
            "event_type": "approval_recorded",
            "run_id": run_id,
            "payload": {"decision": "granted"},
        },
    ]


def scenario_definitions() -> list[ArtifactScenario]:
    return [
        ArtifactScenario(
            name="valid_correct_digest",
            artifact_integrity="ok",
            field_overrides={},
        ),
        ArtifactScenario(
            name="modified_event_body_digest_mismatch",
            artifact_integrity="modified",
            field_overrides={
                "events_content_sha256_match": False,
            },
        ),
        ArtifactScenario(
            name="missing_artifact_bundle",
            artifact_integrity="missing_bundle",
            field_overrides={
                "evidence_pack_present": False,
            },
        ),
        ArtifactScenario(
            name="reordered_events_same_digest",
            artifact_integrity="reordered_ok",
            field_overrides={},
        ),
    ]


def _merged_fields(sc: ArtifactScenario, *, run_id: str) -> dict[str, object]:
    fields = make_base_fields()
    fields.update(sc.field_overrides)
    events = _synthetic_events(run_id=run_id)
    Canon = _digest({"events": sorted(events, key=lambda e: str(e.get("event_id") or ""))})
    fields["event_content_sha256"] = Canon
    if sc.name == "reordered_events_same_digest":
        rev = list(reversed(events))
        assert _digest({"events": sorted(rev, key=lambda e: str(e.get("event_id") or ""))}) == Canon
    return fields


def gate_result_for_scenario(sc: ArtifactScenario, *, run_id: str) -> str:
    fields = _merged_fields(sc, run_id=run_id)
    return decision_gate_verdict_from_fields(fields)


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, sc in enumerate(scenario_definitions(), start=1):
        run_id = f"abe-{i:02d}"
        events = _synthetic_events(run_id=run_id)
        canon_digest = _digest(
            {"events": sorted(events, key=lambda e: str(e.get("event_id") or ""))}
        )
        gate = gate_result_for_scenario(sc, run_id=run_id)
        rows.append(
            {
                "scenario": sc.name,
                "artifact_integrity": sc.artifact_integrity,
                "gate_result": gate,
                "run_id": run_id,
                "event_content_sha256": canon_digest
                if sc.name != "modified_event_body_digest_mismatch"
                else f"{canon_digest}_altered",
            }
        )
    return rows


def write_outputs(out_dir: Path) -> dict[str, str]:
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = build_rows()
    proof = {
        "scenarios": rows,
        "note": "Gate uses events_content_sha256_match/export_digest_match fields from the auditability model; "
        "event_content_sha256 column documents synthetic canonical digest for the scenario.",
    }

    csv_path = out_dir / "artifact_bound_enforcement.csv"
    json_path = out_dir / "artifact_bound_enforcement.json"

    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(
            handle,
            fieldnames=["scenario", "artifact_integrity", "gate_result"],
        )
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "scenario": r["scenario"],
                    "artifact_integrity": r["artifact_integrity"],
                    "gate_result": r["gate_result"],
                }
            )

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(proof, handle, indent=2)

    return {"csv": str(csv_path), "json": str(json_path)}


def main_cli(output: Path) -> int:
    paths = write_outputs(output)
    for v in paths.values():
        print(f"Wrote: {v}")
    return 0
