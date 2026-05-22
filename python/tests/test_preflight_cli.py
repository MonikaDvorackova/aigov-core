from __future__ import annotations

import json
from typing import Any

import pytest

from aigov_py import cli_exit
from aigov_py.cli import main


def test_preflight_local_evidence_pack_passes_without_audit_env(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["preflight", "--local-only"])
    out = capsys.readouterr()
    assert code == cli_exit.EX_OK
    assert "Preflight: local evidence pack" in out.out
    assert out.out.strip().endswith("PASS")
    # local-only: no audit section.
    assert "Preflight: audit service" not in out.out


def test_doctor_is_deprecated_alias_of_preflight_and_warns_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["doctor", "--local-only"])
    out = capsys.readouterr()
    assert code == cli_exit.EX_OK
    assert "warning: 'govai doctor' is deprecated, use 'govai preflight'" in out.err
    assert "Preflight: local evidence pack" in out.out


def test_preflight_audit_ready_pass(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("GOVAI_AUDIT_BASE_URL", "http://audit.example")

    class FakeClient:
        def __init__(self, base_url: str, api_key: str | None = None, *, default_project: str | None = None) -> None:
            self.base_url = base_url
            self.api_key = api_key
            self.default_project = default_project

        def request_json(self, method: str, path: str, **_kwargs: Any) -> Any:
            assert method == "GET"
            assert path == "/ready"
            return {"ok": True}

    import aigov_py.cli as cli_mod

    monkeypatch.setattr(cli_mod, "GovAIClient", FakeClient)
    code = main(["preflight"])
    out = capsys.readouterr()
    assert code == cli_exit.EX_OK
    assert "Preflight: audit service" in out.out
    assert out.out.strip().endswith("PASS")


def test_preflight_audit_ready_fail(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("GOVAI_AUDIT_BASE_URL", "http://audit.example")

    class FakeClient:
        def __init__(self, base_url: str, api_key: str | None = None, *, default_project: str | None = None) -> None:
            self.base_url = base_url
            self.api_key = api_key
            self.default_project = default_project

        def request_json(self, method: str, path: str, **_kwargs: Any) -> Any:
            raise RuntimeError("boom")

    import aigov_py.cli as cli_mod

    monkeypatch.setattr(cli_mod, "GovAIClient", FakeClient)
    code = main(["preflight"])
    out = capsys.readouterr()
    assert code == cli_exit.EX_ERR
    assert "Preflight: audit service" in out.out
    assert "audit service not ready (/ready != 200)" in out.out
    assert out.out.strip().endswith("FAIL")


def test_preflight_submit_capability_pass(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("GOVAI_AUDIT_BASE_URL", "http://audit.example")
    monkeypatch.setenv("GOVAI_API_KEY", "k_test")
    monkeypatch.setenv("GOVAI_PROJECT", "ci")

    state: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, base_url: str, api_key: str | None = None, *, default_project: str | None = None) -> None:
            self.base_url = base_url
            self.api_key = api_key
            self.default_project = default_project

        def request_json(self, method: str, path: str, **kwargs: Any) -> Any:
            if method == "GET" and path == "/ready":
                return {"ok": True}
            if method == "GET" and path == "/bundle-hash":
                rid = str((kwargs.get("params") or {}).get("run_id") or "")
                return {"ok": True, "run_id": rid, "events_content_sha256": state.get("digest", "")}
            raise AssertionError(f"unexpected request {method} {path}")

    import aigov_py.cli as cli_mod

    monkeypatch.setattr(cli_mod, "GovAIClient", FakeClient)

    def fake_submit_evidence_bundle_events(_client: Any, *, bundle: Any, progress: Any = None) -> None:
        # Store expected digest so FakeClient can return it for /bundle-hash.
        run_id = str(bundle.get("run_id") or "")
        events = bundle.get("events") or []
        from aigov_py.portable_evidence_digest import portable_evidence_digest_v1

        state["digest"] = portable_evidence_digest_v1(run_id, list(events)).lower()

    monkeypatch.setattr(cli_mod.eag, "submit_evidence_bundle_events", fake_submit_evidence_bundle_events)
    code = main(["preflight", "--with-submit"])
    out = capsys.readouterr()
    assert code == cli_exit.EX_OK
    assert "Preflight: submit capability" in out.out
    assert out.out.strip().endswith("PASS")


def test_preflight_detects_manifest_mismatch(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("GOVAI_AUDIT_BASE_URL", raising=False)

    import aigov_py.cli as cli_mod

    real = cli_mod.generate_demo_golden_path

    def tampered_generate_demo_golden_path(*, run_id: str, output_dir: Any) -> Any:
        res = real(run_id=run_id, output_dir=output_dir)
        manifest_path = res.manifest_path
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert isinstance(manifest, dict)
        manifest["events_content_sha256"] = "0" * 64
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return res

    monkeypatch.setattr(cli_mod, "generate_demo_golden_path", tampered_generate_demo_golden_path)

    code = cli_mod.main(["preflight", "--local-only"])
    out = capsys.readouterr()
    assert code == cli_exit.EX_ERR
    assert "Preflight: local evidence pack" in out.out
    assert "evidence digest mismatch" in out.out
    assert out.out.strip().endswith("FAIL")


def test_preflight_without_audit_base_url_fails(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("GOVAI_AUDIT_BASE_URL", raising=False)
    code = main(["preflight"])
    out = capsys.readouterr()
    assert code == cli_exit.EX_USAGE
    assert "requires GOVAI_AUDIT_BASE_URL" in out.err


def test_preflight_local_only_without_audit_base_url_passes(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("GOVAI_AUDIT_BASE_URL", raising=False)
    code = main(["preflight", "--local-only"])
    out = capsys.readouterr()
    assert code == cli_exit.EX_OK
    assert "Preflight: audit service" not in out.out


def test_preflight_with_submit_without_api_key_fails_clearly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GOVAI_AUDIT_BASE_URL", "http://audit.example")
    monkeypatch.delenv("GOVAI_API_KEY", raising=False)
    code = main(["preflight", "--with-submit"])
    out = capsys.readouterr()
    assert code == cli_exit.EX_USAGE
    assert "requires GOVAI_API_KEY" in out.err


def test_doctor_alias_follows_default_behavior_and_warns(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("GOVAI_AUDIT_BASE_URL", raising=False)
    code = main(["doctor"])
    out = capsys.readouterr()
    assert code == cli_exit.EX_USAGE
    assert "warning: 'govai doctor' is deprecated, use 'govai preflight'" in out.err
    assert "requires GOVAI_AUDIT_BASE_URL" in out.err

