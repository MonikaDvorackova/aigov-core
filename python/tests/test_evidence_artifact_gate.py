from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from govai import GovAIAPIError, GovAIHTTPError

from aigov_py import cli_exit
from aigov_py.cli import main
from aigov_py import evidence_artifact_gate as eag


def test_canonicalize_evidence_event_dicts_deduplicates_so_latest_timestamp_wins() -> None:
    xs = [
        {"event_id": "a", "ts_utc": "t1", "event_type": "x"},
        {"event_id": "a", "ts_utc": "t2", "event_type": "x"},
    ]
    out = eag.canonicalize_evidence_event_dicts(xs)
    assert len(out) == 1
    assert out[0]["ts_utc"] == "t2"


def test_event_for_submit_strips_environment() -> None:
    ev = {"event_id": "1", "environment": "dev", "payload": {}, "run_id": "r"}
    assert "environment" not in eag.event_for_submit(ev)


def test_bundle_hash_digest_requires_events_content_sha256() -> None:
    cli = MagicMock()
    cli.request_json.return_value = {"ok": True, "bundle_sha256": "a" * 64}
    with pytest.raises(GovAIAPIError):
        eag.bundle_hash_digest(cli, "rid")


@pytest.fixture()
def artifact_dir(tmp_path: Path) -> Path:
    run_id = "rid-art"
    d = tmp_path / "art"
    d.mkdir(parents=True, exist_ok=True)
    bundle = {
        "ok": True,
        "run_id": run_id,
        "events": [
            {
                "event_id": "e1",
                "event_type": "ai_discovery_reported",
                "ts_utc": "2020-01-01T00:00:00Z",
                "actor": "ci",
                "system": "github_actions",
                "run_id": run_id,
                "payload": {"openai": False},
                "environment": "dev",
            }
        ],
    }
    (d / f"{run_id}.json").write_text(json.dumps(bundle), encoding="utf-8")
    (d / "evidence_digest_manifest.json").write_text(
        json.dumps(
            {"run_id": run_id, "events_content_sha256": ("ab" * 32)},
            indent=2,
        ),
        encoding="utf-8",
    )
    return d


