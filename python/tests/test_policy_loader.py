from __future__ import annotations

import json
from pathlib import Path

import pytest

from aigov_py import cli_exit
from aigov_py.cli import main
from aigov_py.policy_loader import load_policy_module, policy_identity, required_evidence_from_policy


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_valid_ai_act_example_loads() -> None:
    p = _repo_root() / "docs" / "policies" / "ai-act-high-risk.example.yaml"
    policy = load_policy_module(p)
    ident = policy_identity(policy)
    assert ident["id"] == "ai-act-high-risk"
    assert "AI Act" in ident["name"]
    assert ident["version"] == "0.1.0"


def test_valid_internal_policy_example_loads() -> None:
    p = _repo_root() / "docs" / "policies" / "internal-genai-policy.example.yaml"
    policy = load_policy_module(p)
    ident = policy_identity(policy)
    assert ident["id"] == "internal-genai-policy"
    assert "Internal" in ident["name"]
    assert ident["version"] == "2026-05-01"


def test_required_evidence_is_flat_deduped_and_sorted_when_rendered() -> None:
    p = _repo_root() / "docs" / "policies" / "ai-act-high-risk.example.yaml"
    policy = load_policy_module(p)
    ev = required_evidence_from_policy(policy)
    assert isinstance(ev, set)
    assert "evaluation_reported" in ev
    assert "human_approved" in ev

    rendered = sorted(ev)
    assert rendered == sorted(rendered)
    assert len(rendered) == len(set(rendered))


def test_missing_policy_id_fails(tmp_path: Path) -> None:
    y = tmp_path / "p.yaml"
    y.write_text(
        "\n".join(
            [
                "policy:",
                '  name: "X"',
                '  version: "1"',
                "requirements:",
                "  - code: R1",
                "    required_evidence:",
                "      - evaluation_reported",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"policy\.id"):
        _ = load_policy_module(y)


def test_missing_policy_version_fails(tmp_path: Path) -> None:
    y = tmp_path / "p.yaml"
    y.write_text(
        "\n".join(
            [
                "policy:",
                '  id: "x"',
                '  name: "X"',
                "requirements:",
                "  - code: R1",
                "    required_evidence:",
                "      - evaluation_reported",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"policy\.version"):
        _ = load_policy_module(y)


def test_requirement_without_required_evidence_fails(tmp_path: Path) -> None:
    y = tmp_path / "p.yaml"
    y.write_text(
        "\n".join(
            [
                "policy:",
                '  id: "x"',
                '  name: "X"',
                '  version: "1"',
                "requirements:",
                "  - code: R1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"required_evidence"):
        _ = load_policy_module(y)


def test_cli_policy_compile_prints_expected_evidence(capsys: pytest.CaptureFixture[str]) -> None:
    p = _repo_root() / "docs" / "policies" / "ai-act-high-risk.example.yaml"
    code = main(["policy", "compile", "--path", str(p)])
    assert code == cli_exit.EX_OK
    out_lines = [ln.strip() for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert out_lines == sorted(out_lines)
    assert "evaluation_reported" in out_lines
    assert "human_approved" in out_lines


def test_cli_policy_compile_json_prints_valid_json(capsys: pytest.CaptureFixture[str]) -> None:
    p = _repo_root() / "docs" / "policies" / "internal-genai-policy.example.yaml"
    code = main(["policy", "compile", "--path", str(p), "--json"])
    assert code == cli_exit.EX_OK
    raw = capsys.readouterr().out
    obj = json.loads(raw)
    assert obj["policy"]["id"] == "internal-genai-policy"
    assert obj["policy"]["version"] == "2026-05-01"
    assert isinstance(obj["required_evidence"], list)
    assert obj["required_evidence"] == sorted(obj["required_evidence"])
