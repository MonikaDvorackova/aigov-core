from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def _read_json(p: Path) -> Dict[str, Any]:
    import json
    return json.loads(_read_text(p))


def _rewrite_header(report_text: str, run_id: str, bundle_sha256: str, policy_version: str) -> str:
    lines = report_text.splitlines()

    # Keep the body intact, only force the 3 header lines.
    # If the file is shorter, pad it.
    while len(lines) < 3:
        lines.append("")

    lines[0] = f"run_id={run_id}"
    lines[1] = f"bundle_sha256={bundle_sha256}"
    lines[2] = f"policy_version={policy_version}"

    # Ensure an empty line after header.
    if len(lines) == 3:
        lines.append("")
    elif lines[3].strip() != "":
        lines.insert(3, "")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        raise SystemExit("Usage: python -m aigov_py.report_fill <run_id>")

    run_id = argv[1].strip()
    if not run_id:
        raise SystemExit("run_id is required")

    root = _repo_root()
    audit_path = root / "docs" / "audit" / f"{run_id}.json"
    report_path = root / "docs" / "reports" / f"{run_id}.md"

    if not audit_path.exists():
        raise FileNotFoundError(f"Missing audit object: {audit_path}")
    if not report_path.exists():
        raise FileNotFoundError(f"Missing report: {report_path}")

    audit = _read_json(audit_path)
    bundle_sha256 = str(audit.get("bundle_sha256") or "").strip()
    policy_version = str(audit.get("policy_version") or "").strip()

    if not bundle_sha256:
        raise ValueError("audit object missing bundle_sha256")
    if not policy_version:
        raise ValueError("audit object missing policy_version")

    report_text = _read_text(report_path)
    updated = _rewrite_header(report_text, run_id, bundle_sha256, policy_version)
    _write_text(report_path, updated)

    print(f"saved {report_path}")


if __name__ == "__main__":
    main(sys.argv)
