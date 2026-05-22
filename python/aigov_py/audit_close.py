from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit("Usage: python -m aigov_py.audit_close <RUN_ID>")

    run_id = argv[1].strip()
    if not run_id:
        raise SystemExit("RUN_ID is empty")

    root = repo_root()

    evidence = root / "docs" / "evidence" / f"{run_id}.json"
    report = root / "docs" / "reports" / f"{run_id}.md"
    bundle = root / "docs" / "packs" / f"{run_id}.zip"

    for p in (evidence, report, bundle):
        if not p.exists():
            raise FileNotFoundError(f"Missing required artifact: {p}")

    combined = (
        read_bytes(evidence)
        + b"\n"
        + read_bytes(report)
        + b"\n"
        + read_bytes(bundle)
    )

    audit_sha256 = sha256_bytes(combined)

    audit_out = root / "docs" / "audit" / f"{run_id}.json"
    audit_out.parent.mkdir(parents=True, exist_ok=True)

    audit_payload: Dict[str, str] = {
        "run_id": run_id,
        "audit_sha256": audit_sha256,
    }

    audit_out.write_text(json.dumps(audit_payload, indent=2), encoding="utf-8")
    print(f"saved {audit_out}")


if __name__ == "__main__":
    main(sys.argv)
