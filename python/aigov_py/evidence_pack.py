from __future__ import annotations

import json
import os
import hashlib
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest(entries: List[Tuple[str, Path]]) -> Dict[str, Any]:
    files = []
    for logical_name, p in entries:
        files.append(
            {
                "name": logical_name,
                "path": logical_name,
                "sha256": _sha256_file(p),
                "bytes": p.stat().st_size,
            }
        )
    return {"schema_version": "aigov.pack.manifest.v1", "files": files}


def main() -> None:
    run_id = os.environ.get("RUN_ID", "").strip()
    if not run_id:
        raise SystemExit("RUN_ID is required")

    repo_root = Path(__file__).resolve().parents[2]

    evidence_path = repo_root / "docs" / "evidence" / f"{run_id}.json"
    report_path = repo_root / "docs" / "reports" / f"{run_id}.md"
    audit_path = repo_root / "docs" / "audit" / f"{run_id}.json"

    if not evidence_path.exists():
        raise SystemExit(f"missing evidence bundle: {evidence_path}")
    if not report_path.exists():
        raise SystemExit(f"missing report: {report_path}")
    if not audit_path.exists():
        raise SystemExit(f"missing audit JSON: {audit_path}")

    bundle = _read_json(evidence_path)
    policy_version = str(bundle.get("policy_version", "")).strip() or "unknown"

    out_dir = repo_root / "docs" / "packs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy into pack staging directory with stable names
    bundle_out = out_dir / "bundle.json"
    report_out = out_dir / "report.md"
    audit_out = out_dir / "audit.json"
    policy_out = out_dir / "policy.txt"
    readme_out = out_dir / "README.txt"
    manifest_out = out_dir / "manifest.json"

    bundle_out.write_bytes(evidence_path.read_bytes())
    report_out.write_bytes(report_path.read_bytes())
    audit_out.write_bytes(audit_path.read_bytes())

    _write_text(policy_out, f"policy_version={policy_version}\n")

    _write_text(
        readme_out,
        "\n".join(
            [
                "AIGov evidence pack",
                "",
                f"run_id={run_id}",
                f"policy_version={policy_version}",
                "",
                "Contents",
                "- bundle.json: machine verifiable evidence bundle",
                "- report.md: human readable audit report",
                "- audit.json: machine verifiable combined audit index",
                "- policy.txt: policy snapshot reference",
                "- manifest.json: sha256 for each file in this pack",
                "",
                "Verification",
                "1) Check manifest.json hashes match files",
                "2) Optionally verify audit log chain with the governance server",
                "",
            ]
        ),
    )

    entries: List[Tuple[str, Path]] = [
        ("bundle.json", bundle_out),
        ("report.md", report_out),
        ("audit.json", audit_out),
        ("policy.txt", policy_out),
        ("README.txt", readme_out),
    ]
    manifest = _manifest(entries)
    _write_text(manifest_out, json.dumps(manifest, ensure_ascii=False, indent=2))

    # Now create zip
    zip_path = repo_root / "docs" / "packs" / f"{run_id}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(bundle_out, arcname="bundle.json")
        z.write(report_out, arcname="report.md")
        z.write(audit_out, arcname="audit.json")
        z.write(policy_out, arcname="policy.txt")
        z.write(readme_out, arcname="README.txt")
        z.write(manifest_out, arcname="manifest.json")

    print(f"saved {zip_path}")
    print(f"pack_sha256={_sha256_file(zip_path)}")


if __name__ == "__main__":
    main()
