from __future__ import annotations

import json
import subprocess
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, check=False)


def test_disaster_recovery_ledger_verify_round_trip(tmp_path: Path) -> None:
    sys.path.insert(0, str(SCRIPTS))
    from disaster_recovery_ledger import compute_record_hash, verify_ledger_file

    event_json = json.dumps({"event_id": "e1", "event_type": "test", "run_id": "r1"})
    prev = "GENESIS"
    rh = compute_record_hash(prev, event_json)
    line = json.dumps({"prev_hash": prev, "record_hash": rh, "event_json": event_json}) + "\n"
    ledger = tmp_path / "t.jsonl"
    ledger.write_text(line, encoding="utf-8")
    rep = verify_ledger_file(ledger)
    assert rep["ok"] is True
    assert rep["record_count"] == 1


def test_backup_and_verify_scripts(tmp_path: Path) -> None:
    sys.path.insert(0, str(SCRIPTS))
    from disaster_recovery_ledger import compute_record_hash

    led_dir = tmp_path / "led"
    led_dir.mkdir()
    event_json = json.dumps({"event_id": "e1", "event_type": "test", "run_id": "r1"})
    rh = compute_record_hash("GENESIS", event_json)
    line = json.dumps({"prev_hash": "GENESIS", "record_hash": rh, "event_json": event_json}) + "\n"
    (led_dir / "tenant-a.jsonl").write_text(line, encoding="utf-8")

    arch = tmp_path / "b.tar.gz"
    r1 = _run([sys.executable, str(SCRIPTS / "backup_audit_ledger.py"), "--ledger-dir", str(led_dir), "--output", str(arch)])
    assert r1.returncode == 0, r1.stderr + r1.stdout
    out = json.loads(r1.stdout)
    assert out["ok"] is True

    assert tarfile.is_tarfile(str(arch))
    r2 = _run([sys.executable, str(SCRIPTS / "verify_audit_backup.py"), "--archive", str(arch)])
    assert r2.returncode == 0, r2.stderr + r2.stdout

    r3 = _run(
        [
            sys.executable,
            str(SCRIPTS / "restore_drill_check.py"),
            "--ledger-file",
            str(led_dir / "tenant-a.jsonl"),
        ]
    )
    assert r3.returncode == 0, r3.stderr + r3.stdout


def test_backup_postgres_metadata_stub() -> None:
    r = _run([sys.executable, str(SCRIPTS / "backup_postgres_metadata.py")])
    assert r.returncode == 0
    doc = json.loads(r.stdout)
    assert doc["ok"] is True


def test_evidence_map_check() -> None:
    r = _run([sys.executable, str(SCRIPTS / "evidence_map_check.py")])
    assert r.returncode == 0, r.stderr


def test_security_program_check() -> None:
    r = _run([sys.executable, str(SCRIPTS / "security_program_check.py")])
    assert r.returncode == 0, r.stderr


def test_makefile_declares_stabilization_targets() -> None:
    text = (REPO / "Makefile").read_text(encoding="utf-8")
    for t in (
        "stabilization-readiness-check",
        "disaster-recovery-check",
        "evidence-map-check",
        "security-program-check",
        "runtime-audit-metrics-check",
    ):
        assert t in text, f"missing Makefile target {t!r}"
