from __future__ import annotations

from pathlib import Path

from aigov_py.experiments import artifact_bundle_replay as abr


def test_replay_rubric_accuracy_smoke(tmp_path: Path) -> None:
    runs = abr.generate_replay_runs(root=tmp_path / "art")
    assert len(runs) == 200
    s = abr.summarize_replay(runs)
    assert s["verdict_classification_accuracy"] == 1.0
    assert s["total_runs"] == 200
    assert all(r.gate_matches_rubric for r in runs)


def test_replay_writes_outputs(tmp_path: Path) -> None:
    out = tmp_path / "out"
    paths = abr.write_outputs(out_dir=out)
    assert Path(paths["json"]).is_file()
    assert Path(paths["tex_replay_table"]).is_file()
    assert len(list((out / "artifact_bundle_replay_artifacts").rglob("*.json"))) >= 200
