from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

from govai import (
    GovAIAPIError,
    GovAIClient,
    GovAIHTTPError,
    __version__,
    export_run,
    get_usage,
    get_compliance_summary,
    submit_event,
)

from aigov_py import cli_config
from aigov_py import cli_exit
from aigov_py import evidence_artifact_gate as eag
from aigov_py.client import GovaiClient
from aigov_py.discovery_scan import scan_repo
from aigov_py.discovery_policy_mapping import (
    coerce_discovery_signals,
    discovery_required_evidence_additions,
    triggered_by_discovery,
)
from aigov_py.policy_loader import load_policy_module, policy_identity, required_evidence_from_policy
from aigov_py.audit_export_signing import (
    load_trust_from_env_json,
    sign_audit_export_ed25519,
    verify_signed_audit_export,
)
from aigov_py.policy_bundle_signing import (
    sign_policy_bundle_ed25519,
    verify_policy_bundle_ed25519,
)
from aigov_py.sigstore_verify import SigstoreIdentity, load_bundle_bytes, parse_json_payload, verify_dsse_bundle
from aigov_py import export_bundle as export_bundle_mod
from aigov_py import fetch_bundle_from_govai
from aigov_py.prototype_domain import (
    approved_human_event_id_for_run,
    assessment_id_for_run,
    model_version_id_for_run,
    risk_id_for_run,
)
from aigov_py import report as report_mod
from aigov_py.types import AssessmentCreate, GovaiError
from aigov_py import verify as verify_mod
from aigov_py.demo_golden_path import generate_demo_golden_path
from aigov_py.portable_evidence_digest import portable_evidence_digest_v1

# Thin wrappers — same package