def test_check_verify_artifacts_digest_mismatch_errors(
    artifact_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch("aigov_py.cli.GovAIClient") as gc:
        inst = MagicMock()
        gc.return_value = inst
        inst.request_json.return_value = {
            "ok": True,
            "events_content_sha256": "cd" * 32,
            "bundle_sha256": "ab" * 32,
            "policy_version": "v0_test",
            "run_id": "rid-art",
        }
        code = main(
            [
                "--audit-base-url",
                "http://audit.test",
                "check",
                "rid-art",
                "--verify-artifacts",
                str(artifact_dir),
            ]
        )
    assert code == cli_exit.EX_ERR
    err = capsys.readouterr().err
    assert "hosted events_content_sha256" in err.lower() or "expected=" in err


def test_fetch_export_evidence_hashes_returns_skip_reason_on_http_failure() -> None:
    cli = MagicMock()
    cli.request_json.side_effect = OSError("network down")
    got, reason = eag.fetch_export_evidence_hashes(cli, "r1")
    assert got is None
    assert reason == "export not available"


def test_submit_evidence_pack_missing_bundle_errors(tmp_path: Path) -> None:
    code = main(
        [
            "--audit-base-url",
            "http://audit.test",
            "submit-evidence-pack",
            "--path",
            str(tmp_path),
            "--run-id",
            "missing-only",
        ]
    )
    assert code == cli_exit.EX_ERR


def _dup_409_body(*, eid: str, rid: str) -> str:
    raw = f"duplicate event_id for run_id: event_id={eid} run_id={rid}"
    return json.dumps(
        {
            "ok": False,
            "error": {
                "code": "DUPLICATE_EVENT_ID",
                "message": "dup",
                "hint": "h",
                "details": {"raw": raw},
            },
        }
    )


def test_is_duplicate_event_id_idempotent_acceptance_matching_raw() -> None:
    body = _dup_409_body(eid="evt_x", rid="run_a")
    assert eag.is_duplicate_event_id_idempotent_acceptance(
        409,
        body,
        {"event_id": "evt_x", "run_id": "run_a"},
    )


def test_is_duplicate_event_id_idempotent_acceptance_matching_details_fields() -> None:
    payload = json.dumps(
        {
            "ok": False,
            "error": {
                "code": "DUPLICATE_EVENT_ID",
                "message": "dup",
                "details": {"event_id": "e1", "run_id": "r1"},
            },
        }
    )
    assert eag.is_duplicate_event_id_idempotent_acceptance(409, payload, {"event_id": "e1", "run_id": "r1"})


def test_is_duplicate_event_id_idempotent_acceptance_matching_message_pattern() -> None:
    raw_in_msg = "duplicate event_id for run_id: event_id=same run_id=rid"
    payload = json.dumps(
        {
            "ok": False,
            "error": {
                "code": "DUPLICATE_EVENT_ID",
                "message": raw_in_msg,
            },
        }
    )
    assert eag.is_duplicate_event_id_idempotent_acceptance(
        409, payload, {"event_id": "same", "run_id": "rid"}
    )


def test_is_duplicate_event_id_idempotent_acceptance_rejects_non_409() -> None:
    body = _dup_409_body(eid="evt_x", rid="run_a")
    assert not eag.is_duplicate_event_id_idempotent_acceptance(200, body, {"event_id": "evt_x", "run_id": "run_a"})


def test_is_duplicate_event_id_idempotent_acceptance_rejects_mismatch() -> None:
    body = _dup_409_body(eid="other", rid="run_a")
    assert not eag.is_duplicate_event_id_idempotent_acceptance(
        409, body, {"event_id": "evt_x", "run_id": "run_a"}
    )


def test_is_duplicate_event_id_idempotent_acceptance_rejects_wrong_409_code() -> None:
    payload = json.dumps({"ok": False, "error": {"code": "CONFLICT_OTHER", "message": "no"}})
    assert not eag.is_duplicate_event_id_idempotent_acceptance(
        409, payload, {"event_id": "e", "run_id": "r"}
    )


def test_is_duplicate_event_id_idempotent_acceptance_rejects_unparsable_conflict() -> None:
    body409 = json.dumps(
        {"ok": False, "error": {"code": "DUPLICATE_EVENT_ID", "message": "dup", "details": {}}},
    )
    assert not eag.is_duplicate_event_id_idempotent_acceptance(
        409, body409, {"event_id": "e1", "run_id": "run_a"}
    )


def _two_event_artifact_dir(tmp_path: Path) -> tuple[Path, str]:
    run_id = "rid-two"
    d = tmp_path / "pack"
    d.mkdir(parents=True, exist_ok=True)
    ev = {
        "event_type": "ai_discovery_reported",
        "ts_utc": "2020-01-01T00:00:00Z",
        "actor": "ci",
        "system": "github_actions",
        "run_id": run_id,
        "payload": {"openai": False},
    }
    promoted = {
        "event_type": "model_promoted",
        "ts_utc": "2020-01-01T00:02:00Z",
        "actor": "ci",
        "system": "github_actions",
        "run_id": run_id,
        "payload": {
            "artifact_path": "s3://bucket/model",
            "artifact_sha256": "11" * 32,
            "promotion_reason": "ok",
            "assessment_id": "a1",
            "risk_id": "r1",
            "dataset_governance_commitment": "c1",
            "approved_human_event_id": "h1",
            "ai_system_id": "ai1",
            "dataset_id": "d1",
            "model_version_id": "m1",
        },
    }
    bundle = {
        "ok": True,
        "run_id": run_id,
        "events": [
            {**ev, "event_id": "e1"},
            {**promoted, "event_id": "e2"},
        ],
    }
    (d / f"{run_id}.json").write_text(json.dumps(bundle), encoding="utf-8")
    from aigov_py.portable_evidence_digest import portable_evidence_digest_v1

    digest = portable_evidence_digest_v1(run_id, bundle["events"]).lower()
    (d / "evidence_digest_manifest.json").write_text(
        json.dumps({"run_id": run_id, "events_content_sha256": digest}, indent=2),
        encoding="utf-8",
    )
    return d, run_id


def test_submit_evidence_pack_duplicate_409_matching_ids_succeeds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact_dir, run_id = _two_event_artifact_dir(tmp_path)
    body409 = _dup_409_body(eid="e1", rid=run_id)
    err = GovAIHTTPError("HTTP 409", status_code=409, body_text=body409)

    def fake_submit(client: object, body: dict) -> dict:
        if str(body.get("event_id")) == "e1":
            raise err
        return {"ok": True, "record_hash": "x"}

    with patch("aigov_py.evidence_artifact_gate.submit_event", side_effect=fake_submit):
        code = main(
            [
                "--audit-base-url",
                "http://audit.test",
                "submit-evidence-pack",
                "--path",
                str(artifact_dir),
                "--run-id",
                run_id,
            ]
        )
    assert code == cli_exit.EX_OK
    out = capsys.readouterr().out
    assert "already submitted: e1" in out
    assert "submitted evidence pack" in out


def test_submit_evidence_pack_duplicate_409_mismatched_event_id_fails(tmp_path: Path) -> None:
    artifact_dir, run_id = _two_event_artifact_dir(tmp_path)
    body409 = _dup_409_body(eid="other_id", rid=run_id)
    err = GovAIHTTPError("HTTP 409", status_code=409, body_text=body409)

    def fake_submit(client: object, body: dict) -> dict:
        if str(body.get("event_id")) == "e1":
            raise err
        return {"ok": True}

    with patch("aigov_py.evidence_artifact_gate.submit_event", side_effect=fake_submit):
        code = main(
            [
                "--audit-base-url",
                "http://audit.test",
                "submit-evidence-pack",
                "--path",
                str(artifact_dir),
                "--run-id",
                run_id,
            ]
        )
    assert code == cli_exit.EX_ERR


def test_submit_evidence_pack_duplicate_409_missing_parseable_ids_fails(tmp_path: Path) -> None:
    artifact_dir, run_id = _two_event_artifact_dir(tmp_path)
    body409 = json.dumps(
        {
            "ok": False,
            "error": {
                "code": "DUPLICATE_EVENT_ID",
                "message": "dup",
                "hint": "h",
                "details": {},
            },
        }
    )
    err = GovAIHTTPError("HTTP 409", status_code=409, body_text=body409)

    with patch("aigov_py.evidence_artifact_gate.submit_event", side_effect=err):
        code = main(
            [
                "--audit-base-url",
                "http://audit.test",
                "submit-evidence-pack",
                "--path",
                str(artifact_dir),
                "--run-id",
                run_id,
            ]
        )
    assert code == cli_exit.EX_ERR


def test_verify_evidence_pack_still_runs_digest_after_idempotent_submit(tmp_path: Path) -> None:
    """Idempotent submit must not replace verify-evidence-pack; digest + verdict checks still run."""
    artifact_dir, run_id = _two_event_artifact_dir(tmp_path)
    body409 = _dup_409_body(eid="e1", rid=run_id)
    dup_err = GovAIHTTPError("HTTP 409", status_code=409, body_text=body409)

    def fake_submit(client: object, body: dict) -> dict:
        if str(body.get("event_id")) == "e1":
            raise dup_err
        return {"ok": True}

    digest_calls: list[str] = []

    def fake_bundle_hash_digest(cli: object, rid: str) -> dict:
        digest_calls.append(rid)
        manifest = json.loads((artifact_dir / "evidence_digest_manifest.json").read_text(encoding="utf-8"))
        return {"ok": True, "events_content_sha256": manifest["events_content_sha256"], "run_id": rid}

    with patch("aigov_py.evidence_artifact_gate.submit_event", side_effect=fake_submit):
        c_submit = main(
            [
                "--audit-base-url",
                "http://audit.test",
                "submit-evidence-pack",
                "--path",
                str(artifact_dir),
                "--run-id",
                run_id,
            ]
        )
    assert c_submit == cli_exit.EX_OK

    with (
        patch("aigov_py.cli.GovAIClient") as gc,
        patch("aigov_py.evidence_artifact_gate.bundle_hash_digest", side_effect=fake_bundle_hash_digest),
        patch("aigov_py.evidence_artifact_gate.fetch_export_evidence_hashes", return_value=(None, "skip")),
    ):
        inst = MagicMock()
        gc.return_value = inst
        inst.request_json.return_value = {"ok": True, "verdict": "VALID"}

        c_verify = main(
            [
                "--audit-base-url",
                "http://audit.test",
                "verify-evidence-pack",
                "--path",
                str(artifact_dir),
                "--run-id",
                run_id,
            ]
        )

    assert c_verify == cli_exit.EX_OK
    assert digest_calls == [run_id]
    inst.request_json.assert_called()
