from __future__ import annotations

import json
from pathlib import Path

from aigov_py.discovery_scan import scan_repo


def test_scan_repo_v2_emits_required_fields(tmp_path: Path) -> None:
    # Create minimal signals
    (tmp_path / "requirements.txt").write_text("openai==1.0.0\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("from openai import OpenAI\nclient = OpenAI()\n", encoding="utf-8")
    (tmp_path / "model.onnx").write_bytes(b"\x00\x01")

    out = scan_repo(tmp_path, include_history=False)

    assert out["schema_version"] == "aigov.discovery_scan.v2"
    assert out["openai"] is True
    assert out["model_artifacts"] is True
    assert isinstance(out["findings"], list)
    assert len(out["findings"]) >= 2

    for f in out["findings"]:
        assert "detected_ai_usage" in f
        assert "file_path" in f
        assert "detector_type" in f
        assert "confidence" in f
        assert isinstance(f["confidence"], float)
        assert 0.0 <= f["confidence"] <= 1.0


def test_findings_are_json_serializable(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("transformers\n", encoding="utf-8")
    out = scan_repo(tmp_path, include_history=False)
    json.dumps(out)  # must not raise

