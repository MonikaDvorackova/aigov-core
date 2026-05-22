from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        raise SystemExit(2)

    run_id = argv[1].strip()
    if not run_id:
        raise SystemExit(2)

    mode = os.environ.get("AIGOV_MODE", "ci")

    root = repo_root()
    reports = root / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    evidence_path = root / "docs" / "evidence" / f"{run_id}.json"
    if not evidence_path.exists():
        raise FileNotFoundError(f"Missing evidence file: {evidence_path}")

    report_path = reports / f"{run_id}.md"
    if report_path.exists():
        return

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    policy_version = evidence.get("policy_version")
    if not policy_version:
        raise SystemExit("policy_version missing in evidence")

    bundle_sha256 = sha256_file(evidence_path)

    content = "\n".join(
        [
            f"run_id={run_id}",
            f"bundle_sha256={bundle_sha256}",
            f"policy_version={policy_version}",
            f"aigov_mode={mode}",
            "",
            f"# Audit report for run `{run_id}`",
            "",
            f"generated_ts_utc={utc_now()}",
            "",
        ]
    )

    report_path.write_text(content, encoding="utf-8")
    print(f"saved {report_path}")


if __name__ == "__main__":
    main(sys.argv)