class GovaiArgumentParser(argparse.ArgumentParser):
    """argparse wired to ``EX_USAGE`` (4), keeping policy verdict exits on 2/3 only."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(cli_exit.EX_USAGE, f"{self.prog}: error: {message}\n")


def _system_exit_code(se: SystemExit) -> int:
    c = se.code
    if c is None:
        return cli_exit.EX_OK
    if isinstance(c, int):
        if c == 2:
            return cli_exit.EX_USAGE
        return c
    return cli_exit.EX_USAGE


def _config_path_from_args(ns: argparse.Namespace) -> Path | None:
    raw = getattr(ns, "config", None)
    if isinstance(raw, Path):
        return raw.expanduser().resolve()
    return None


def _audit_url(ns: argparse.Namespace) -> str:
    flag = getattr(ns, "audit_base_url", None)
    if flag:
        return str(flag).rstrip("/")
    return cli_config.resolve_audit_base_url(
        flag=None,
        config_path=_config_path_from_args(ns),
    ).rstrip("/")


def _api_key(ns: argparse.Namespace) -> str | None:
    return cli_config.resolve_api_key(
        flag=getattr(ns, "api_key", None) or None,
        config_path=_config_path_from_args(ns),
    )


def _is_localhost_url(url: str) -> bool:
    try:
        u = urlparse(str(url or ""))
    except Exception:
        return False
    host = (u.hostname or "").strip().lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def _resolve_project(ns: argparse.Namespace) -> str | None:
    flag = (getattr(ns, "project", None) or "").strip()
    if flag:
        return flag
    env = (os.environ.get("GOVAI_PROJECT") or os.environ.get("X_GOVAI_PROJECT") or "").strip()
    return env if env else None


def _resolve_run_id(ns: argparse.Namespace) -> str | None:
    rid = (getattr(ns, "run_id", None) or "").strip()
    if rid:
        return rid
    env = (os.environ.get("GOVAI_RUN_ID") or os.environ.get("RUN_ID") or "").strip()
    if env:
        return env
    return None


def _default_run_id_for_evidence_pack_init() -> str:
    """
    Evidence-pack init run_id rules:
    - explicit --run-id wins
    - in CI (GitHub Actions): deterministic `ci-<GITHUB_RUN_ID>-<GITHUB_RUN_ATTEMPT or 1>`
    - otherwise: uuid4 (unique)
    """
    gh_run_id = (os.environ.get("GITHUB_RUN_ID") or "").strip()
    if gh_run_id:
        gh_attempt = (os.environ.get("GITHUB_RUN_ATTEMPT") or "").strip() or "1"
        return f"ci-{gh_run_id}-{gh_attempt}"
    return str(uuid.uuid4())


def _print_json(data: Any, *, compact: bool) -> None:
    if compact:
        print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def _utc_now_z() -> str:
    return "1970-01-01T00:00:00Z"


def _load_payload_one_of(*, payload_file: str | None, payload_json: str | None) -> dict[str, Any]:
    pf = (payload_file or "").strip() or None
    pj = (payload_json or "").strip() or None
    if (pf is None and pj is None) or (pf is not None and pj is not None):
        raise ValueError("exactly one payload source required: --payload-file OR --payload-json")
    if pf is not None:
        raw = Path(pf).expanduser().read_text(encoding="utf-8")
    else:
        raw = pj or ""

    stripped = raw.strip()
    if not stripped:
        raise ValueError("payload must be a JSON object")
    if not (stripped.startswith("{") and stripped.endswith("}")):
        raise ValueError("payload must be a JSON object")

    obj = json.loads(stripped)
    if not isinstance(obj, dict):
        raise TypeError("payload must be a JSON object")
    return obj


def _parse_bool_override(raw: str | None, *, name: str) -> bool | None:
    if raw is None:
        return None
    value = str(raw).strip().lower()
    if value in {"true", "1", "yes", "y", "on"}:
        return True
    if value in {"false", "0", "no", "n", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _coerce_findings(scan_result: Any) -> list[dict[str, Any]]:
    findings = getattr(scan_result, "findings", None)
    if findings is None and isinstance(scan_result, dict):
        findings = scan_result.get("findings")
    if not isinstance(findings, list):
        return []

    out: list[dict[str, Any]] = []
    for item in findings:
        if isinstance(item, dict):
            out.append(item)
        else:
            out.append(
                {
                    "type": getattr(item, "type", None),
                    "file": getattr(item, "file", None),
                    "reason": getattr(item, "reason", None),
                }
            )
    return out


def _signal_from_scan(scan_result: Any, key: str) -> bool:
    if isinstance(scan_result, dict):
        return bool(scan_result.get(key, False))
    return bool(getattr(scan_result, key, False))


def _demo_event_id(kind: str, run_id: str) -> str:
    return f"demo_{kind}_{run_id}"


def _require_env_nonempty(name: str) -> str | None:
    raw = (os.environ.get(name) or "").strip()
    return raw if raw else None


def _missing_evidence_from_summary(summary: Any) -> list[str]:
    """Gap codes from `/compliance-summary` requirements: `missing` (current API) union `missing_evidence` (legacy)."""
    if not isinstance(summary, dict):
        return []
    requirements = summary.get("requirements")
    if not isinstance(requirements, dict):
        current_state = summary.get("current_state")
        if isinstance(current_state, dict):
            requirements = current_state.get("requirements")
    if not isinstance(requirements, dict):
        return []

    out: list[str] = []
    seen: set[str] = set()

    def add_code(code: str) -> None:
        c = code.strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)

    for key in ("missing_evidence", "missing"):
        items = requirements.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                code = item.get("code")
                if isinstance(code, str):
                    add_code(code)
            elif isinstance(item, str) and item.strip():
                add_code(item)

    return out


def _requirements_dict_from_summary(summary: dict[str, Any]) -> dict[str, Any] | None:
    requirements = summary.get("requirements")
    if not isinstance(requirements, dict):
        current_state = summary.get("current_state")
        if isinstance(current_state, dict):
            requirements = current_state.get("requirements")
    return requirements if isinstance(requirements, dict) else None


def _print_check_failure_details(summary: dict[str, Any], verdict: str) -> None:
    """After the verdict line, print requirement gaps (API `missing` / legacy `missing_evidence`) and blocked_reasons."""
    if verdict not in ("BLOCKED", "INVALID"):
        return
    req = _requirements_dict_from_summary(summary)
    if isinstance(req, dict):
        missing_evidence = req.get("missing_evidence") or []
        if isinstance(missing_evidence, list) and missing_evidence:
            print("missing_evidence:")
            for item in missing_evidence:
                if isinstance(item, dict):
                    code = item.get("code")
                    src = item.get("source")
                    if isinstance(code, str) and code.strip():
                        extra = f" ({src})" if src else ""
                        print(f"  - {code.strip()}{extra}")
                    else:
                        print(f"  - {item}")
                elif isinstance(item, str) and item.strip():
                    print(f"  - {item.strip()}")
        missing_only = req.get("missing") or []
        if isinstance(missing_only, list) and missing_only:
            print("missing (requirement ids):")
            for item in missing_only:
                if isinstance(item, dict):
                    code = item.get("code")
                    src = item.get("source")
                    if isinstance(code, str) and code.strip():
                        extra = f" ({src})" if src else ""
                        print(f"  - {code.strip()}{extra}")
                    else:
                        print(f"  - {item}")
                elif isinstance(item, str) and item.strip():
                    print(f"  - {item.strip()}")
    blocked_reasons = summary.get("blocked_reasons") or []
    if isinstance(blocked_reasons, list) and blocked_reasons:
        print("blocked_reasons:")
        for reason in blocked_reasons:
            if isinstance(reason, dict):
                code = reason.get("code")
                message = reason.get("message")
                print(f"  - {code}: {message}")
            else:
                print(f"  - {reason}")


def _print_doctor_block(title: str) -> None:
    print("")
    print(f"== {title} ==")


def _stable_reason_codes(codes: Sequence[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for c in (codes or []):
        s = str(c or "").strip()
        if not s:
            continue
        if s not in seen:
            seen.add(s)
            out.append(s)
    out.sort()
    return out


def _category_for_verdict(verdict: str) -> str:
    v = (verdict or "").strip().upper()
    if v == "ERROR":
        return "integration"
    if v == "BLOCKED":
        return "evidence"
    if v == "INVALID":
        return "policy"
    return "policy" if v == "VALID" else "integration"


def _shell_argv_join(argv: Sequence[str]) -> str:
    """Join argv for copy/paste into bash; preserve ``$GOVAI_API_KEY`` without quoting so it expands."""
    parts: list[str] = []
    for a in argv:
        s = str(a)
        if s == "$GOVAI_API_KEY":
            parts.append(s)
        else:
            parts.append(shlex.quote(s))
    return " ".join(parts)


def _format_repro_command(args_list: Sequence[str]) -> str:
    # Exact CLI reproduction command, with stable shell quoting.
    return _shell_argv_join(["govai", *[str(a) for a in args_list]])


def _print_final_summary(
    *,
    verdict: str,
    reason_codes: Sequence[str] | None,
    next_action: str,
    repro: str,
    triggered_by: Sequence[str] | None = None,
) -> None:
    # Preserve "verdict-first" stdout contract even when CI merges stdout+stderr.
    # If stdout is buffered and stderr is unbuffered, stderr can appear first unless we flush.
    try:
        sys.stdout.flush()
    except Exception:
        pass
    v = (verdict or "").strip().upper() or "ERROR"
    if v not in {"VALID", "INVALID", "BLOCKED", "ERROR"}:
        v = "ERROR"
    cat = _category_for_verdict(v)
    rc = _stable_reason_codes(reason_codes)

    # Printed to stderr so existing stdout remains machine-friendly (verdict-only / JSON-only).
    print("--------------------------------", file=sys.stderr, flush=True)
    print("GovAI summary", file=sys.stderr, flush=True)
    print(f"verdict: {v}", file=sys.stderr, flush=True)
    print(f"category: {cat}", file=sys.stderr, flush=True)
    print(f"reason_codes: {rc}", file=sys.stderr, flush=True)
    if triggered_by:
        tb = [str(x).strip() for x in triggered_by if str(x or "").strip()]
        # Stable ordering
        seen: set[str] = set()
        stable: list[str] = []
        for x in tb:
            if x not in seen:
                seen.add(x)
                stable.append(x)
        stable.sort()
        print(f"triggered_by: {stable}", file=sys.stderr, flush=True)
    print(f"next_action: {next_action}", file=sys.stderr, flush=True)
    print(f"repro: {repro}", file=sys.stderr, flush=True)
    print("--------------------------------", file=sys.stderr, flush=True)


def _summary_for_compliance(
    *,
    verdict: str,
    summary: dict[str, Any] | None,
    repro: str,
) -> tuple[str, list[str], str, str]:
    v = (verdict or "").strip().upper() or "ERROR"
    codes: list[str] = []

    if v == "VALID":
        next_action = "Proceed with deployment."
    elif v == "BLOCKED":
        missing = _missing_evidence_from_summary(summary or {})
        blocked_reasons = (summary or {}).get("blocked_reasons")
        if missing or (isinstance(blocked_reasons, list) and blocked_reasons):
            codes.append("EVIDENCE_MISSING")
        next_action = _next_action_for_missing_evidence(missing) or (
            "Submit the missing evidence for this run_id, then rerun the same command."
        )
    elif v == "INVALID":
        codes.append("EVALUATION_FAILED")
        next_action = "Fix the failed evaluation evidence and rerun the same command."
    else:
        codes.append("INTEGRATION_ERROR")
        next_action = "Check GOVAI_AUDIT_BASE_URL and GOVAI_API_KEY (and network), then rerun the same command."

    return v if v in {"VALID", "INVALID", "BLOCKED"} else "ERROR", _stable_reason_codes(codes), next_action, repro


_MISSING_EVIDENCE_HINTS: dict[str, str] = {
    "evaluation_reported": "Run your evaluation pipeline and submit evidence.",
    "human_approved": "Record human approval event.",
    "usage_policy_defined": "Define and submit usage policy.",
    "privacy_review_completed": "Complete privacy review and submit evidence.",
    "model_registered": "Register the model version and submit evidence.",
    "risk_recorded": "Record risk assessment evidence for this run.",
    "risk_reviewed": "Complete risk review and submit evidence.",
    "risk_mitigated": "Record mitigation evidence and submit it for this run.",
}


def _next_action_for_missing_evidence(missing: Sequence[str] | None) -> str | None:
    """
    Deterministic mapping: missing evidence → actionable hint.
    Picks the first hint by stable (sorted) missing code order.
    """
    codes = sorted({str(x).strip() for x in (missing or []) if str(x or "").strip()})
    for c in codes:
        hint = _MISSING_EVIDENCE_HINTS.get(c)
        if hint:
            return hint
    return None


def _triggered_by_from_repo_scan(path: Path) -> list[str]:
    """
    Best-effort local enhancement for summary output:
    - deterministic scan_repo()
    - deterministic mapping to discovery-required evidence
    - returns *signal labels* (not evidence codes)

    This does not change Rust semantics and is not submitted to the backend.
    """
    scan = scan_repo(path, include_history=False)
    signals = coerce_discovery_signals(scan)
    # Ensure we only claim triggers that correspond to a rule we enforce in mapping.
    _ = discovery_required_evidence_additions(signals)
    return triggered_by_discovery(signals)


def doctor(audit_url: str, api_key: str | None, *, timeout_sec: float) -> int:
    """
    ``govai doctor``: read-only preflight checks for first-time success.

    This does not change compliance semantics; it probes `/status` and `/ready` for operator clarity.
    """
    client = GovAIClient(audit_url.rstrip("/"), api_key=api_key, default_project=os.environ.get("GOVAI_PROJECT"))

    _print_doctor_block("GovAI doctor")
    print(f"govai_cli_version: {__version__}")
    print(f"audit_base_url: {audit_url}")
    print(f"api_key_configured: {bool(api_key)}")

    _print_doctor_block("HTTP checks")
    ok_status = False
    ok_ready = False

    try:
        status = client.request_json("GET", "/status", timeout=timeout_sec, raise_on_body_ok_false=False)
        if isinstance(status, dict) and status.get("ok") is not False:
            ok_status = True
            pv = status.get("policy_version")
            env = status.get("environment")
            print(f"PASS /status (policy_version={pv} environment={env})")
        else:
            msg = status.get("message") if isinstance(status, dict) else None
            print(f"FAIL /status ({msg or 'unexpected response'})")
    except GovAIHTTPError as e:
        hint = ""
        if e.status_code == 404:
            hint = " hint: base_url must point to audit service origin (no /api or /v1 prefix)."
        print(f"FAIL /status ({e}).{hint}")
    except Exception as e:
        print(f"FAIL /status ({e})")

    try:
        ready = client.request_json("GET", "/ready", timeout=timeout_sec, raise_on_body_ok_false=False)
        if isinstance(ready, dict) and ready.get("ok") is not False:
            ok_ready = True
            print("PASS /ready (operational readiness: DB + migrations + ledger)")
        else:
            msg = ready.get("message") if isinstance(ready, dict) else None
            print(f"FAIL /ready ({msg or 'not ready'})")
    except GovAIHTTPError as e:
        if e.status_code in (401, 403):
            print(
                "FAIL /ready (auth rejected). hint: verify GOVAI_API_KEY and server GOVAI_API_KEYS_JSON / GOVAI_API_KEYS configuration."
            )
        else:
            print(f"FAIL /ready ({e})")
    except Exception as e:
        print(f"FAIL /ready ({e})")

    if ok_status and ok_ready:
        return cli_exit.EX_OK
    return cli_exit.EX_ERR


def _preflight_print_section(title: str) -> None:
    print(title)


def _preflight_print_fail(reason: str) -> None:
    msg = (reason or "").strip() or "preflight failed"
    print(msg)
    print("FAIL")


def _preflight_print_pass() -> None:
    print("PASS")


def _preflight_local_evidence_pack_check(*, timeout_sec: float) -> tuple[bool, str | None]:
    _ = timeout_sec  # reserved for future local timeouts
    run_id = str(uuid.uuid4())
    try:
        with tempfile.TemporaryDirectory(prefix="govai_preflight_") as td:
            out_dir = Path(td)
            generate_demo_golden_path(run_id=run_id, output_dir=out_dir)

            files = sorted(p.name for p in out_dir.iterdir() if p.is_file())
            expected = sorted([f"{run_id}.json", "evidence_digest_manifest.json"])
            if files != expected:
                return (
                    False,
                    f"unexpected evidence pack files (expected {expected}, got {files})",
                )

            bundle, _bundle_path = eag.load_bundle(run_id, out_dir)
            manifest = eag.load_manifest(out_dir)

            if str(bundle.get("run_id") or "") != str(manifest.get("run_id") or ""):
                return False, "bundle/manifest run_id mismatch"

            events = bundle.get("events")
            if not isinstance(events, list):
                return False, "bundle.events must be a list"

            required_types = {
                "data_registered",
                "model_trained",
                "evaluation_reported",
                "human_approved",
                "model_promoted",
            }
            present_types: set[str] = set()
            for e in events:
                if isinstance(e, dict):
                    et = e.get("event_type")
                    if isinstance(et, str) and et.strip():
                        present_types.add(et.strip())
            missing = sorted(required_types.difference(present_types))
            if missing:
                return False, f"missing required event_type(s): {', '.join(missing)}"

            expected_digest = str(manifest.get("events_content_sha256") or "").strip().lower()
            if len(expected_digest) != 64:
                return False, "manifest events_content_sha256 missing or invalid"

            got_digest = portable_evidence_digest_v1(run_id, events).lower()
            if got_digest != expected_digest:
                return False, "evidence digest mismatch (recompute != manifest)"
    except Exception:
        # Keep production gate output actionable and minimal (no stack traces).
        return False, "failed to generate/validate evidence pack"

    return True, None


def _preflight_audit_ready_check(*, audit_url: str, api_key: str | None, timeout_sec: float) -> tuple[bool, str | None]:
    try:
        client = GovAIClient(audit_url.rstrip("/"), api_key=api_key, default_project=os.environ.get("GOVAI_PROJECT"))
        _ = client.request_json("GET", "/ready", timeout=timeout_sec, raise_on_body_ok_false=False)
    except Exception:
        return False, "audit service not ready (/ready != 200)"
    return True, None


def _preflight_submit_capability_check(
    *,
    audit_url: str,
    api_key: str | None,
    timeout_sec: float,
) -> tuple[bool, str | None]:
    run_id = str(uuid.uuid4())
    try:
        with tempfile.TemporaryDirectory(prefix="govai_preflight_submit_") as td:
            out_dir = Path(td)
            generate_demo_golden_path(run_id=run_id, output_dir=out_dir)
            bundle, _bundle_path = eag.load_bundle(run_id, out_dir)
            manifest = eag.load_manifest(out_dir)

            client = GovAIClient(audit_url.rstrip("/"), api_key=api_key, default_project=os.environ.get("GOVAI_PROJECT"))
            # Submit all evidence for this new run_id.
            eag.submit_evidence_bundle_events(client, bundle=bundle, progress=None)

            expected = str(manifest.get("events_content_sha256") or "").strip().lower()
            got_body = eag.bundle_hash_digest(client, run_id)
            got = str(got_body.get("events_content_sha256") or "").strip().lower()
            if expected and got and expected != got:
                return False, "submitted evidence digest mismatch (/bundle-hash != manifest)"
    except GovAIHTTPError as exc:
        payload = getattr(exc, "payload", None)
        code: str | None = None
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict) and isinstance(err.get("code"), str):
                code = (err.get("code") or "").strip().upper() or None
            if code is None and isinstance(payload.get("code"), str):
                code = (payload.get("code") or "").strip().upper() or None
        if code:
            return False, f"submit capability check failed ({code})"
        return False, "submit capability check failed (HTTP error)"
    except GovAIAPIError as exc:
        payload = getattr(exc, "payload", None)
        code: str | None = None
        if isinstance(payload, dict) and isinstance(payload.get("code"), str):
            code = (payload.get("code") or "").strip().upper() or None
        if code:
            return False, f"submit capability check failed ({code})"
        return False, "submit capability check failed (API error)"
    except Exception:
        return False, "submit capability check failed (cannot submit evidence or verify digest)"

    return True, None


def preflight(
    *,
    local_only: bool,
    submit: bool,
    timeout_sec: float,
    audit_url: str,
    api_key: str | None,
) -> int:
    ok_all = True

    _preflight_print_section("Preflight: local evidence pack")
    ok_local, reason_local = _preflight_local_evidence_pack_check(timeout_sec=timeout_sec)
    if ok_local:
        _preflight_print_pass()
    else:
        ok_all = False
        _preflight_print_fail(reason_local or "local evidence pack check failed")

    if local_only:
        return cli_exit.EX_OK if ok_all else cli_exit.EX_ERR

    _preflight_print_section("Preflight: audit service")
    ok_audit, reason_audit = _preflight_audit_ready_check(
        audit_url=audit_url,
        api_key=api_key,
        timeout_sec=timeout_sec,
    )
    if ok_audit:
        _preflight_print_pass()
    else:
        ok_all = False
        _preflight_print_fail(reason_audit or "audit service check failed")

    if submit:
        _preflight_print_section("Preflight: submit capability")
        ok_submit, reason_submit = _preflight_submit_capability_check(
            audit_url=audit_url,
            api_key=api_key,
            timeout_sec=timeout_sec,
        )
        if ok_submit:
            _preflight_print_pass()
        else:
            ok_all = False
            _preflight_print_fail(reason_submit or "submit capability check failed")

    return cli_exit.EX_OK if ok_all else cli_exit.EX_ERR


def _exit_for_compliance_verdict(verdict: str) -> int:
    if verdict == "VALID":
        return cli_exit.EX_OK
    if verdict == "BLOCKED":
        return cli_exit.EX_BLOCKED
    return cli_exit.EX_INVALID


def _verify_artifact_digest_continuity(
    client: GovAIClient,
    *,
    artifact_dir: Path,
    run_id: str,
    require_export: bool = False,
    artifact_file: Path | None = None,
    portable_only: bool = False,
) -> tuple[int, str]:
    reason_code = "DIGEST_MISMATCH"
    try:
        bundle, _bundle_path = eag.load_bundle(run_id, artifact_dir)
        man = eag.load_manifest(artifact_dir)
    except (OSError, json.JSONDecodeError, TypeError, FileNotFoundError) as exc:
        print(f"ERROR: cannot read evidence pack: {exc}", file=sys.stderr)
        return cli_exit.EX_ERR, reason_code

    # Phase 1 prerequisite: local bundle must match CI digest manifest (fail-closed).
    br = str(bundle.get("run_id") or "").strip()
    if br != run_id.strip():
        print(
            f"ERROR: bundle run_id mismatch (bundle={br!r} expected={run_id!r})",
            file=sys.stderr,
        )
        return cli_exit.EX_ERR, reason_code

    events = bundle.get("events")
    if not isinstance(events, list):
        print("ERROR: bundle.events must be a list", file=sys.stderr)
        return cli_exit.EX_ERR, reason_code
    mr = str(man.get("run_id") or "").strip()
    if mr != run_id.strip():
        print(
            f"ERROR: manifest run_id mismatch (manifest={mr!r} expected={run_id!r})",
            file=sys.stderr,
        )
        return cli_exit.EX_ERR, reason_code
    expected = str(man.get("events_content_sha256") or "").strip().lower()
    if len(expected) != 64:
        print("ERROR: manifest events_content_sha256 missing or not a 64-char hex digest", file=sys.stderr)
        return cli_exit.EX_ERR, reason_code

    recomputed = portable_evidence_digest_v1(run_id, [dict(e) for e in events if isinstance(e, dict)]).lower()
    if recomputed != expected:
        print(
            "ERROR: evidence bundle digest mismatch (recompute from <run_id>.json != evidence_digest_manifest.json "
            f"events_content_sha256; expected={expected} actual={recomputed})",
            file=sys.stderr,
        )
        return cli_exit.EX_ERR, reason_code

    # Phase 1 prerequisite: promoted artifact must carry a stable digest in evidence (source-of-truth),
    # even when the artifact file isn't available at gate time.
    promoted_digest: str | None = None
    for e in reversed([ev for ev in events if isinstance(ev, dict)]):
        if str(e.get("event_type") or "").strip() != "model_promoted":
            continue
        payload = e.get("payload")
        if isinstance(payload, dict):
            raw = payload.get("artifact_sha256") or payload.get("artifact_digest_sha256")
            if isinstance(raw, str) and raw.strip():
                promoted_digest = raw.strip().lower()
        break
    if not promoted_digest or len(promoted_digest) != 64:
        print(
            "ERROR: model_promoted missing required artifact digest (expected payload.artifact_sha256 "
            "or payload.artifact_digest_sha256 as a 64-char hex string).",
            file=sys.stderr,
        )
        return cli_exit.EX_ERR, "MISSING_ARTIFACT_DIGEST"

    if artifact_file is not None:
        try:
            import hashlib

            h = hashlib.sha256()
            with artifact_file.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            actual = h.hexdigest().lower()
        except Exception as exc:
            print(f"ERROR: cannot compute SHA256 for --artifact-file {artifact_file}: {exc}", file=sys.stderr)
            return cli_exit.EX_ERR, reason_code
        if actual != promoted_digest:
            print(
                "ERROR: promoted artifact digest mismatch (--artifact-file sha256 != model_promoted payload digest; "
                f"expected={promoted_digest} actual={actual})",
                file=sys.stderr,
            )
            return cli_exit.EX_ERR, reason_code
    if portable_only:
        return cli_exit.EX_OK, "OK"

    try:
        got_body = eag.bundle_hash_digest(client, run_id)
    except Exception as exc:
        print(f"ERROR: /bundle-hash failed: {exc}", file=sys.stderr)
        msg = str(exc).lower()
        if "connection refused" in msg or "failed to establish a new connection" in msg:
            print(
                "hint: Configure GOVAI_AUDIT_BASE_URL to your operator runtime (GovAI Platform or self-host), "
                "or use verify-evidence-pack --portable-only for offline CI.",
                file=sys.stderr,
            )
        return cli_exit.EX_ERR, reason_code
    got = str(got_body.get("events_content_sha256") or "").strip().lower()
    if got != expected:
        print(
            "ERROR: hosted events_content_sha256 does not match CI evidence_digest_manifest.json "
            f"(expected={expected} actual={got})",
            file=sys.stderr,
        )
        return cli_exit.EX_ERR, reason_code

    export_hashes, export_skip = eag.fetch_export_evidence_hashes(client, run_id)
    if export_hashes is None:
        note = export_skip or "export not available"
        print(
            f"NOTE: /api/export cross-check skipped ({note}).",
            file=sys.stderr,
        )
        if require_export:
            print(
                "ERROR: --require-export requires a successful /api/export cross-check.",
                file=sys.stderr,
            )
            return cli_exit.EX_ERR, reason_code
    else:
        ex = str(export_hashes.get("events_content_sha256") or "").strip().lower()
        if ex and ex != got:
            print(
                "ERROR: /api/export evidence_hashes.events_content_sha256 disagrees with /bundle-hash "
                f"(export={ex} bundle_hash={got})",
                file=sys.stderr,
            )
            return cli_exit.EX_ERR, reason_code
    return cli_exit.EX_OK, "OK"


def _compliance_verdict_or_err(client: GovAIClient, run_id: str, *, timeout: float) -> tuple[int, dict[str, Any] | None]:
    try:
        summary = get_compliance_summary(client, run_id, timeout=timeout)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return cli_exit.EX_ERR, None
    if not isinstance(summary, dict):
        print("error: expected object from /compliance-summary", file=sys.stderr)
        return cli_exit.EX_ERR, None
    if summary.get("ok") is False:
        print(
            summary.get("message") or summary.get("error") or "error: /compliance-summary failed",
            file=sys.stderr,
        )
        return cli_exit.EX_ERR, None
    verdict = summary.get("verdict")
    if not isinstance(verdict, str) or not verdict.strip():
        print("error: /compliance-summary missing verdict", file=sys.stderr)
        return cli_exit.EX_ERR, None
    return cli_exit.EX_OK, summary


def run_demo_deterministic(*, timeout_sec: float) -> int:
    """
    ``govai run demo-deterministic``: deterministic, hosted-friendly demo flow.

    Required flow:
    1) create a run id
    2) submit incomplete evidence
    3) check decision and print BLOCKED
    4) print missing evidence
    5) submit required evidence
    6) check decision and print VALID
    7) export audit JSON

    Requirements:
    - Must not require local Postgres when hosted env vars are provided.
    - Requires GOVAI_AUDIT_BASE_URL and GOVAI_API_KEY; if missing, exit 4 with clear instructions.
    """
    base_url = _require_env_nonempty("GOVAI_AUDIT_BASE_URL")
    api_key = _require_env_nonempty("GOVAI_API_KEY")
    if not base_url or not api_key:
        print("error: deterministic demo requires hosted env vars", file=sys.stderr)
        if not base_url:
            print("", file=sys.stderr)
            print("Missing GOVAI_AUDIT_BASE_URL.", file=sys.stderr)
            print('Set it, e.g. export GOVAI_AUDIT_BASE_URL="https://YOUR_GOVAI_AUDIT_SERVICE"', file=sys.stderr)
        if not api_key:
            print("", file=sys.stderr)
            print("Missing GOVAI_API_KEY.", file=sys.stderr)
            print('Set it, e.g. export GOVAI_API_KEY="YOUR_API_KEY"', file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "This demo does not need local Postgres when GOVAI_AUDIT_BASE_URL points to a hosted GovAI audit service.",
            file=sys.stderr,
        )
        return cli_exit.EX_USAGE

    actor = (os.environ.get("AIGOV_ACTOR") or "govai_demo").strip() or "govai_demo"
    system = (os.environ.get("AIGOV_SYSTEM") or "govai_demo_cli").strip() or "govai_demo_cli"

    # Prefer uuid4; allow override for deterministic tests.
    run_id = (os.environ.get("GOVAI_DEMO_RUN_ID") or "").strip() or str(uuid.uuid4())
    print(f"run_id: {run_id}")

    ai_system_id = "demo-ai-system"
    dataset_id = "demo-dataset-v1"
    dataset_commitment = "basic_compliance"
    model_version_id = model_version_id_for_run(run_id)
    assessment_id = assessment_id_for_run(run_id)
    risk_id = risk_id_for_run(run_id)
    human_event_id = approved_human_event_id_for_run(run_id)

    client = GovAIClient(base_url.rstrip("/"), api_key=api_key, default_project=os.environ.get("GOVAI_PROJECT"))

    # (2) Submit incomplete evidence.
    incomplete_seq: list[dict[str, Any]] = [
        {
            "event_id": _demo_event_id("data_registered", run_id),
            "event_type": "data_registered",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "dataset": "demo_dataset",
                "dataset_version": "v1",
                "dataset_fingerprint": "sha256:demo",
                "dataset_governance_id": "gov_demo_v1",
                "dataset_governance_commitment": dataset_commitment,
                "source": "internal",
                "intended_use": "deterministic onboarding demo",
                "limitations": "demo only",
                "quality_summary": "demo only",
                "governance_status": "registered",
            },
        },
        {
            "event_id": _demo_event_id("model_trained", run_id),
            "event_type": "model_trained",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "model_version_id": model_version_id,
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_type": "LogisticRegression",
                "artifact_path": f"registry://demo/model/{model_version_id}",
                "artifact_sha256": "govai_demo_placeholder",
            },
        },
    ]

    try:
        print("(2/7) submit incomplete evidence")
        for ev in incomplete_seq:
            submit_event(client, ev)

        print("(3/7) check decision (expect BLOCKED)")
        summary1 = get_compliance_summary(client, run_id, timeout=timeout_sec)
    except Exception as e:
        print(f"error: demo failed during incomplete phase: {e}", file=sys.stderr)
        return cli_exit.EX_ERR

    verdict1 = summary1.get("verdict") if isinstance(summary1, dict) else None
    verdict1_str = verdict1.strip() if isinstance(verdict1, str) and verdict1.strip() else "BLOCKED"
    print(f"verdict: {verdict1_str}")

    print("(4/7) missing evidence:")
    missing = _missing_evidence_from_summary(summary1)
    if missing:
        for code in missing:
            print(f"- {code}")
    else:
        print("- (none reported by server)")

    # (5) Submit required evidence.
    risk_class = (os.environ.get("AIGOV_RISK_CLASS") or "high").strip() or "high"
    severity = float(os.environ.get("AIGOV_RISK_SEVERITY", "4"))
    likelihood = float(os.environ.get("AIGOV_RISK_LIKELIHOOD", "0.3"))
    owner = (os.environ.get("AIGOV_RISK_OWNER") or "risk_owner").strip() or "risk_owner"
    reviewer = (os.environ.get("AIGOV_RISK_REVIEWER") or "risk_officer").strip() or "risk_officer"

    complete_seq: list[dict[str, Any]] = [
        {
            "event_id": _demo_event_id("evaluation_reported", run_id),
            "event_type": "evaluation_reported",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "metric": "accuracy",
                "value": 0.95,
                "threshold": 0.8,
                "passed": True,
            },
        },
        {
            "event_id": _demo_event_id("risk_recorded", run_id),
            "event_type": "risk_recorded",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "assessment_id": assessment_id,
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "risk_id": risk_id,
                "risk_class": risk_class,
                "severity": severity,
                "likelihood": likelihood,
                "status": "submitted",
                "mitigation": "Demo mitigation: enforce evaluation gate + require human approval before promotion.",
                "owner": owner,
                "dataset_governance_commitment": dataset_commitment,
            },
        },
        {
            "event_id": _demo_event_id("risk_mitigated", run_id),
            "event_type": "risk_mitigated",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "assessment_id": assessment_id,
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "risk_id": risk_id,
                "status": "mitigated",
                "mitigation": "Demo mitigation applied.",
                "dataset_governance_commitment": dataset_commitment,
            },
        },
        {
            "event_id": _demo_event_id("risk_reviewed", run_id),
            "event_type": "risk_reviewed",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "assessment_id": assessment_id,
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "risk_id": risk_id,
                "decision": "approve",
                "reviewer": reviewer,
                "justification": "Demo review: acceptable residual risk within governed demo scope.",
                "dataset_governance_commitment": dataset_commitment,
            },
        },
        {
            "event_id": human_event_id,
            "event_type": "human_approved",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "scope": "model_promoted",
                "decision": "approve",
                "approved": True,
                "approver": "compliance_officer",
                "justification": "Demo: approve promotion after evaluation + risk review.",
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": dataset_commitment,
            },
        },
        {
            "event_id": _demo_event_id("model_promoted", run_id),
            "event_type": "model_promoted",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "artifact_path": f"registry://demo/artifacts/model/{model_version_id}",
                "promotion_reason": "approved_by_human",
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": dataset_commitment,
                "approved_human_event_id": human_event_id,
            },
        },
    ]

    try:
        print("(5/7) submit required evidence")
        for ev in complete_seq:
            submit_event(client, ev)

        print("(6/7) check decision (expect VALID)")
        summary2 = get_compliance_summary(client, run_id, timeout=timeout_sec)
    except Exception as e:
        print(f"error: demo failed during completion phase: {e}", file=sys.stderr)
        return cli_exit.EX_ERR

    verdict2 = summary2.get("verdict") if isinstance(summary2, dict) else None
    verdict2_str = verdict2.strip() if isinstance(verdict2, str) and verdict2.strip() else "UNKNOWN"
    print(f"verdict: {verdict2_str}")
    if verdict2_str != "VALID":
        return cli_exit.EX_ERR

    try:
        print("(7/7) export audit JSON")
        exported = export_run(client, run_id, project=os.environ.get("GOVAI_PROJECT"))
    except Exception as e:
        print(f"error: export failed: {e}", file=sys.stderr)
        return cli_exit.EX_ERR

    out_dir = Path("docs") / "demo"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"audit_export_{run_id}.json"
    out_path.write_text(json.dumps(exported, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"exported: {out_path}")

    return cli_exit.EX_OK


def run_demo(audit_url: str, api_key: str | None) -> int:
    """``govai run demo``: submit a full compliance sequence; print server verdict."""
    actor = (os.environ.get("AIGOV_ACTOR") or "govai_demo").strip() or "govai_demo"
    system = (os.environ.get("AIGOV_SYSTEM") or "govai_demo_cli").strip() or "govai_demo_cli"

    run_id = str(uuid.uuid4())
    dataset_gov: dict[str, Any] = {
        "ai_system_id": "expense-ai",
        "dataset_id": "expense_dataset_v1",
        "dataset": "customer_expense_records",
        "dataset_version": "v1",
        "dataset_fingerprint": "sha256:demo",
        "dataset_governance_id": "gov_expense_v1",
        "dataset_governance_commitment": "basic_compliance",
        "source": "internal",
        "intended_use": "expense classification",
        "limitations": "demo dataset",
        "quality_summary": "validated sample",
        "governance_status": "registered",
    }
    ai_system_id = dataset_gov["ai_system_id"]
    dataset_id = dataset_gov["dataset_id"]
    dataset_commitment = dataset_gov["dataset_governance_commitment"]
    model_version_id = model_version_id_for_run(run_id)
    assessment_id = assessment_id_for_run(run_id)
    risk_id = risk_id_for_run(run_id)
    risk_class = (os.environ.get("AIGOV_RISK_CLASS") or "high").strip() or "high"
    severity = float(os.environ.get("AIGOV_RISK_SEVERITY", "4"))
    likelihood = float(os.environ.get("AIGOV_RISK_LIKELIHOOD", "0.3"))
    owner = (os.environ.get("AIGOV_RISK_OWNER") or "risk_owner").strip() or "risk_owner"
    reviewer = (os.environ.get("AIGOV_RISK_REVIEWER") or "risk_officer").strip() or "risk_officer"
    justification = (
        "Dataset governance commitment verified; evaluation threshold and human oversight requested before promotion."
    )
    risk_recorded_payload = {
        "assessment_id": assessment_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
        "risk_class": risk_class,
        "severity": severity,
        "likelihood": likelihood,
        "status": "submitted",
        "mitigation": "Establish evaluation threshold and require human promotion approval.",
        "owner": owner,
        "dataset_governance_commitment": dataset_commitment,
    }
    risk_mitigated_payload = {
        "assessment_id": assessment_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
        "status": "mitigated",
        "mitigation": "Mitigation applied: restrict intended use to the governed demo scope + enforce passed evaluation gate.",
        "dataset_governance_commitment": dataset_commitment,
    }
    risk_reviewed_payload = {
        "assessment_id": assessment_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
        "decision": "approve",
        "reviewer": reviewer,
        "justification": justification,
        "dataset_governance_commitment": dataset_commitment,
    }
    human_event_id = approved_human_event_id_for_run(run_id)
    artifact_path = f"python/artifacts/model_{run_id}.joblib"

    # Policy requires risk_recorded → risk_mitigated → risk_reviewed before human_approved / model_promoted.
    seq: list[dict[str, Any]] = [
        {
            "event_id": _demo_event_id("data_registered", run_id),
            "event_type": "data_registered",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "dataset": dataset_gov["dataset"],
                "dataset_version": dataset_gov["dataset_version"],
                "dataset_fingerprint": dataset_gov["dataset_fingerprint"],
                "dataset_governance_id": dataset_gov["dataset_governance_id"],
                "dataset_governance_commitment": dataset_commitment,
                "source": dataset_gov["source"],
                "intended_use": dataset_gov["intended_use"],
                "limitations": dataset_gov["limitations"],
                "quality_summary": dataset_gov["quality_summary"],
                "governance_status": dataset_gov["governance_status"],
            },
        },
        {
            "event_id": _demo_event_id("model_trained", run_id),
            "event_type": "model_trained",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "model_version_id": model_version_id,
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_type": "LogisticRegression",
                "artifact_path": artifact_path,
                "artifact_sha256": "govai_cli_demo_deterministic_placeholder",
            },
        },
        {
            "event_id": _demo_event_id("evaluation_reported", run_id),
            "event_type": "evaluation_reported",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "metric": "accuracy",
                "value": 0.95,
                "threshold": 0.8,
                "passed": True,
            },
        },
        {
            "event_id": _demo_event_id("risk_recorded", run_id),
            "event_type": "risk_recorded",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": risk_recorded_payload,
        },
        {
            "event_id": _demo_event_id("risk_mitigated", run_id),
            "event_type": "risk_mitigated",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": risk_mitigated_payload,
        },
        {
            "event_id": _demo_event_id("risk_reviewed", run_id),
            "event_type": "risk_reviewed",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": risk_reviewed_payload,
        },
        {
            "event_id": human_event_id,
            "event_type": "human_approved",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "scope": "model_promoted",
                "decision": "approve",
                "approved": True,
                "approver": "compliance_officer",
                "justification": "evaluation passed; risk review complete; approve promotion (cli demo).",
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": dataset_commitment,
            },
        },
        {
            "event_id": _demo_event_id("model_promoted", run_id),
            "event_type": "model_promoted",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "artifact_path": artifact_path,
                "promotion_reason": "approved_by_human",
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": dataset_commitment,
                "approved_human_event_id": human_event_id,
            },
        },
    ]

    client = GovAIClient(audit_url, api_key=api_key, default_project=os.environ.get("GOVAI_PROJECT"))
    try:
        for ev in seq:
            submit_event(client, ev)
        summary = get_compliance_summary(client, run_id)
    except (GovAIAPIError, GovAIHTTPError, OSError, TypeError, ValueError):
        return cli_exit.EX_ERR

    if isinstance(summary, dict) and summary.get("ok") is False:
        print(summary.get("message") or summary.get("error") or "error: /compliance-summary failed", file=sys.stderr)
        return cli_exit.EX_ERR

    verdict = summary.get("verdict") if isinstance(summary, dict) else None
    if not isinstance(verdict, str) or not verdict.strip():
        print("error: /compliance-summary missing verdict", file=sys.stderr)
        return cli_exit.EX_ERR

    verdict = verdict.strip()
    print(verdict)
    return _exit_for_compliance_verdict(verdict)


def build_parser() -> GovaiArgumentParser:
    p = GovaiArgumentParser(
        prog="govai",
        description=f"GovAI Terminal SDK — audit service workflow and assessment API (v{__version__}).",
    )
    p.add_argument(
        "--version",
        "-V",
        action="version",
        version=__version__,
        help="Print the package version and exit.",
    )
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help=f"Path to config JSON (default: {cli_config.CONFIG_ENV} env or .govai/config.json).",
    )
    p.add_argument(
        "--audit-base-url",
        default=None,
        help="Audit / ledger service base URL (overrides env/config when set).",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="Bearer token for the audit API (or GOVAI_API_KEY / config).",
    )
    p.add_argument(
        "--project",
        default=None,
        help="Optional project label for requests via X-GovAI-Project header (or GOVAI_PROJECT / X_GOVAI_PROJECT). Metadata only; does not select the ledger tenant.",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("GOVAI_TIMEOUT_SEC", "30")),
        help="HTTP timeout in seconds.",
    )
    p.add_argument(
        "--compact-json",
        action="store_true",
        help="Single-line JSON for assessment subcommands and compliance-summary.",
    )

    sub = p.add_subparsers(dest="cmd", required=False, metavar="COMMAND")

    s_init = sub.add_parser("init", help="Write .govai/config.json with audit URL and optional API key.")
    s_init.add_argument(
        "--url",
        dest="init_audit_url",
        default=cli_config.DEFAULT_AUDIT_BASE_URL,
        metavar="URL",
        help="Audit service base URL to store (default: %(default)s).",
    )
    s_init.add_argument(
        "--store-api-key",
        dest="init_api_key",
        default=None,
        help="Optional API key to store in config (plain text).",
    )

    s_run = sub.add_parser("run", help="Run scripted flows against the audit service.")
    s_run_sub = s_run.add_subparsers(dest="run_cmd", required=True)
    s_run_sub.add_parser("demo", help="Full evidence sequence for one run; prints VALID or BLOCKED.")
    s_run_sub.add_parser(
        "demo-deterministic",
        help="Deterministic demo: BLOCKED → missing evidence → VALID → export audit JSON (requires GOVAI_* env vars).",
    )

    s_demo_gp = sub.add_parser(
        "demo-golden-path",
        help="Generate deterministic CI-ready evidence artifacts (artefacts/<run_id>.json + artefacts/evidence_digest_manifest.json).",
    )
    s_demo_gp.add_argument(
        "--output-dir",
        dest="demo_output_dir",
        type=Path,
        default=Path("artefacts"),
        help="Output directory for artefacts (default: artefacts).",
    )
    s_demo_gp.add_argument(
        "--print-run-id",
        action="store_true",
        help="Print only the run_id to stdout (full instructions go to stderr).",
    )
    s_demo_gp.add_argument(
        "--show-api-key",
        action="store_true",
        help="Include the resolved api key value in the printed verify command (default: use $GOVAI_API_KEY).",
    )

    # Customer-facing evidence pack generator (deterministic by default).
    s_ep = sub.add_parser(
        "evidence-pack",
        help="Generate a minimal customer-ready evidence pack (<run_id>.json + evidence_digest_manifest.json).",
    )
    s_ep_sub = s_ep.add_subparsers(dest="evidence_pack_cmd", required=True, metavar="SUBCOMMAND")
    s_ep_init = s_ep_sub.add_parser(
        "init",
        help="Write <run_id>.json and evidence_digest_manifest.json to an output directory (deterministic default).",
    )
    s_ep_init.add_argument(
        "--run-id",
        default=None,
        help="Run id to embed in the evidence pack (default: CI-deterministic in GitHub Actions; otherwise uuid4).",
    )
    s_ep_init.add_argument(
        "--out",
        dest="evidence_pack_out_dir",
        type=Path,
        default=Path("evidence_pack"),
        help="Output directory for the evidence pack files (default: evidence_pack).",
    )
    s_ep_init.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting an existing output directory.",
    )

    s_preflight = sub.add_parser(
        "preflight",
        help="Fail-safe pre-deployment gate: validate local evidence-pack + audit service readiness; optional submit+digest verification.",
    )
    g_preflight_mode = s_preflight.add_mutually_exclusive_group(required=False)
    g_preflight_mode.add_argument(
        "--local-only",
        action="store_true",
        dest="local_only",
        help="Run only local evidence-pack validation (does not require GOVAI_AUDIT_BASE_URL).",
    )
    g_preflight_mode.add_argument(
        "--with-submit",
        action="store_true",
        dest="with_submit",
        help="Also submit a fresh evidence pack to the audit service and verify /bundle-hash digest (requires GOVAI_API_KEY).",
    )

    s_doctor = sub.add_parser(
        "doctor",
        help="(Deprecated) Alias for `govai preflight`.",
    )
    g_doctor_mode = s_doctor.add_mutually_exclusive_group(required=False)
    g_doctor_mode.add_argument(
        "--local-only",
        action="store_true",
        dest="local_only",
        help="Run only local evidence-pack validation (does not require GOVAI_AUDIT_BASE_URL).",
    )
    g_doctor_mode.add_argument(
        "--with-submit",
        action="store_true",
        dest="with_submit",
        help="Also submit a fresh evidence pack to the audit service and verify /bundle-hash digest (requires GOVAI_API_KEY).",
    )

    s_runtime_diag = sub.add_parser(
        "runtime-diagnostics",
        help="Probe /health, /ready, and /status for operator diagnostics (read-only).",
    )
    s_runtime_diag.add_argument(
        "--base-url",
        default=None,
        help="Audit service origin (default: GOVAI_AUDIT_BASE_URL or http://127.0.0.1:8088).",
    )
    s_runtime_diag.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout seconds.")
    s_runtime_diag.add_argument("--json", action="store_true", help="Machine-readable report on stdout.")

    s_verify = sub.add_parser("verify", help="Verify local docs/* artifacts and governance hash chain.")
    s_verify.add_argument("--run-id", default=None, help="Run UUID (fallback: env GOVAI_RUN_ID or RUN_ID).")
    s_verify.add_argument("--json", action="store_true", help="Machine-readable output on stdout.")

    s_fetch = sub.add_parser("fetch-bundle", help="GET /bundle + /bundle-hash → docs/evidence/<run_id>.json")
    s_fetch.add_argument("--run-id", default=None, help="Run UUID (fallback: env GOVAI_RUN_ID or RUN_ID).")

    s_sum = sub.add_parser("compliance-summary", help="GET /compliance-summary for a run_id.")
    s_sum.add_argument("--run-id", default=None, help="Run UUID (fallback: env GOVAI_RUN_ID or RUN_ID).")

    s_check = sub.add_parser(
        "check",
        help="Check compliance decision (VALID / INVALID / BLOCKED). Exit 0 only if VALID "
        "(2=INVALID · 3=BLOCKED · 1=infra/api error · 4=usage). Use verify-evidence-pack for production artefact gates.",
    )
    s_check.add_argument(
        "--run-id",
        dest="check_run_id",
        default=None,
        help="Run UUID (overrides positional / GOVAI_RUN_ID / RUN_ID).",
    )
    s_check.add_argument("run_id", nargs="?", default=None, help="Run UUID (fallback: env GOVAI_RUN_ID or RUN_ID).")
    s_check.add_argument(
        "--verify-artifacts",
        dest="verify_artifacts_dir",
        type=Path,
        default=None,
        help="Require evidence_digest_manifest.json under this directory to match hosted /bundle-hash "
        "(after verdict check).",
    )

    s_submit_pack = sub.add_parser(
        "submit-evidence-pack",
        help="POST every event from CI evidence bundle JSON (<dir>/<run_id>.json) to the audit API.",
    )
    s_submit_pack.add_argument(
        "--path",
        dest="evidence_pack_dir",
        required=True,
        type=Path,
        help="Directory containing <run_id>.json (from CI evidence_pack artifacts).",
    )
    s_submit_pack.add_argument("--run-id", default=None, help="Run id (fallback: env GOVAI_RUN_ID or RUN_ID).")

    s_verify_pack = sub.add_parser(
        "verify-evidence-pack",
        help="Hosted gate: /bundle-hash events_content_sha256 (mandatory) vs CI digest manifest; optional "
        "/api/export cross-check unless --require-export; then compliance-summary VALID. "
        "With --bundle, verify an offline signed audit export zip (Rust-native verifier).",
    )
    s_verify_pack.add_argument(
        "--path",
        dest="verify_pack_dir",
        required=False,
        type=Path,
        help="Directory with evidence_digest_manifest.json and <run_id>.json (CI artifacts).",
    )
    s_verify_pack.add_argument(
        "--bundle",
        default=None,
        type=Path,
        help="Offline signed audit export zip bundle (.zip) for Rust-native verification.",
    )
    s_verify_pack.add_argument(
        "--json",
        dest="verify_bundle_json",
        action="store_true",
        help="Emit structured JSON verification output (offline --bundle mode).",
    )
    s_verify_pack.add_argument(
        "--trust-json",
        dest="verify_bundle_trust_json",
        default=os.environ.get("AIGOV_POLICY_TRUST_ED25519_JSON"),
        help="Trusted Ed25519 public keys JSON for --bundle mode "
        "(default: env AIGOV_POLICY_TRUST_ED25519_JSON).",
    )
    s_verify_pack.add_argument(
        "--expected-issuer-id",
        dest="verify_bundle_expected_issuer",
        default=None,
        help="Optional expected signature issuer_id for --bundle mode.",
    )
    s_verify_pack.add_argument("--run-id", default=None, help="Run id (fallback: env GOVAI_RUN_ID or RUN_ID).")
    s_verify_pack.add_argument(
        "--require-export",
        action="store_true",
        help="Fail (exit 1) if /api/export cross-check cannot be performed or disagrees with /bundle-hash.",
    )
    s_verify_pack.add_argument(
        "--portable-only",
        action="store_true",
        help="Offline GovAI Core gate: validate manifest vs bundle digest only (no /bundle-hash or compliance-summary HTTP).",
    )
    s_verify_pack.add_argument(
        "--artifact-file",
        dest="artifact_file",
        default=None,
        help="Optional path to the promoted model artifact on disk. When provided, verify its SHA256 matches "
        "the model_promoted payload artifact digest in the evidence bundle.",
    )

    s_submit = sub.add_parser("submit-evidence", help="Submit one evidence event to POST /evidence.")
    s_submit.add_argument("--run-id", default=None, help="Run UUID (fallback: env GOVAI_RUN_ID or RUN_ID).")
    s_submit.add_argument("--event-type", required=True, help="Evidence event type (e.g. ai_discovery_reported).")
    s_submit.add_argument("--payload-file", default=None, help="Path to JSON file containing payload object.")
    s_submit.add_argument("--payload-json", default=None, help="Inline JSON object payload.")
    s_submit.add_argument("--event-id", default=None, help="Optional event_id override (default: uuid4).")
    s_submit.add_argument(
        "--actor",
        default=os.environ.get("AIGOV_ACTOR") or "govai_cli",
        help="Evidence actor label (default: env AIGOV_ACTOR or govai_cli).",
    )
    s_submit.add_argument(
        "--system",
        default=os.environ.get("AIGOV_SYSTEM") or "govai_cli",
        help="Evidence system label (default: env AIGOV_SYSTEM or govai_cli).",
    )

    s_discover = sub.add_parser(
        "discover",
        help="(Deprecated) Use `govai discovery scan`. Scan a repo deterministically and record ai_discovery_reported for the run.",
    )
    s_discover.add_argument("--run-id", default=None, help="Run UUID (fallback: env GOVAI_RUN_ID or RUN_ID).")
    s_discover.add_argument("--path", default=".", help="Path to scan (default: current directory).")
    s_discover.add_argument("--openai", default=None, help="Override scan result: true|false")
    s_discover.add_argument("--transformers", default=None, help="Override scan result: true|false")
    s_discover.add_argument("--model-artifacts", default=None, help="Override scan result: true|false")
    s_discover.add_argument(
        "--event-id",
        default=None,
        help="Optional event_id override (default: deterministic ai_discovery_reported_<run_id>).",
    )
    s_discover.add_argument(
        "--actor",
        default=os.environ.get("AIGOV_ACTOR") or "govai_cli",
        help="Evidence actor label (default: env AIGOV_ACTOR or govai_cli).",
    )
    s_discover.add_argument(
        "--system",
        default=os.environ.get("AIGOV_SYSTEM") or "govai_cli",
        help="Evidence system label (default: env AIGOV_SYSTEM or govai_cli).",
    )

    # New: discovery group
    s_discovery = sub.add_parser("discovery", help="AI discovery as silent infrastructure.")
    s_discovery_sub = s_discovery.add_subparsers(dest="discovery_cmd", required=True)

    s_discovery_scan = s_discovery_sub.add_parser(
        "scan",
        help="Scan a repository for AI usage (optionally submit to hosted backend for a run_id).",
    )
    s_discovery_scan.add_argument("--path", default=".", help="Path to scan (default: current directory).")
    s_discovery_scan.add_argument(
        "--no-history",
        action="store_true",
        help="Disable git history/change summary enrichment.",
    )
    s_discovery_scan.add_argument(
        "--format",
        default="json",
        choices=["json", "text"],
        help="Output format (default: json).",
    )
    s_discovery_scan.add_argument(
        "--submit",
        action="store_true",
        help="Submit `ai_discovery_reported` evidence event to hosted backend.",
    )
    s_discovery_scan.add_argument("--run-id", default=None, help="Run UUID (required with --submit).")
    s_discovery_scan.add_argument(
        "--event-id",
        default=None,
        help="Optional event_id override (default: ai_discovery_reported_<run_id>).",
    )
    s_discovery_scan.add_argument(
        "--actor",
        default=os.environ.get("AIGOV_ACTOR") or "govai_cli",
        help="Evidence actor label (default: env AIGOV_ACTOR or govai_cli).",
    )
    s_discovery_scan.add_argument(
        "--system",
        default=os.environ.get("AIGOV_SYSTEM") or "govai_cli",
        help="Evidence system label (default: env AIGOV_SYSTEM or govai_cli).",
    )

    s_explain = sub.add_parser(
        "explain",
        help="Explain verdict + requirements + blocked reasons (CI-friendly).",
    )
    s_explain.add_argument("--run-id", default=None, help="Run UUID (fallback: env GOVAI_RUN_ID or RUN_ID).")

    s_report = sub.add_parser("report", help="Render docs/reports/<run_id>.md from evidence JSON.")
    s_report.add_argument("--run-id", default=None, help="Run UUID (fallback: env GOVAI_RUN_ID or RUN_ID).")

    s_export = sub.add_parser("export-bundle", help="Write docs/audit + docs/packs zip for a run.")
    s_export.add_argument("--run-id", default=None, help="Run UUID (fallback: env GOVAI_RUN_ID or RUN_ID).")

    s_export_run = sub.add_parser(
        "export-run",
        help="GET /api/export/:run_id (machine-readable JSON).",
    )
    s_export_run.add_argument("--run-id", default=None, help="Run UUID (fallback: env GOVAI_RUN_ID or RUN_ID).")
    s_export_run.add_argument(
        "--project",
        default=os.environ.get("GOVAI_PROJECT"),
        help="Optional X-GovAI-Project header (or GOVAI_PROJECT); metadata/metering only, not ledger tenant.",
    )

    s_sign_export = sub.add_parser(
        "sign-audit-export",
        help="Sign aigov.audit_export.v1 JSON with Ed25519 (post-export; ledger unchanged).",
    )
    s_sign_export.add_argument("--in", dest="in_path", required=True, help="Input audit export JSON path.")
    s_sign_export.add_argument("--out", dest="out_path", required=True, help="Output signed audit export JSON path.")
    s_sign_export.add_argument("--issuer-id", required=True, help="Issuer id for signature trust lookup.")
    s_sign_export.add_argument("--signer", required=True, help="Signer identity label.")
    s_sign_export.add_argument("--private-key-base64", required=True, help="Ed25519 private key (base64, 32-byte seed).")
    s_sign_export.add_argument("--created-at-utc", required=True, help="RFC3339 UTC timestamp.")
    s_sign_export.add_argument("--expires-at-utc", default=None, help="Optional RFC3339 UTC timestamp.")

    s_verify_export = sub.add_parser(
        "verify-audit-export",
        help="Verify signed aigov.audit_export.v1 (schema, hashes, run_id, Ed25519).",
    )
    s_verify_export.add_argument("--path", required=True, help="Signed audit export JSON path.")
    s_verify_export.add_argument(
        "--trust-json",
        default=os.environ.get("AIGOV_POLICY_TRUST_ED25519_JSON"),
        help="Trusted Ed25519 public keys JSON (default: env AIGOV_POLICY_TRUST_ED25519_JSON).",
    )

    s_replay_export = sub.add_parser(
        "replay-audit-export",
        help="Deterministic governance replay from aigov.audit_export.v1 JSON.",
    )
    s_replay_export.add_argument("--path", required=True, help="Audit export JSON path.")
    s_replay_export.add_argument(
        "--json",
        action="store_true",
        help="Emit full ReplayResult JSON (default: human-readable summary).",
    )

    s_lineage_graph = sub.add_parser(
        "lineage-graph",
        help="Build governance lineage graph from aigov.audit_export.v1 JSON.",
    )
    s_lineage_graph.add_argument("--path", required=True, help="Audit export JSON path.")
    s_lineage_graph.add_argument(
        "--json",
        action="store_true",
        help="Emit full graph document JSON (default: human-readable summary).",
    )
    s_lineage_graph.add_argument(
        "--mermaid",
        action="store_true",
        help="Emit deterministic Mermaid flowchart (stdout).",
    )

    s_usage = sub.add_parser("usage", help="GET /usage (machine-readable JSON).")
    s_usage.add_argument(
        "--project",
        default=os.environ.get("GOVAI_PROJECT"),
        help="Optional X-GovAI-Project header (or GOVAI_PROJECT); metadata/metering only, not ledger tenant.",
    )

    c = sub.add_parser("create-assessment", help="Create a new assessment (POST /api/assessments).")
    c.add_argument("--system-name", required=True)
    c.add_argument("--intended-purpose", required=True)
    c.add_argument("--risk-class", required=True)
    c.add_argument("--team-id", default=os.environ.get("GOVAI_TEAM_ID"), help="Team UUID (or GOVAI_TEAM_ID).")
    c.add_argument("--created-by", default=os.environ.get("GOVAI_CREATED_BY"), help="User UUID (or GOVAI_CREATED_BY).")

    s_exp = sub.add_parser(
        "experiment",
        help="Auditability experiments: offline matrices plus optional GitHub Actions RWCI runner.",
    )
    s_exp_sub = s_exp.add_subparsers(dest="experiment_cmd", required=True, metavar="EXPERIMENT")

    s_exp_cfi = s_exp_sub.add_parser(
        "controlled-failure-injection",
        help="Deterministic rubric-driven failure injection (VALID/INVALID/BLOCKED; policy conformance).",
    )
    s_exp_cfi.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="DIR",
        help="Directory for controlled_failure_injection.csv and .json.",
    )

    s_exp_abe = s_exp_sub.add_parser(
        "artifact-bound",
        help="Artifact digest / bundle scenarios vs gate outcomes.",
    )
    s_exp_abe.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="DIR",
        help="Directory for artifact_bound_enforcement.csv and .json.",
    )

    s_exp_abr = s_exp_sub.add_parser(
        "artifact-bundle-replay",
        help="Experiment 2: concrete evidence bundles + manifest + export; gate vs replay rubric (200 runs).",
    )
    s_exp_abr.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="DIR",
        help="Directory for artifact_bundle_replay.json, csv, and artifact tree.",
    )

    s_exp_rwci = s_exp_sub.add_parser(
        "real-world-ci-runner",
        help="Fork repos, inject govai-audit workflow, run real GitHub Actions + govai check (requires tokens).",
    )
    s_exp_rwci.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="DIR",
        help="Directory for real_world_ci_injection.csv, .json, and artifacts/ logs.",
    )
    s_exp_rwci.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Maximum repositories from datasets/repos.json to process (after optional --repo filter).",
    )
    s_exp_rwci.add_argument(
        "--repo",
        default=None,
        metavar="NAME",
        help="Run only the dataset entry with this name (e.g. transformers).",
    )
    s_exp_rwci.add_argument(
        "--scenario",
        default=None,
        metavar="NAME",
        help="Run only this scenario: missing_evidence, missing_approval, or broken_traceability.",
    )

    s_exp_agg = s_exp_sub.add_parser(
        "aggregate",
        help="Merge CFI, optional ABE, and RWCI JSON into final_summary.json and final_table.csv.",
    )
    s_exp_agg.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="DIR",
        help="Directory for final outputs (final_summary.json, final_table.csv).",
    )
    s_exp_agg.add_argument(
        "--cfi",
        type=Path,
        required=True,
        metavar="DIR",
        help="Directory containing controlled_failure_injection.json.",
    )
    s_exp_agg.add_argument(
        "--abe",
        type=Path,
        default=None,
        metavar="DIR",
        help="Optional directory containing artifact_bound_enforcement.json.",
    )
    s_exp_agg.add_argument(
        "--rwci",
        type=Path,
        required=True,
        metavar="DIR",
        help="Directory containing real_world_ci_injection.json.",
    )

    # Policy tooling (compile-only product layer)
    s_policy = sub.add_parser("policy", help="Policy tools (modules + signed bundles).")
    s_policy_sub = s_policy.add_subparsers(dest="policy_cmd", required=True)

    s_policy_compile = s_policy_sub.add_parser(
        "compile",
        help="Compile a policy module YAML into a flat required_evidence set.",
    )
    s_policy_compile.add_argument(
        "--path",
        required=True,
        help="Path to policy module YAML (e.g. docs/policies/ai-act-high-risk.example.yaml).",
    )
    s_policy_compile.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON (policy identity + required_evidence).",
    )

    s_policy_sign = s_policy_sub.add_parser(
        "sign-bundle",
        help="Sign a govai.policy.v1 bundle using Ed25519 (governance-as-code).",
    )
    s_policy_sign.add_argument("--in", dest="in_path", required=True, help="Input policy bundle JSON path.")
    s_policy_sign.add_argument("--out", dest="out_path", required=True, help="Output policy bundle JSON path.")
    s_policy_sign.add_argument("--issuer-id", required=True, help="Policy issuer id (must match policy.issuer.issuer_id).")
    s_policy_sign.add_argument("--signer", required=True, help="Signer identity label.")
    s_policy_sign.add_argument("--private-key-base64", required=True, help="Ed25519 private key (base64, 32 bytes seed).")
    s_policy_sign.add_argument("--created-at-utc", required=True, help="RFC3339 UTC timestamp.")
    s_policy_sign.add_argument("--expires-at-utc", default=None, help="Optional RFC3339 UTC timestamp.")

    s_policy_verify = s_policy_sub.add_parser(
        "verify-bundle",
        help="Verify a govai.policy.v1 bundle signature using trusted public keys in AIGOV_POLICY_TRUST_ED25519_JSON.",
    )
    s_policy_verify.add_argument("--path", required=True, help="Policy bundle JSON path.")

    # Crypto verification (Sigstore/DSSE baseline)
    s_crypto = sub.add_parser("crypto", help="Cryptographic verification tools.")
    s_crypto_sub = s_crypto.add_subparsers(dest="crypto_cmd", required=True)

    s_crypto_verify_pack = s_crypto_sub.add_parser(
        "verify-evidence-pack",
        help="Verify a Sigstore DSSE attestation binds run_id to events_content_sha256.",
    )
    s_crypto_verify_pack.add_argument(
        "--run-id",
        required=True,
        help="Run id to verify.",
    )
    s_crypto_verify_pack.add_argument(
        "--attestation-bundle",
        required=True,
        help="Path to Sigstore bundle JSON (DSSE).",
    )
    s_crypto_verify_pack.add_argument(
        "--identity",
        required=True,
        help="Expected signing identity (e.g. email, workflow identity).",
    )
    s_crypto_verify_pack.add_argument(
        "--issuer",
        required=True,
        help="Expected OIDC issuer for the signing identity.",
    )
    s_crypto_verify_pack.add_argument(
        "--expected-events-content-sha256",
        required=True,
        help="Expected events_content_sha256 (usually from evidence_digest_manifest.json).",
    )
    s_crypto_verify_pack.add_argument(
        "--sigstore-env",
        default="prod",
        help="Sigstore environment: prod|staging (default: prod).",
    )

    # Phase 5 portable standards (offline validators; deterministic JSON on stdout).
    s_standards = sub.add_parser(
        "standards",
        help="Validate portable governance standards documents (JSON/YAML; no network; no ledger writes).",
    )
    s_standards_sub = s_standards.add_subparsers(dest="standards_cmd", required=True, metavar="SUBCOMMAND")

    s_st_cap = s_standards_sub.add_parser(
        "validate-capability-policy",
        help="Validate Open Capability Policy document; stdout is one JSON object.",
    )
    s_st_cap.add_argument("standards_path", metavar="PATH", type=str, help="Path to JSON or YAML document.")

    s_st_dg = s_standards_sub.add_parser(
        "validate-delegation-graph",
        help="Validate Delegation Graph document; stdout is one JSON object.",
    )
    s_st_dg.add_argument("standards_path", metavar="PATH", type=str, help="Path to JSON or YAML document.")

    s_st_tv = s_standards_sub.add_parser(
        "validate-trace-verification-plan",
        help="Validate Trace Verification Plan document; stdout is one JSON object.",
    )
    s_st_tv.add_argument("standards_path", metavar="PATH", type=str, help="Path to JSON or YAML document.")

    s_st_ep = s_standards_sub.add_parser(
        "validate-evidence-pack",
        help="Validate Governance Evidence Pack document; stdout is one JSON object.",
    )
    s_st_ep.add_argument("standards_path", metavar="PATH", type=str, help="Path to JSON or YAML document.")

    return p


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv if argv is not None else sys.argv[1:])
    parser = build_parser()
    try:
        args = parser.parse_args(args_list)
    except SystemExit as se:
        return _system_exit_code(se)

    if args.cmd is None:
        parser.print_help()
        return cli_exit.EX_OK

    if args.cmd == "standards":
        from aigov_py.standards.cli import dispatch_govai_standards

        return int(dispatch_govai_standards(args))

    if args.cmd == "policy" and getattr(args, "policy_cmd", None) == "compile":
        raw_path = str(getattr(args, "path", "") or "").strip()
        if not raw_path:
            print("error: --path is required", file=sys.stderr)
            return cli_exit.EX_USAGE
        try:
            pol = load_policy_module(raw_path)
            req = sorted(required_evidence_from_policy(pol))
        except ValueError as e:
            print(f"error: invalid policy module: {e}", file=sys.stderr)
            return cli_exit.EX_USAGE
        except OSError as e:
            print(f"error: cannot read policy module: {e}", file=sys.stderr)
            return cli_exit.EX_ERR

        if bool(getattr(args, "json", False)):
            _print_json(
                {
                    "policy": policy_identity(pol),
                    "required_evidence": req,
                },
                compact=False,
            )
        else:
            for item in req:
                print(item)
        return cli_exit.EX_OK

    if args.cmd == "policy" and getattr(args, "policy_cmd", None) == "sign-bundle":
        try:
            sign_policy_bundle_ed25519(
                str(getattr(args, "in_path")),
                out_path=str(getattr(args, "out_path")),
                issuer_id=str(getattr(args, "issuer_id")),
                signer=str(getattr(args, "signer")),
                private_key_base64=str(getattr(args, "private_key_base64")),
                created_at_utc=str(getattr(args, "created_at_utc")),
                expires_at_utc=getattr(args, "expires_at_utc"),
            )
        except Exception as e:  # noqa: BLE001
            print(f"error: policy sign failed: {e}", file=sys.stderr)
            return cli_exit.EX_ERR
        return cli_exit.EX_OK

    if args.cmd == "policy" and getattr(args, "policy_cmd", None) == "verify-bundle":
        raw = str(getattr(args, "path", "") or "").strip()
        if not raw:
            print("error: --path is required", file=sys.stderr)
            return cli_exit.EX_USAGE
        try:
            doc = json.loads(Path(raw).read_text(encoding="utf-8"))
            trust_raw = os.environ.get("AIGOV_POLICY_TRUST_ED25519_JSON", "")
            trust = load_trust_from_env_json(trust_raw)
            if not trust:
                raise ValueError("AIGOV_POLICY_TRUST_ED25519_JSON is empty/unset")
            verify_policy_bundle_ed25519(doc, trust=trust)
        except Exception as e:  # noqa: BLE001
            print(f"error: policy verify failed: {e}", file=sys.stderr)
            return cli_exit.EX_ERR
        print("ok")
        return cli_exit.EX_OK

    if args.cmd == "crypto" and getattr(args, "crypto_cmd", None) == "verify-evidence-pack":
        run_id = str(getattr(args, "run_id") or "").strip()
        bundle_path = str(getattr(args, "attestation_bundle") or "").strip()
        identity = str(getattr(args, "identity") or "").strip()
        issuer = str(getattr(args, "issuer") or "").strip()
        expected = str(getattr(args, "expected_events_content_sha256") or "").strip().lower()
        sigstore_env = str(getattr(args, "sigstore_env") or "prod").strip()

        if not run_id or not bundle_path or not identity or not issuer or not expected:
            print("error: missing required arguments", file=sys.stderr)
            return cli_exit.EX_USAGE

        try:
            payload_type, payload = verify_dsse_bundle(
                bundle_json_bytes=load_bundle_bytes(bundle_path),
                identity=SigstoreIdentity(identity=identity, issuer=issuer),
                sigstore_env=sigstore_env,
            )
            doc = parse_json_payload(payload)
            schema = str(doc.get("schema") or "").strip()
            if schema != "aigov.evidence_attestation.v1":
                raise ValueError(f"unexpected attestation schema: {schema!r}")
            got_run = str(doc.get("run_id") or "").strip()
            got_digest = str(doc.get("events_content_sha256") or "").strip().lower()
            if got_run != run_id:
                raise ValueError(f"run_id mismatch: expected={run_id} got={got_run}")
            if got_digest != expected:
                raise ValueError(
                    f"events_content_sha256 mismatch: expected={expected} got={got_digest}"
                )
            if not str(payload_type or "").strip():
                raise ValueError("missing DSSE payload type")
        except Exception as e:  # noqa: BLE001
            print(f"error: crypto verify failed: {e}", file=sys.stderr)
            return cli_exit.EX_ERR

        print("ok")
        return cli_exit.EX_OK

    if args.cmd == "experiment":
        from aigov_py.experiments import aggregate as exp_aggregate
        from aigov_py.experiments import artifact_bound_enforcement as exp_abe
        from aigov_py.experiments import artifact_bundle_replay as exp_abr
        from aigov_py.experiments import controlled_failure_injection as exp_cfi
        from aigov_py.experiments import real_world_ci_runner as exp_rwci_runner

        ec = getattr(args, "experiment_cmd", "")
        if ec == "controlled-failure-injection":
            return exp_cfi.main_cli(getattr(args, "output"))
        if ec == "artifact-bound":
            return exp_abe.main_cli(getattr(args, "output"))
        if ec == "artifact-bundle-replay":
            return exp_abr.main_cli(output=getattr(args, "output"))
        if ec == "real-world-ci-runner":
            return exp_rwci_runner.main_cli(
                output=getattr(args, "output"),
                limit=int(getattr(args, "limit", 10)),
                repo=getattr(args, "repo", None),
                scenario=getattr(args, "scenario", None),
            )
        if ec == "aggregate":
            return exp_aggregate.main_cli(
                output=getattr(args, "output"),
                cfi=getattr(args, "cfi"),
                abe=getattr(args, "abe"),
                rwci=getattr(args, "rwci"),
            )
        print("unknown experiment", file=sys.stderr)
        return cli_exit.EX_USAGE

    if args.cmd == "init":
        try:
            path = _config_path_from_args(args) or cli_config.default_config_path()
            written = cli_config.save_config(
                audit_base_url=str(args.init_audit_url),
                api_key=args.init_api_key,
                path=path,
            )
        except OSError as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
            return cli_exit.EX_ERR
        out = {"ok": True, "path": str(written), "audit_base_url": str(args.init_audit_url).rstrip("/")}
        _print_json(out, compact=args.compact_json)
        return cli_exit.EX_OK

    if args.cmd == "run" and getattr(args, "run_cmd", None) == "demo":
        audit_url = _audit_url(args)
        api_key = _api_key(args)
        return run_demo(audit_url, api_key)

    if args.cmd == "run" and getattr(args, "run_cmd", None) == "demo-deterministic":
        return run_demo_deterministic(timeout_sec=float(getattr(args, "timeout", 30.0)))

    if args.cmd == "demo-golden-path":
        run_id = str(uuid.uuid4())
        out_dir = Path(getattr(args, "demo_output_dir"))
        res = generate_demo_golden_path(run_id=run_id, output_dir=out_dir)

        audit_url = _audit_url(args)
        api_key = _api_key(args)

        if bool(getattr(args, "print_run_id", False)):
            print(res.run_id)
            stream = sys.stderr
        else:
            stream = sys.stdout

        # Proactive local operator hint: if localhost and /ready is unreachable.
        if audit_url and _is_localhost_url(audit_url):
            try:
                client = GovAIClient(audit_url.rstrip("/"), api_key=api_key, default_project=os.environ.get("GOVAI_PROJECT"))
                _ = client.request_json("GET", "/ready", timeout=2.0, raise_on_body_ok_false=False)
            except Exception:
                print(
                    "Operator audit runtime not reachable at GOVAI_AUDIT_BASE_URL. "
                    "Start GovAI Platform / self-host stack, or use offline portable targets.",
                    file=stream,
                )
                print("", file=stream)

        print(f"run_id: {res.run_id}", file=stream)
        print(f"artefacts_path: {res.artefacts_path}", file=stream)
        print("", file=stream)
        print("next steps (run in order — submit before verify/check):", file=stream)
        print("", file=stream)
        prefix: list[str] = ["govai"]
        project = _resolve_project(args)
        if project:
            prefix += ["--project", project]
        if audit_url:
            prefix += ["--audit-base-url", audit_url]
        # Never leak key by default; always prefer env var placeholder for copy/paste onboarding.
        if api_key and bool(getattr(args, "show_api_key", False)):
            prefix += ["--api-key", api_key]
        else:
            prefix += ["--api-key", "$GOVAI_API_KEY"]
        artefacts = str(res.artefacts_path)
        submit_cmd = prefix + ["submit-evidence-pack", "--path", artefacts, "--run-id", res.run_id]
        verify_cmd = prefix + ["verify-evidence-pack", "--path", artefacts, "--run-id", res.run_id]
        check_cmd = prefix + ["check", "--run-id", res.run_id]

        print(_shell_argv_join(submit_cmd), file=stream)
        print(_shell_argv_join(verify_cmd), file=stream)
        print(_shell_argv_join(check_cmd), file=stream)

        if not api_key:
            print("", file=stream)
            print("missing GOVAI_API_KEY. Set it, e.g.:", file=stream)
            print('export GOVAI_API_KEY="YOUR_LOCAL_KEY"', file=stream)
        if not audit_url:
            print("", file=stream)
            print("missing GOVAI_AUDIT_BASE_URL. Set it, e.g.:", file=stream)
            print('export GOVAI_AUDIT_BASE_URL="http://127.0.0.1:8088"', file=stream)
        return cli_exit.EX_OK

    if args.cmd == "evidence-pack" and getattr(args, "evidence_pack_cmd", None) == "init":
        raw_run_id = getattr(args, "run_id", None)
        run_id = raw_run_id if isinstance(raw_run_id, str) and raw_run_id != "" else _default_run_id_for_evidence_pack_init()
        out_dir = Path(getattr(args, "evidence_pack_out_dir")).expanduser().resolve()
        force = bool(getattr(args, "force", False))

        if out_dir.exists():
            if not out_dir.is_dir():
                print(
                    f"error: output path exists and is not a directory: {out_dir}",
                    file=sys.stderr,
                )
                return cli_exit.EX_USAGE
            if not force:
                print(
                    "error: output directory already exists; refusing to overwrite.\n"
                    f"  path: {out_dir}\n"
                    "  hint: choose a new --out directory, or pass --force to overwrite",
                    file=sys.stderr,
                )
                return cli_exit.EX_USAGE

        try:
            res = generate_demo_golden_path(run_id=run_id, output_dir=out_dir)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return cli_exit.EX_USAGE
        except OSError as exc:
            print(f"error: cannot write evidence pack: {exc}", file=sys.stderr)
            return cli_exit.EX_ERR
        except Exception as exc:
            print(f"error: evidence pack generation failed: {exc}", file=sys.stderr)
            return cli_exit.EX_ERR

        # Keep stdout minimal and copy/paste friendly.
        print(f"run_id: {res.run_id}")
        print(f"path: {res.artefacts_path}")
        return cli_exit.EX_OK

    audit_url = _audit_url(args)
    api_key = _api_key(args)
    project = _resolve_project(args)
    repro = _format_repro_command(args_list)

    if args.cmd == "runtime-diagnostics":
        from aigov_py.runtime_diagnostics import run_runtime_diagnostics

        base = (
            getattr(args, "base_url", None)
            or os.environ.get("GOVAI_AUDIT_BASE_URL")
            or "http://127.0.0.1:8088"
        ).strip()
        if not base:
            print("error: --base-url or GOVAI_AUDIT_BASE_URL required", file=sys.stderr)
            return cli_exit.EX_USAGE
        return run_runtime_diagnostics(
            base,
            timeout_sec=float(getattr(args, "timeout", 10.0)),
            json_out=bool(getattr(args, "json", False)),
        )

    if args.cmd == "preflight":
        local_only = bool(getattr(args, "local_only", False))
        with_submit = bool(getattr(args, "with_submit", False))
        audit_env = _require_env_nonempty("GOVAI_AUDIT_BASE_URL")
        api_env = _require_env_nonempty("GOVAI_API_KEY")
        if not local_only and not audit_env:
            print("error: govai preflight requires GOVAI_AUDIT_BASE_URL (unless --local-only)", file=sys.stderr)
            print('hint: export GOVAI_AUDIT_BASE_URL="https://YOUR_GOVAI_AUDIT_SERVICE"', file=sys.stderr)
            return cli_exit.EX_USAGE
        if with_submit and not api_env:
            print("error: govai preflight --with-submit requires GOVAI_API_KEY", file=sys.stderr)
            print('hint: export GOVAI_API_KEY="YOUR_API_KEY"', file=sys.stderr)
            return cli_exit.EX_USAGE
        return preflight(
            local_only=local_only,
            submit=with_submit,
            timeout_sec=float(getattr(args, "timeout", 30.0)),
            audit_url=audit_url,
            api_key=api_key,
        )

    if args.cmd == "doctor":
        print("warning: 'govai doctor' is deprecated, use 'govai preflight'", file=sys.stderr, flush=True)
        local_only = bool(getattr(args, "local_only", False))
        with_submit = bool(getattr(args, "with_submit", False))
        audit_env = _require_env_nonempty("GOVAI_AUDIT_BASE_URL")
        api_env = _require_env_nonempty("GOVAI_API_KEY")
        if not local_only and not audit_env:
            print("error: govai preflight requires GOVAI_AUDIT_BASE_URL (unless --local-only)", file=sys.stderr)
            print('hint: export GOVAI_AUDIT_BASE_URL="https://YOUR_GOVAI_AUDIT_SERVICE"', file=sys.stderr)
            return cli_exit.EX_USAGE
        if with_submit and not api_env:
            print("error: govai preflight --with-submit requires GOVAI_API_KEY", file=sys.stderr)
            print('hint: export GOVAI_API_KEY="YOUR_API_KEY"', file=sys.stderr)
            return cli_exit.EX_USAGE
        return preflight(
            local_only=local_only,
            submit=with_submit,
            timeout_sec=float(getattr(args, "timeout", 30.0)),
            audit_url=audit_url,
            api_key=api_key,
        )

    if args.cmd == "verify":
        summary_verdict = "ERROR"
        summary_codes: list[str] = ["INTEGRATION_ERROR"]
        summary_next_action = "Fix the reported issue, then rerun the same command."
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID (or RUN_ID)", file=sys.stderr)
            _print_final_summary(
                verdict="ERROR",
                reason_codes=["USAGE_ERROR"],
                next_action="Pass --run-id (or set GOVAI_RUN_ID / RUN_ID), then rerun.",
                repro=repro,
            )
            return cli_exit.EX_USAGE
        prev_audit = os.environ.get("AIGOV_AUDIT_URL")
        prev_end = os.environ.get("AIGOV_AUDIT_ENDPOINT")
        try:
            os.environ["AIGOV_AUDIT_URL"] = audit_url
            os.environ["AIGOV_AUDIT_ENDPOINT"] = audit_url
            rc = verify_mod.verify(run_id, as_json=args.json)
            if rc == cli_exit.EX_OK:
                summary_verdict = "VALID"
                summary_codes = []
                summary_next_action = "Proceed (artifacts verified)."
            return rc
        finally:
            if prev_audit is None:
                os.environ.pop("AIGOV_AUDIT_URL", None)
            else:
                os.environ["AIGOV_AUDIT_URL"] = prev_audit
            if prev_end is None:
                os.environ.pop("AIGOV_AUDIT_ENDPOINT", None)
            else:
                os.environ["AIGOV_AUDIT_ENDPOINT"] = prev_end
            _print_final_summary(
                verdict=summary_verdict,
                reason_codes=summary_codes,
                next_action=summary_next_action,
                repro=repro,
            )

    if args.cmd == "fetch-bundle":
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID (or RUN_ID)", file=sys.stderr)
            return cli_exit.EX_USAGE
        prev_audit = os.environ.get("AIGOV_AUDIT_URL")
        prev_end = os.environ.get("AIGOV_AUDIT_ENDPOINT")
        try:
            os.environ["AIGOV_AUDIT_URL"] = audit_url
            os.environ["AIGOV_AUDIT_ENDPOINT"] = audit_url
            fetch_bundle_from_govai.main(["govai", run_id])
        except SystemExit as se:
            return _system_exit_code(se)
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
            return cli_exit.EX_ERR
        finally:
            if prev_audit is None:
                os.environ.pop("AIGOV_AUDIT_URL", None)
            else:
                os.environ["AIGOV_AUDIT_URL"] = prev_audit
            if prev_end is None:
                os.environ.pop("AIGOV_AUDIT_ENDPOINT", None)
            else:
                os.environ["AIGOV_AUDIT_ENDPOINT"] = prev_end
        return cli_exit.EX_OK

    if args.cmd == "compliance-summary":
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID (or RUN_ID)", file=sys.stderr)
            return cli_exit.EX_USAGE
        try:
            client = GovAIClient(audit_url, api_key=api_key, default_project=project)
            out = client.request_json(
                "GET",
                "/compliance-summary",
                params={"run_id": run_id},
                raise_on_body_ok_false=False,
                timeout=args.timeout,
            )
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
            return cli_exit.EX_ERR
        _print_json(out, compact=args.compact_json)
        return cli_exit.EX_OK

    if args.cmd == "check":
        summary_verdict = "ERROR"
        summary_obj: dict[str, Any] | None = None
        summary_codes: list[str] = ["INTEGRATION_ERROR"]
        summary_next_action = "Check GOVAI_AUDIT_BASE_URL and GOVAI_API_KEY (and network), then rerun the same command."
        summary_triggered_by: list[str] | None = None
        opt = (getattr(args, "check_run_id", None) or "").strip()
        run_id = opt or _resolve_run_id(args)
        if not run_id:
            print("run id required", file=sys.stderr)
            _print_final_summary(
                verdict="ERROR",
                reason_codes=["USAGE_ERROR"],
                next_action="Pass --run-id (or set GOVAI_RUN_ID / RUN_ID), then rerun.",
                repro=repro,
            )
            return cli_exit.EX_USAGE

        # Optional local enrichment for summary output (append-only).
        raw_scan_path = (os.environ.get("GOVAI_DISCOVERY_PATH") or "").strip()
        if raw_scan_path:
            try:
                scan_path = Path(raw_scan_path).expanduser()
                if scan_path.exists():
                    summary_triggered_by = _triggered_by_from_repo_scan(scan_path)
            except Exception:
                summary_triggered_by = None

        client = GovAIClient(audit_url, api_key=api_key, default_project=project)
        vad = getattr(args, "verify_artifacts_dir", None)
        try:
            if vad is not None:
                artifact_dir = Path(vad).expanduser().resolve()
                rc, reason = _verify_artifact_digest_continuity(client, artifact_dir=artifact_dir, run_id=run_id)
                if rc != cli_exit.EX_OK:
                    summary_verdict = "ERROR"
                    summary_codes = [reason or "DIGEST_MISMATCH"]
                    summary_next_action = "Fix evidence_digest_manifest.json / hosted bundle-hash mismatch, then rerun."
                    return rc

            code_sum, summary = _compliance_verdict_or_err(client, run_id, timeout=args.timeout)
            if code_sum != cli_exit.EX_OK or summary is None:
                summary_verdict = "ERROR"
                summary_codes = ["INTEGRATION_ERROR"]
                return code_sum

            summary_obj = summary
            verdict = str(summary.get("verdict") or "").strip()
            print(verdict, flush=True)
            if verdict in ("BLOCKED", "INVALID"):
                _print_check_failure_details(summary, verdict)

            summary_verdict, summary_codes, summary_next_action, _ = _summary_for_compliance(
                verdict=verdict,
                summary=summary_obj,
                repro=repro,
            )
            return _exit_for_compliance_verdict(verdict)
        finally:
            _print_final_summary(
                verdict=summary_verdict,
                reason_codes=summary_codes,
                triggered_by=summary_triggered_by,
                next_action=summary_next_action,
                repro=repro,
            )

    if args.cmd == "submit-evidence-pack":
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID (or RUN_ID)", file=sys.stderr)
            return cli_exit.EX_USAGE
        base = Path(getattr(args, "evidence_pack_dir")).expanduser().resolve()
        try:
            bundle, _path = eag.load_bundle(run_id, base)
        except (OSError, json.JSONDecodeError, TypeError, FileNotFoundError) as exc:
            print(f"ERROR: cannot load evidence bundle: {exc}", file=sys.stderr)
            return cli_exit.EX_ERR
        client = GovAIClient(audit_url, api_key=api_key, default_project=project)

        def _progress(i: int, n: int, et: str) -> None:
            print(f"[{i}/{n}] POST /evidence ({et})")

        try:
            eag.submit_evidence_bundle_events(client, bundle=bundle, progress=_progress)
        except (GovAIAPIError, GovAIHTTPError) as exc:
            print(f"ERROR: evidence submit failed: {exc}", file=sys.stderr)
            return cli_exit.EX_ERR
        except (TypeError, ValueError) as exc:
            print(f"ERROR: invalid evidence bundle: {exc}", file=sys.stderr)
            return cli_exit.EX_ERR
        except Exception as exc:
            print(f"ERROR: unexpected failure: {exc}", file=sys.stderr)
            return cli_exit.EX_ERR
        print("submitted evidence pack")
        return cli_exit.EX_OK

    if args.cmd == "verify-evidence-pack":
        bundle_path = getattr(args, "bundle", None)
        if bundle_path is not None and str(bundle_path).strip():
            from aigov_py.verify_audit_export_bundle import verify_audit_export_bundle

            trust_raw = str(getattr(args, "verify_bundle_trust_json", "") or "").strip()
            if trust_raw:
                os.environ["AIGOV_POLICY_TRUST_ED25519_JSON"] = trust_raw
            try:
                result = verify_audit_export_bundle(
                    Path(str(bundle_path)).expanduser().resolve(),
                    json_output=True,
                    expected_issuer_id=getattr(args, "verify_bundle_expected_issuer", None),
                )
            except Exception as e:  # noqa: BLE001
                print(f"error: bundle verification failed: {e}", file=sys.stderr)
                return cli_exit.EX_ERR
            if getattr(args, "verify_bundle_json", False):
                print(json.dumps(result, indent=2))
            else:
                print(f"overall_status={result.get('overall_status')}")
                for key in (
                    "canonical_bundle_digest_verified",
                    "signature_verified",
                    "schema_version_supported",
                    "manifest_complete",
                    "all_manifest_hashes_match",
                    "all_evidence_references_resolve",
                    "replay_validation_passed",
                    "unsigned_dependency_detected",
                ):
                    print(f"{key}={result.get(key)}")
                failures = result.get("failures") or []
                if failures:
                    print("failures:")
                    for item in failures:
                        if isinstance(item, dict):
                            print(
                                f"  - [{item.get('stage')}] {item.get('code')}: {item.get('message')}"
                            )
            if str(result.get("overall_status") or "") != "success":
                return cli_exit.EX_ERR
            return cli_exit.EX_OK

        verify_pack_dir = getattr(args, "verify_pack_dir", None)
        if verify_pack_dir is None or not str(verify_pack_dir).strip():
            print(
                "error: pass --path (CI artefacts directory) or --bundle (signed export zip)",
                file=sys.stderr,
            )
            return cli_exit.EX_USAGE

        summary_verdict = "ERROR"
        summary_obj: dict[str, Any] | None = None
        summary_codes: list[str] = ["INTEGRATION_ERROR"]
        summary_next_action = "Check GOVAI_AUDIT_BASE_URL and GOVAI_API_KEY (and network), then rerun the same command."
        summary_triggered_by: list[str] | None = None
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID (or RUN_ID)", file=sys.stderr)
            _print_final_summary(
                verdict="ERROR",
                reason_codes=["USAGE_ERROR"],
                next_action="Pass --run-id (or set GOVAI_RUN_ID / RUN_ID), then rerun.",
                repro=repro,
            )
            return cli_exit.EX_USAGE
        artifact_dir = Path(verify_pack_dir).expanduser().resolve()

        # Optional local enrichment for summary output (append-only).
        raw_scan_path = (os.environ.get("GOVAI_DISCOVERY_PATH") or "").strip()
        if raw_scan_path:
            try:
                scan_path = Path(raw_scan_path).expanduser()
                if scan_path.exists():
                    summary_triggered_by = _triggered_by_from_repo_scan(scan_path)
            except Exception:
                summary_triggered_by = None

        client = GovAIClient(audit_url, api_key=api_key, default_project=project)
        try:
            try:
                _b, bundle_path = eag.load_bundle(run_id, artifact_dir)
            except (OSError, json.JSONDecodeError, TypeError, FileNotFoundError) as exc:
                print(f"ERROR: cannot load evidence bundle: {exc}", file=sys.stderr)
                summary_verdict = "ERROR"
                summary_codes = ["EVIDENCE_BUNDLE_INVALID"]
                summary_next_action = "Fix the evidence pack JSON files, then rerun the same command."
                return cli_exit.EX_ERR
            # Ensure manifest referent exists (CI must ship both files).
            _ = bundle_path
            portable_only = bool(getattr(args, "portable_only", False))
            rc, reason = _verify_artifact_digest_continuity(
                client,
                artifact_dir=artifact_dir,
                run_id=run_id,
                require_export=bool(getattr(args, "require_export", False)),
                artifact_file=(
                    Path(str(getattr(args, "artifact_file") or "")).expanduser().resolve()
                    if str(getattr(args, "artifact_file") or "").strip()
                    else None
                ),
                portable_only=portable_only,
            )
            if rc != cli_exit.EX_OK:
                summary_verdict = "ERROR"
                summary_codes = [reason or "DIGEST_MISMATCH"]
                summary_next_action = (
                    "Fix evidence_digest_manifest.json / bundle digest mismatch, then rerun."
                    if portable_only
                    else "Fix evidence_digest_manifest.json / hosted bundle-hash mismatch, then rerun."
                )
                return rc
            if portable_only:
                print("PORTABLE_OK")
                summary_verdict = "VALID"
                summary_codes = ["PORTABLE_DIGEST_OK"]
                summary_next_action = (
                    "Submit pack to operator-hosted runtime when required (GovAI Platform)."
                )
                return cli_exit.EX_OK
            code_sum, summary = _compliance_verdict_or_err(client, run_id, timeout=args.timeout)
            if code_sum != cli_exit.EX_OK or summary is None:
                summary_verdict = "ERROR"
                summary_codes = ["INTEGRATION_ERROR"]
                return code_sum
            summary_obj = summary
            verdict = str(summary.get("verdict") or "").strip()
            print(verdict)
            if verdict in ("BLOCKED", "INVALID"):
                _print_check_failure_details(summary, verdict)
            summary_verdict, summary_codes, summary_next_action, _ = _summary_for_compliance(
                verdict=verdict,
                summary=summary_obj,
                repro=repro,
            )
            return _exit_for_compliance_verdict(verdict)
        finally:
            _print_final_summary(
                verdict=summary_verdict,
                reason_codes=summary_codes,
                triggered_by=summary_triggered_by,
                next_action=summary_next_action,
                repro=repro,
            )

    if args.cmd == "submit-evidence":
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID (or RUN_ID)", file=sys.stderr)
            return cli_exit.EX_USAGE

        event_type = (getattr(args, "event_type", None) or "").strip()
        if not event_type:
            print("event type required: pass --event-type", file=sys.stderr)
            return cli_exit.EX_USAGE

        try:
            payload_obj = _load_payload_one_of(
                payload_file=getattr(args, "payload_file", None),
                payload_json=getattr(args, "payload_json", None),
            )
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"invalid payload: {e}", file=sys.stderr)
            return cli_exit.EX_USAGE

        event_id = (getattr(args, "event_id", None) or "").strip() or str(uuid.uuid4())
        actor = (getattr(args, "actor", None) or "govai_cli").strip() or "govai_cli"
        system = (getattr(args, "system", None) or "govai_cli").strip() or "govai_cli"

        ev = {
            "event_id": event_id,
            "event_type": event_type,
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": payload_obj,
        }

        try:
            client = GovAIClient(audit_url, api_key=api_key, default_project=project)
            out = submit_event(client, ev)
        except Exception as e:
            print(str(e), file=sys.stderr)
            return cli_exit.EX_ERR

        _print_json(out, compact=True)
        return cli_exit.EX_OK

    if args.cmd == "discover":
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID", file=sys.stderr)
            return cli_exit.EX_USAGE

        scan_path = Path(getattr(args, "path", ".")).expanduser()
        if not scan_path.exists():
            print(f"scan path does not exist: {scan_path}", file=sys.stderr)
            return cli_exit.EX_USAGE

        try:
            scan = scan_repo(scan_path, include_history=True)
            openai_override = _parse_bool_override(getattr(args, "openai", None), name="--openai")
            transformers_override = _parse_bool_override(getattr(args, "transformers", None), name="--transformers")
            model_artifacts_override = _parse_bool_override(
                getattr(args, "model_artifacts", None),
                name="--model-artifacts",
            )
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return cli_exit.EX_USAGE
        except Exception as e:
            print(str(e), file=sys.stderr)
            return cli_exit.EX_ERR

        scan_openai = _signal_from_scan(scan, "openai")
        scan_transformers = _signal_from_scan(scan, "transformers")
        scan_model_artifacts = _signal_from_scan(scan, "model_artifacts")

        openai = scan_openai if openai_override is None else openai_override
        transformers = scan_transformers if transformers_override is None else transformers_override
        model_artifacts = scan_model_artifacts if model_artifacts_override is None else model_artifacts_override

        overrides_used = any(
            value is not None
            for value in (
                openai_override,
                transformers_override,
                model_artifacts_override,
            )
        )

        findings = _coerce_findings(scan)
        finding_types = sorted(
            {
                str(f.get("type"))
                for f in findings
                if isinstance(f, dict) and f.get("type") is not None
            }
        )

        payload_obj = {
            "openai": openai,
            "transformers": transformers,
            "model_artifacts": model_artifacts,
            "findings_count": len(findings),
            "finding_types": finding_types,
        }

        print(f"AI discovery scanned path: {scan_path.resolve()}", file=sys.stderr)
        if findings:
            grouped: dict[str, int] = {}
            for finding in findings:
                raw_type = finding.get("type") if isinstance(finding, dict) else None
                finding_type = str(raw_type or "unknown")
                grouped[finding_type] = grouped.get(finding_type, 0) + 1
            print("AI discovery findings:", file=sys.stderr)
            for key in sorted(grouped):
                print(f" {key}: {grouped[key]}", file=sys.stderr)
        else:
            print("No AI usage signals detected.", file=sys.stderr)

        print("AI discovery recorded:", file=sys.stderr)
        print(f" openai={str(openai).lower()}", file=sys.stderr)
        print(f" transformers={str(transformers).lower()}", file=sys.stderr)
        print(f" model_artifacts={str(model_artifacts).lower()}", file=sys.stderr)
        if overrides_used:
            print(" note: one or more flags overrode scan results", file=sys.stderr)

        event_id = (getattr(args, "event_id", None) or "").strip() or f"ai_discovery_reported_{run_id}"
        actor = (getattr(args, "actor", None) or "govai_cli").strip() or "govai_cli"
        system = (getattr(args, "system", None) or "govai_cli").strip() or "govai_cli"

        ev = {
            "event_id": event_id,
            "event_type": "ai_discovery_reported",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": payload_obj,
        }

        try:
            client = GovAIClient(audit_url, api_key=api_key, default_project=project)
            out = submit_event(client, ev)
        except Exception as e:
            print(str(e), file=sys.stderr)
            return cli_exit.EX_ERR

        _print_json(out, compact=True)
        return cli_exit.EX_OK

    if args.cmd == "discovery" and getattr(args, "discovery_cmd", None) == "scan":
        scan_path = Path(getattr(args, "path", ".")).expanduser()
        if not scan_path.exists():
            print(f"scan path does not exist: {scan_path}", file=sys.stderr)
            return cli_exit.EX_USAGE

        include_history = not bool(getattr(args, "no_history", False))
        try:
            scan = scan_repo(scan_path, include_history=include_history)
        except Exception as e:
            print(str(e), file=sys.stderr)
            return cli_exit.EX_ERR

        fmt = (getattr(args, "format", "json") or "json").strip().lower()
        if fmt == "text":
            findings = scan.get("findings") if isinstance(scan, dict) else None
            print(f"AI discovery: path={scan_path.resolve()}", file=sys.stderr)
            if isinstance(findings, list) and findings:
                print(f"findings: {len(findings)}", file=sys.stderr)
                for f in findings[:50]:
                    if not isinstance(f, dict):
                        continue
                    usage = f.get("detected_ai_usage")
                    file_path = f.get("file_path")
                    detector = f.get("detector_type")
                    conf = f.get("confidence")
                    print(f"- {usage} {file_path} detector={detector} confidence={conf}", file=sys.stderr)
            else:
                print("findings: 0", file=sys.stderr)
        else:
            _print_json({"ok": True, "scan": scan}, compact=args.compact_json)

        if not bool(getattr(args, "submit", False)):
            return cli_exit.EX_OK

        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required for submission: pass --run-id or set GOVAI_RUN_ID (or RUN_ID)", file=sys.stderr)
            return cli_exit.EX_USAGE

        # Backward-compatible fields used by Rust requirement derivation.
        scan_openai = bool(scan.get("openai")) if isinstance(scan, dict) else False
        scan_transformers = bool(scan.get("transformers")) if isinstance(scan, dict) else False
        scan_model_artifacts = bool(scan.get("model_artifacts")) if isinstance(scan, dict) else False
        findings = scan.get("findings") if isinstance(scan, dict) else []
        findings_list = findings if isinstance(findings, list) else []

        payload_obj = {
            "schema_version": "aigov.ai_discovery_reported.v2",
            "openai": scan_openai,
            "transformers": scan_transformers,
            "model_artifacts": scan_model_artifacts,
            "scanned_path": str(scan_path.resolve()),
            "findings": findings_list,
            "findings_count": len(findings_list),
        }

        event_id = (getattr(args, "event_id", None) or "").strip() or f"ai_discovery_reported_{run_id}"
        actor = (getattr(args, "actor", None) or "govai_cli").strip() or "govai_cli"
        system = (getattr(args, "system", None) or "govai_cli").strip() or "govai_cli"

        ev = {
            "event_id": event_id,
            "event_type": "ai_discovery_reported",
            "ts_utc": _utc_now_z(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": payload_obj,
        }

        try:
            client = GovAIClient(audit_url, api_key=api_key, default_project=project)
            out = submit_event(client, ev)
        except Exception as e:
            print(str(e), file=sys.stderr)
            return cli_exit.EX_ERR

        _print_json(out, compact=True)
        return cli_exit.EX_OK

    if args.cmd == "explain":
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID", file=sys.stderr)
            return cli_exit.EX_USAGE

        try:
            client = GovAIClient(audit_url, api_key=api_key, default_project=project)
            summary = get_compliance_summary(client, run_id, timeout=args.timeout)
        except Exception as e:
            print(str(e), file=sys.stderr)
            return cli_exit.EX_ERR

        if not isinstance(summary, dict):
            print("error: expected object from /compliance-summary", file=sys.stderr)
            return cli_exit.EX_ERR

        if summary.get("ok") is False:
            print(summary.get("message") or summary.get("error") or "error: /compliance-summary failed", file=sys.stderr)
            return cli_exit.EX_ERR

        verdict = summary.get("verdict")
        print(f"verdict: {verdict}")

        requirements = summary.get("requirements")
        if not isinstance(requirements, dict):
            current_state = summary.get("current_state")
            if isinstance(current_state, dict):
                requirements = current_state.get("requirements")

        if isinstance(requirements, dict):
            required = requirements.get("required") or []
            satisfied = requirements.get("satisfied") or []
            missing = requirements.get("missing") or []
            required_evidence = requirements.get("required_evidence") or []
            missing_evidence = requirements.get("missing_evidence") or []

            print("requirements:")
            print(f" required: {', '.join(map(str, required)) if required else '-'}")
            print(f" satisfied: {', '.join(map(str, satisfied)) if satisfied else '-'}")
            print(f" missing: {', '.join(map(str, missing)) if missing else '-'}")

            if required_evidence:
                print(" required_evidence:")
                for item in required_evidence:
                    if isinstance(item, dict):
                        print(f"  - {item.get('code')} ({item.get('source')})")
                    else:
                        print(f"  - {item}")

            if missing_evidence:
                print(" missing_evidence:")
                for item in missing_evidence:
                    if isinstance(item, dict):
                        print(f"  - {item.get('code')} ({item.get('source')})")
                    else:
                        print(f"  - {item}")

        blocked_reasons = summary.get("blocked_reasons") or []
        if blocked_reasons:
            print("blocked_reasons:")
            for reason in blocked_reasons:
                if isinstance(reason, dict):
                    code = reason.get("code")
                    message = reason.get("message")
                    print(f" - {code}: {message}")
                else:
                    print(f" - {reason}")

        return cli_exit.EX_OK

    if args.cmd == "report":
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID (or RUN_ID)", file=sys.stderr)
            return cli_exit.EX_USAGE
        prev = os.environ.get("RUN_ID")
        try:
            os.environ["RUN_ID"] = run_id
            report_mod.main()
        except SystemExit as se:
            return _system_exit_code(se)
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
            return cli_exit.EX_ERR
        finally:
            if prev is None:
                os.environ.pop("RUN_ID", None)
            else:
                os.environ["RUN_ID"] = prev
        return cli_exit.EX_OK

    if args.cmd == "export-bundle":
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID (or RUN_ID)", file=sys.stderr)
            return cli_exit.EX_USAGE
        try:
            export_bundle_mod.main(["govai", run_id])
        except SystemExit as se:
            return _system_exit_code(se)
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
            return cli_exit.EX_ERR
        return cli_exit.EX_OK

    if args.cmd == "export-run":
        run_id = _resolve_run_id(args)
        if not run_id:
            print("run id required: pass --run-id or set GOVAI_RUN_ID (or RUN_ID)", file=sys.stderr)
            return cli_exit.EX_USAGE
        try:
            client = GovAIClient(audit_url, api_key=api_key, default_project=project)
            out = export_run(client, run_id, project=getattr(args, "project", None))
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
            return cli_exit.EX_ERR
        _print_json(out, compact=True)
        return cli_exit.EX_OK

    if args.cmd == "sign-audit-export":
        try:
            sign_audit_export_ed25519(
                str(getattr(args, "in_path")),
                out_path=str(getattr(args, "out_path")),
                issuer_id=str(getattr(args, "issuer_id")),
                signer=str(getattr(args, "signer")),
                private_key_base64=str(getattr(args, "private_key_base64")),
                created_at_utc=str(getattr(args, "created_at_utc")),
                expires_at_utc=getattr(args, "expires_at_utc"),
            )
        except Exception as e:  # noqa: BLE001
            print(f"error: sign-audit-export failed: {e}", file=sys.stderr)
            return cli_exit.EX_ERR
        return cli_exit.EX_OK

    if args.cmd == "verify-audit-export":
        raw = str(getattr(args, "path", "") or "").strip()
        trust_raw = str(getattr(args, "trust_json", "") or "").strip()
        if not trust_raw:
            print(
                "error: --trust-json or AIGOV_POLICY_TRUST_ED25519_JSON required",
                file=sys.stderr,
            )
            return cli_exit.EX_USAGE
        try:
            doc = json.loads(Path(raw).read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError("audit export must be a JSON object")
            trust = load_trust_from_env_json(trust_raw)
            payload = verify_signed_audit_export(doc, trust=trust)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "run_id": payload.run_id,
                        "schema_version": payload.schema_version,
                        "decision_verdict": payload.decision_verdict,
                        "events_content_sha256": payload.events_content_sha256,
                        "bundle_sha256": payload.bundle_sha256,
                    },
                    indent=2,
                )
            )
        except Exception as e:  # noqa: BLE001
            print(f"error: verify-audit-export failed: {e}", file=sys.stderr)
            return cli_exit.EX_ERR
        return cli_exit.EX_OK

    if args.cmd == "replay-audit-export":
        from aigov_py.replay_audit_export import format_replay_report, replay_audit_export

        raw = str(getattr(args, "path", "") or "").strip()
        try:
            result = replay_audit_export(raw)
        except Exception as e:  # noqa: BLE001
            print(f"error: replay-audit-export failed: {e}", file=sys.stderr)
            return cli_exit.EX_ERR
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_replay_report(result))
        return cli_exit.EX_OK if result.get("ok") else cli_exit.EX_ERR

    if args.cmd == "lineage-graph":
        from aigov_py.lineage_graph import format_lineage_summary, lineage_graph_from_export

        raw = str(getattr(args, "path", "") or "").strip()
        try:
            if getattr(args, "mermaid", False):
                out = lineage_graph_from_export(raw, mermaid=True)
                print(out if isinstance(out, str) else str(out))
                return cli_exit.EX_OK
            doc = lineage_graph_from_export(raw)
        except Exception as e:  # noqa: BLE001
            print(f"error: lineage-graph failed: {e}", file=sys.stderr)
            return cli_exit.EX_ERR
        if getattr(args, "json", False):
            print(json.dumps(doc, indent=2, ensure_ascii=False))
        else:
            print(format_lineage_summary(doc))
        graph = doc.get("graph") if isinstance(doc, dict) else {}
        validation = (
            graph.get("lineage_validation") if isinstance(graph, dict) else {}
        ) or {}
        ok = not validation.get("errors") and not validation.get("delegation_cycle_detected")
        return cli_exit.EX_OK if ok else cli_exit.EX_ERR

    if args.cmd == "usage":
        try:
            client = GovAIClient(audit_url, api_key=api_key, default_project=project)
            out = get_usage(client, project=getattr(args, "project", None))
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
            return cli_exit.EX_ERR
        _print_json(out, compact=True)
        return cli_exit.EX_OK

    # Assessment API — same origin as audit service (Rust binary)
    client = GovaiClient(base_url=audit_url, api_key=api_key, timeout_sec=args.timeout)

    try:
        if args.cmd == "create-assessment":
            out = client.create_assessment(
                AssessmentCreate(
                    system_name=args.system_name,
                    intended_purpose=args.intended_purpose,
                    risk_class=args.risk_class,
                    team_id=args.team_id,
                    created_by=args.created_by,
                )
            )
            _print_json(out.__dict__, compact=args.compact_json)
            return cli_exit.EX_OK

    except GovaiError as e:
        payload = {"error": str(e), "status_code": e.status_code, "details": e.details}
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return cli_exit.EX_ERR

    return cli_exit.EX_ERR


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))