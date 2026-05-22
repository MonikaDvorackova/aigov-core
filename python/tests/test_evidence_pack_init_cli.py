from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest

from aigov_py import cli_exit
from aigov_py.cli import main
from aigov_py.evidence_artifact_gate import load_bundle, load_manifest
from aigov_py.portable_evidence_digest import portable_evidence_digest_v1


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_evidence_pack_init_creates_required_files(tmp_path: Path) -> None:
    out = tmp_path / "pack"
    rid = "00000000-0000-0000-0000-000000000abc"
    code = main(["evidence-pack", "init", "--out", str(out), "--run-id", rid])
    assert code == cli_exit.EX_OK
    assert (out / "evidence_digest_manifest.json").is_file()
    assert (out / f"{rid}.json").is_file()


def test_evidence_pack_init_output_file_shape_contract(tmp_path: Path) -> None:
    out = tmp_path / "pack"
    rid = "00000000-0000-0000-0000-00000000f00d"
    code = main(["evidence-pack", "init", "--out", str(out), "--run-id", rid])
    assert code == cli_exit.EX_OK

    files = sorted(p.name for p in out.iterdir())
    assert len(files) == 2
    assert files == [f"{rid}.json", "evidence_digest_manifest.json"]

    bundle = _read_json(out / f"{rid}.json")
    assert "run_id" in bundle
    assert "events" in bundle
    assert isinstance(bundle["events"], list)

    manifest = _read_json(out / "evidence_digest_manifest.json")
    assert "schema" in manifest
    assert "run_id" in manifest
    assert "events_content_sha256" in manifest
    assert manifest["run_id"] == bundle["run_id"] == rid


def test_evidence_pack_init_manifest_matches_bundle_digest(tmp_path: Path) -> None:
    out = tmp_path / "pack"
    rid = "00000000-0000-0000-0000-000000000def"
    code = main(["evidence-pack", "init", "--out", str(out), "--run-id", rid])
    assert code == cli_exit.EX_OK

    bundle = _read_json(out / f"{rid}.json")
    events = bundle["events"]
    digest = portable_evidence_digest_v1(rid, events).lower()

    manifest = _read_json(out / "evidence_digest_manifest.json")
    assert manifest["schema"] == "aigov.evidence_digest_manifest.v1"
    assert manifest["run_id"] == rid
    assert manifest["events_content_sha256"] == digest


def test_evidence_pack_init_is_consumable_by_existing_pack_loaders(tmp_path: Path) -> None:
    out = tmp_path / "pack"
    rid = "00000000-0000-0000-0000-000000000123"
    code = main(["evidence-pack", "init", "--out", str(out), "--run-id", rid])
    assert code == cli_exit.EX_OK

    bundle, bundle_path = load_bundle(rid, out)
    assert bundle_path == out / f"{rid}.json"
    assert bundle.get("run_id") == rid
    assert isinstance(bundle.get("events"), list)

    manifest = load_manifest(out)
    assert manifest.get("run_id") == rid


def test_evidence_pack_init_respects_default_run_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.delenv("GITHUB_RUN_ATTEMPT", raising=False)

    out = tmp_path / "pack"
    code = main(["evidence-pack", "init", "--out", str(out)])
    assert code == cli_exit.EX_OK
    assert (out / "evidence_digest_manifest.json").is_file()
    bundle_json = sorted(p for p in out.glob("*.json") if p.name != "evidence_digest_manifest.json")
    assert len(bundle_json) == 1
    rid = bundle_json[0].stem
    # Outside CI, default is uuid4; just validate it parses as a UUID.
    _ = UUID(rid)


def test_evidence_pack_init_is_deterministic_for_same_run_id(tmp_path: Path) -> None:
    rid = "00000000-0000-0000-0000-00000000cafe"
    out1 = tmp_path / "pack1"
    out2 = tmp_path / "pack2"

    code1 = main(["evidence-pack", "init", "--out", str(out1), "--run-id", rid])
    assert code1 == cli_exit.EX_OK
    code2 = main(["evidence-pack", "init", "--out", str(out2), "--run-id", rid])
    assert code2 == cli_exit.EX_OK

    assert (out1 / f"{rid}.json").read_bytes() == (out2 / f"{rid}.json").read_bytes()
    assert (out1 / "evidence_digest_manifest.json").read_bytes() == (out2 / "evidence_digest_manifest.json").read_bytes()


def test_evidence_pack_init_enforcement_semantics(tmp_path: Path) -> None:
    out = tmp_path / "pack"
    rid = "00000000-0000-0000-0000-00000000beef"
    code = main(["evidence-pack", "init", "--out", str(out), "--run-id", rid])
    assert code == cli_exit.EX_OK

    bundle = _read_json(out / f"{rid}.json")
    events = bundle["events"]
    assert isinstance(events, list)

    by_type: dict[str, dict] = {}
    for e in events:
        if isinstance(e, dict):
            et = e.get("event_type")
            if isinstance(et, str):
                by_type[et] = e

    for required in (
        "data_registered",
        "model_trained",
        "evaluation_reported",
        "human_approved",
        "model_promoted",
    ):
        assert required in by_type, f"missing required event_type: {required}"

    evaluation = by_type["evaluation_reported"]
    assert isinstance(evaluation.get("payload"), dict)
    assert evaluation["payload"].get("passed") is True

    human = by_type["human_approved"]
    promoted = by_type["model_promoted"]
    assert isinstance(promoted.get("payload"), dict)
    assert promoted["payload"].get("approved_human_event_id") == human.get("event_id")


def test_evidence_pack_init_existing_out_dir_fails_without_force_and_does_not_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "pack"
    out.mkdir(parents=True, exist_ok=True)

    sentinel_bundle = out / "sentinel.json"
    sentinel_manifest = out / "evidence_digest_manifest.json"
    sentinel_bundle.write_text('{"sentinel":true}\n', encoding="utf-8")
    sentinel_manifest.write_text('{"sentinel_manifest":true}\n', encoding="utf-8")
    bundle_before = sentinel_bundle.read_bytes()
    manifest_before = sentinel_manifest.read_bytes()

    code = main(["evidence-pack", "init", "--out", str(out)])
    assert code == cli_exit.EX_USAGE

    assert sentinel_bundle.read_bytes() == bundle_before
    assert sentinel_manifest.read_bytes() == manifest_before


def test_evidence_pack_init_default_run_id_is_ci_deterministic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")

    out = tmp_path / "pack"
    code = main(["evidence-pack", "init", "--out", str(out)])
    assert code == cli_exit.EX_OK

    rid = "ci-123-2"
    assert (out / f"{rid}.json").is_file()

