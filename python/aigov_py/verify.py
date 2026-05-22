from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests

from aigov_py.fetch_bundle_from_govai import audit_base_url


def repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _audit_request_headers() -> Dict[str, str]:
    """Same defaults as fetch_bundle_from_govai / write_digest_manifest (tenant-scoped routes)."""
    h: Dict[str, str] = {"Accept": "application/json"}
    key = (os.environ.get("GOVAI_API_KEY") or "ci-test-api-key").strip()
    if key:
        h["Authorization"] = f"Bearer {key}"
    proj = (os.environ.get("GOVAI_PROJECT") or "github-actions").strip()
    if proj:
        h["X-GovAI-Project"] = proj
    return h


def verify(run_id: str, *, as_json: bool = False) -> int:
    root = repo_root()
    mode = os.environ.get("AIGOV_MODE", "ci")
    endpoint = audit_base_url()

    audit_path = os.path.join(root, "docs", "audit", f"{run_id}.json")
    evidence_path = os.path.join(root, "docs", "evidence", f"{run_id}.json")
    report_path = os.path.join(root, "docs", "reports", f"{run_id}.md")

    checks: List[Dict[str, Any]] = []
    ok = True

    def human(msg: str) -> None:
        if not as_json:
            print(msg)

    if not as_json:
        print("AIGOV VERIFICATION REPORT")
        print(f"Audit ID: {run_id}")
        print(f"AIGOV_MODE: {mode}")

    audit = load_json(audit_path)
    evidence = load_json(evidence_path)

    # --- AUDIT FILE ---
    if audit is None:
        human("FAIL missing audit file")
        checks.append({"id": "audit_file", "ok": False, "message": "missing audit file"})
        ok = False
    else:
        human("OK   audit file present")
        checks.append({"id": "audit_file", "ok": True, "message": "present"})

    # --- EVIDENCE FILE ---
    if evidence is None:
        human("FAIL missing evidence file")
        checks.append({"id": "evidence_file", "ok": False, "message": "missing evidence file"})
        ok = False
        evidence = {}
    else:
        human("OK   evidence file present")
        checks.append({"id": "evidence_file", "ok": True, "message": "present"})

    # --- GOVERNANCE LOG VERIFICATION ---
    ledger_derived = isinstance(evidence, dict) and bool(evidence.get("log_path"))
    try:
        r = requests.get(
            f"{endpoint}/verify-log",
            headers=_audit_request_headers(),
            timeout=15,
        )
        r.raise_for_status()
        verdict = r.json()
        if verdict.get("ok") is True:
            human("OK   governance hash chain verified")
            checks.append({"id": "governance_chain", "ok": True, "message": "hash chain verified", "detail": verdict})
        else:
            human(f"FAIL governance verify-log returned: {verdict}")
            checks.append({"id": "governance_chain", "ok": False, "message": "verify-log not ok", "detail": verdict})
            ok = False
    except Exception as e:
        if ledger_derived:
            human(f"FAIL could not verify governance log chain: {e}")
            checks.append({"id": "governance_chain", "ok": False, "message": str(e)})
            ok = False
        else:
            human(f"WARN could not verify governance log chain (skipping): {e}")
            checks.append({"id": "governance_chain", "ok": True, "level": "warn", "message": str(e)})

    # --- EVENTS LIST ---
    events = evidence.get("events")
    if not isinstance(events, list) or len(events) == 0:
        human("FAIL evidence.events missing or empty")
        checks.append({"id": "evidence_events", "ok": False, "message": "events missing or empty"})
        ok = False
    else:
        human(f"OK   evidence contains {len(events)} events")
        event_ok = True
        for idx, ev in enumerate(events[:10]):
            if not isinstance(ev, dict):
                human(f"FAIL event {idx} is not an object")
                checks.append({"id": "evidence_events", "ok": False, "message": f"event {idx} is not an object"})
                ok = False
                event_ok = False
                break
            if not isinstance(ev.get("event_id"), str) or not isinstance(ev.get("event_type"), str):
                human(f"FAIL event {idx} missing event_id/event_type")
                checks.append(
                    {"id": "evidence_events", "ok": False, "message": f"event {idx} missing event_id/event_type"}
                )
                ok = False
                event_ok = False
                break
        if event_ok:
            checks.append({"id": "evidence_events", "ok": True, "message": f"{len(events)} events", "count": len(events)})

    # --- POLICY VERSION ---
    policy_version = None
    if isinstance(audit, dict):
        policy_version = audit.get("policy_version")
    if not policy_version and isinstance(evidence, dict):
        policy_version = evidence.get("policy_version")
    if not policy_version:
        human("FAIL missing policy_version (audit or evidence)")
        checks.append({"id": "policy_version", "ok": False, "message": "missing"})
        ok = False
    else:
        human(f"OK   policy_version={policy_version}")
        checks.append({"id": "policy_version", "ok": True, "message": str(policy_version)})

    # --- AUDIT BUNDLE FINGERPRINT ---
    if isinstance(audit, dict):
        bundle_sha = audit.get("bundle_sha256")
        if not isinstance(bundle_sha, str) or not bundle_sha.strip():
            human("FAIL missing audit.bundle_sha256")
            checks.append({"id": "bundle_sha256", "ok": False, "message": "missing"})
            ok = False
        else:
            checks.append({"id": "bundle_sha256", "ok": True, "message": "present"})

    # --- REPORT FILE ---
    if not os.path.exists(report_path):
        human("FAIL missing report")
        checks.append({"id": "report_file", "ok": False, "message": "missing"})
        ok = False
    else:
        human("OK   report file present")
        checks.append({"id": "report_file", "ok": True, "message": "present"})

    verdict = "VALID" if ok else "INVALID"
    if as_json:
        payload = {
            "run_id": run_id,
            "aigov_mode": mode,
            "audit_endpoint": endpoint,
            "verdict": verdict,
            "checks": checks,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if ok:
            print("ARTIFACTS_OK")
        else:
            print("ARTIFACTS_INVALID")

    return 0 if ok else 2


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python -m aigov_py.verify <RUN_ID>")
        return 2

    run_id = argv[1].strip()
    if not run_id:
        print("RUN_ID is empty")
        return 2

    return verify(run_id, as_json=False)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
