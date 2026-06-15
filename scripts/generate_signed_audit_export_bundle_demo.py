#!/usr/bin/env python3
"""Generate a small signed audit export zip for offline verifier demos (no runtime required)."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "python") not in sys.path:
    sys.path.insert(0, str(ROOT / "python"))

from aigov_py.audit_export_bundle import (  # noqa: E402
    DEFAULT_AUDIT_EXPORT_PATH,
    DEFAULT_MANIFEST_PATH,
    build_manifest_json,
    sha256_content_hex,
    write_bundle_zip,
)
from aigov_py.audit_export_signing import (  # noqa: E402
    SUPPORTED_EXPORT_SCHEMA,
    sign_audit_export_ed25519,
)
from aigov_py.portable_evidence_digest import portable_evidence_digest_v1  # noqa: E402

# Public demo signing key (Ed25519 seed 0x22 repeated). For examples and tests only.
DEMO_SEED = b"\x22" * 32
DEMO_ISSUER_ID = "govai-export-signer"
DEFAULT_RUN_ID = "demo-signed-export"


def demo_trust_json() -> str:
    from nacl.signing import SigningKey

    pk_b64 = base64.b64encode(SigningKey(DEMO_SEED).verify_key.encode()).decode("ascii")
    return json.dumps([{"issuer_id": DEMO_ISSUER_ID, "pubkeys_base64": [pk_b64]}])


def minimal_export(run_id: str) -> dict:
    events = [
        {
            "event_id": f"{run_id}-e1",
            "event_type": "ai_discovery_reported",
            "ts_utc": "2026-01-01T00:00:01Z",
            "actor": "demo",
            "system": "demo",
            "run_id": run_id,
            "payload": {"openai": False, "transformers": False, "model_artifacts": False},
        }
    ]
    events_sha = portable_evidence_digest_v1(run_id, events)
    return {
        "ok": True,
        "schema_version": SUPPORTED_EXPORT_SCHEMA,
        "policy_version": "demo-policy",
        "environment": "dev",
        "run": {"run_id": run_id},
        "evidence_hashes": {
            "bundle_sha256": "a" * 64,
            "events_content_sha256": events_sha,
            "chain_head_record_sha256": "b" * 64,
            "log_chain": [],
        },
        "decision": {"verdict": "BLOCKED", "evaluation_passed": False},
        "evidence_events": events,
        "evidence_requirements": {
            "required_evidence": [],
            "provided_evidence": [],
            "missing_evidence": [],
        },
    }


def build_demo_bundle(run_id: str) -> dict[str, bytes]:
    export = minimal_export(run_id)
    export_path = ROOT / ".tmp-export.json"
    signed_path = ROOT / ".tmp-signed-export.json"
    export_path.write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
    sign_audit_export_ed25519(
        export_path,
        out_path=signed_path,
        issuer_id=DEMO_ISSUER_ID,
        signer="demo-generator",
        private_key_base64=base64.b64encode(DEMO_SEED).decode("ascii"),
        created_at_utc="2026-01-01T00:00:00Z",
    )
    export_bytes = signed_path.read_bytes()
    evidence_bytes = json.dumps({"note": "demo attachment"}, indent=2).encode("utf-8") + b"\n"
    finding_bytes = json.dumps({"finding_id": "finding:demo-none"}, indent=2).encode("utf-8") + b"\n"

    files = [
        {
            "path": DEFAULT_AUDIT_EXPORT_PATH,
            "sha256": sha256_content_hex(export_bytes),
            "required": True,
            "unsigned": False,
        },
        {
            "path": "evidence/discovery.json",
            "sha256": sha256_content_hex(evidence_bytes),
            "required": True,
            "unsigned": False,
        },
        {
            "path": "findings/demo.json",
            "sha256": sha256_content_hex(finding_bytes),
            "required": True,
            "unsigned": False,
        },
    ]
    manifest = {
        "schema_version": "aigov.audit_export_bundle.v1",
        "run_id": run_id,
        "audit_export_path": DEFAULT_AUDIT_EXPORT_PATH,
        "files": files,
        "evidence_refs": [{"ref_id": "evidence:discovery", "path": "evidence/discovery.json"}],
        "finding_refs": [{"finding_id": "finding:demo", "path": "findings/demo.json"}],
        "unsigned_dependencies": [],
    }
    manifest_bytes = build_manifest_json(manifest)
    return {
        DEFAULT_AUDIT_EXPORT_PATH: export_bytes,
        "evidence/discovery.json": evidence_bytes,
        "findings/demo.json": finding_bytes,
        DEFAULT_MANIFEST_PATH: manifest_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "examples/signed-audit-export-bundle/demo.valid.zip",
        help="Output zip path",
    )
    parser.add_argument(
        "--trust-out",
        type=Path,
        default=ROOT / "examples/signed-audit-export-bundle/trust-demo.json",
        help="Write demo trust store JSON (public keys only)",
    )
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID, help="Run id embedded in export")
    args = parser.parse_args()

    entries = build_demo_bundle(str(args.run_id).strip())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_bundle_zip(args.out, entries)
    args.trust_out.parent.mkdir(parents=True, exist_ok=True)
    args.trust_out.write_text(demo_trust_json() + "\n", encoding="utf-8")

    # Cleanup temp files if present
    for name in (".tmp-export.json", ".tmp-signed-export.json"):
        p = ROOT / name
        if p.exists():
            p.unlink()

    print(json.dumps({"ok": True, "bundle": str(args.out), "trust": str(args.trust_out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
