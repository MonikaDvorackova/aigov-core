from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from aigov_py import cli_exit
from aigov_py.cli import main
from aigov_py.demo_golden_path import generate_demo_golden_path
from aigov_py.portable_evidence_digest import portable_evidence_digest_v1
from aigov_py.prototype_domain import assessment_id_for_run, model_version_id_for_run, risk_id_for_run


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_demo_golden_path_outputs_expected_files(tmp_path: Path) -> None:
    out = tmp_path / "artefacts"
    with patch("aigov_py.cli.uuid.uuid4", return_value="00000000-0000-0000-0000-000000000001"):
        code = main(["demo-golden-path", "--output-dir", str(out)])
    assert code == cli_exit.EX_OK
    assert (out / "evidence_digest_manifest.json").is_file()
    assert (out / "00000000-0000-0000-0000-000000000001.json").is_file()


def test_demo_golden_path_creates_valid_structure(tmp_path: Path) -> None:
    out = tmp_path / "artefacts"
    rid = "00000000-0000-0000-0000-000000000002"
    with patch("aigov_py.cli.uuid.uuid4", return_value=rid):
        code = main(["demo-golden-path", "--output-dir", str(out)])
    assert code == cli_exit.EX_OK

    bundle = _read_json(out / f"{rid}.json")
    assert bundle["ok"] is True
    assert bundle["run_id"] == rid
    events = bundle["events"]
    assert isinstance(events, list)
    assert [e["event_type"] for e in events] == [
        "ai_discovery_reported",
        "data_registered",
        "model_trained",
        "evaluation_reported",
        "risk_recorded",
        "risk_mitigated",
        "risk_reviewed",
        "human_approved",
        "model_promoted",
    ]

    manifest = _read_json(out / "evidence_digest_manifest.json")
    assert manifest["run_id"] == rid
    sha = manifest.get("events_content_sha256")
    assert isinstance(sha, str)
    assert len(sha) == 64
    assert sha == portable_evidence_digest_v1(rid, events).lower()


def test_demo_golden_path_linkage_fields_match_policy(tmp_path: Path) -> None:
    """Payloads include linkage required by rust/src/policy.rs for human_approved and model_promoted."""
    rid = "00000000-0000-0000-0000-000000000099"
    res = generate_demo_golden_path(run_id=rid, output_dir=tmp_path / "gp")
    bundle = _read_json(res.bundle_path)

    mvi = model_version_id_for_run(rid)
    aid = assessment_id_for_run(rid)
    rsk = risk_id_for_run(rid)
    commitment = "basic_compliance"

    human = next(e for e in bundle["events"] if e["event_type"] == "human_approved")
    mp = next(e for e in bundle["events"] if e["event_type"] == "model_promoted")
    hp = human["payload"]
    pp = mp["payload"]

    for ev in (human, mp):
        assert ev["run_id"] == rid

    assert hp["assessment_id"] == aid
    assert hp["risk_id"] == rsk
    assert hp["dataset_governance_commitment"] == commitment
    assert hp["ai_system_id"] == "golden-path-ai-system"
    assert hp["dataset_id"] == "golden-path-dataset-v1"
    assert hp["model_version_id"] == mvi

    assert pp["approved_human_event_id"] == human["event_id"]
    assert pp["assessment_id"] == aid
    assert pp["risk_id"] == rsk
    assert pp["dataset_governance_commitment"] == commitment
    assert pp["ai_system_id"] == "golden-path-ai-system"
    assert pp["dataset_id"] == "golden-path-dataset-v1"
    assert pp["model_version_id"] == mvi


def _normalize_bundle(bundle: dict) -> dict:
    """Remove run-id derived values so we can compare deterministic structure."""
    b = json.loads(json.dumps(bundle))
    rid = b.get("run_id")
    b["run_id"] = "<run_id>"
    for e in b.get("events", []):
        if isinstance(e, dict):
            e["run_id"] = "<run_id>"
            if isinstance(e.get("event_id"), str) and rid and rid in e["event_id"]:
                e["event_id"] = e["event_id"].replace(rid, "<run_id>")
            p = e.get("payload")
            if isinstance(p, dict):
                for k, v in list(p.items()):
                    if isinstance(v, str) and rid and rid in v:
                        p[k] = v.replace(rid, "<run_id>")
    return b


def _normalize_manifest(manifest: dict) -> dict:
    m = json.loads(json.dumps(manifest))
    m["run_id"] = "<run_id>"
    # Digest is expected to differ because run_id is part of the portable digest envelope.
    m["events_content_sha256"] = "<digest>"
    return m


def test_demo_golden_path_is_deterministic_except_run_id(tmp_path: Path) -> None:
    out1 = tmp_path / "a1"
    out2 = tmp_path / "a2"
    rid1 = "00000000-0000-0000-0000-000000000003"
    rid2 = "00000000-0000-0000-0000-000000000004"

    with patch("aigov_py.cli.uuid.uuid4", side_effect=[rid1, rid2]):
        code1 = main(["demo-golden-path", "--output-dir", str(out1)])
        code2 = main(["demo-golden-path", "--output-dir", str(out2)])
    assert code1 == cli_exit.EX_OK
    assert code2 == cli_exit.EX_OK

    b1 = _read_json(out1 / f"{rid1}.json")
    b2 = _read_json(out2 / f"{rid2}.json")
    assert _normalize_bundle(b1) == _normalize_bundle(b2)

    m1 = _read_json(out1 / "evidence_digest_manifest.json")
    m2 = _read_json(out2 / "evidence_digest_manifest.json")
    assert _normalize_manifest(m1) == _normalize_manifest(m2)
