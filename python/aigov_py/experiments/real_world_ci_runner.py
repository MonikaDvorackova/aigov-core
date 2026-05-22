from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

import requests

from aigov_py.experiments import real_world_ci_injection as rwci_data

# Real execution only: no offline gate projection (see controlled_failure_injection package).
SCENARIOS: tuple[str, ...] = ("missing_evidence", "missing_approval", "broken_traceability")
EXPECTED_GOVAI_STATUS: dict[str, str] = {
    "missing_evidence": "BLOCKED",
    "missing_approval": "BLOCKED",
    "broken_traceability": "BLOCKED_OR_INVALID",
}

RWCI_CSV_FIELDNAMES: tuple[str, ...] = (
    "repo",
    "scenario",
    "baseline_type",
    "baseline_method",
    "native_ci_status",
    "govai_ci_status",
    "govai_status",
    "native_run_url",
    "govai_run_url",
    "native_log_path",
    "govai_log_path",
    "error",
)

WORKFLOW_NATIVE = "GovAI Native Baseline"
WORKFLOW_GOVAI = "GovAI Audit Injection"
WORKFLOW_TIMEOUT_SEC = 600
POLL_SEC = 15
MAX_RETRIES = 3

_GITHUB_CONCLUSION_MAP: dict[str, str] = {
    "success": "success",
    "failure": "failure",
    "cancelled": "cancelled",
    "timed_out": "timed_out",
    "neutral": "failure",
    "skipped": "cancelled",
    "action_required": "error",
    "stale": "error",
}


def _map_conclusion(raw: str | None) -> str:
    c = (raw or "").strip().lower()
    if c in _GITHUB_CONCLUSION_MAP:
        return _GITHUB_CONCLUSION_MAP[c]
    if not c:
        return "error"
    return "error"


def govai_pip_install_snippet() -> str:
    override = (os.environ.get("RWCI_GOVAI_PIP_SPEC") or "").strip()
    if override:
        return "python -m pip install --upgrade pip\npip install " + override
    git_sha = (os.environ.get("RWCI_AIGOV_GIT_COMMIT") or "").strip()
    if git_sha:
        url = (
            "git+https://github.com/MonikaDvorackova/aigov-compliance-engine.git"
            f"@{git_sha}#subdirectory=python"
        )
        return f'python -m pip install --upgrade pip\npip install "{url}"'
    return "python -m pip install --upgrade pip\npip install aigov-py==0.2.1"


def _require_env() -> None:
    missing: list[str] = []
    for name in ("GITHUB_TOKEN", "GOVAI_AUDIT_BASE_URL", "GOVAI_API_KEY"):
        if not (os.environ.get(name) or "").strip():
            missing.append(name)
    if missing:
        print(
            "FATAL: missing required environment variable(s): " + ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(2)


def _request_with_retry(
    method: str,
    url: str,
    *,
    session: requests.Session,
    **kwargs: Any,
) -> requests.Response:
    last: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            r = session.request(method, url, timeout=120, **kwargs)
            if r.status_code in (403, 429) and attempt < MAX_RETRIES - 1:
                time.sleep(2**attempt)
                continue
            return r
        except (requests.RequestException, OSError) as e:
            last = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(2**attempt)
    assert last is not None
    raise last


def _gh_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    return s


def _me(session: requests.Session) -> str:
    r = _request_with_retry("GET", "https://api.github.com/user", session=session)
    r.raise_for_status()
    login = r.json().get("login")
    if not isinstance(login, str) or not login:
        raise RuntimeError("GitHub /user missing login")
    return login


def _ensure_fork(
    session: requests.Session,
    *,
    owner: str,
    repo: str,
    me: str,
) -> str:
    target = f"{me}/{repo}"
    chk = _request_with_retry("GET", f"https://api.github.com/repos/{me}/{repo}", session=session)
    if chk.status_code == 200:
        return target

    r = _request_with_retry(
        "POST",
        f"https://api.github.com/repos/{owner}/{repo}/forks",
        session=session,
        json={},
    )
    if r.status_code not in (200, 201, 202):
        msg = r.text or ""
        if "already exists" in msg.lower():
            return target
        r.raise_for_status()

    deadline = time.time() + WORKFLOW_TIMEOUT_SEC
    while time.time() < deadline:
        cr = _request_with_retry("GET", f"https://api.github.com/repos/{me}/{repo}", session=session)
        if cr.status_code == 200:
            return target
        time.sleep(POLL_SEC)

    raise TimeoutError(f"fork did not become ready in time: {target}")


def _emit_script_source() -> str:
    path = Path(__file__).resolve().parent / "scripts" / "emit_scenario.py"
    return path.read_text(encoding="utf-8")


def _native_baseline_script_source() -> str:
    path = Path(__file__).resolve().parent / "scripts" / "native_baseline.py"
    return path.read_text(encoding="utf-8")


def native_workflow_yaml(scenario: str) -> str:
    if scenario not in SCENARIOS:
        raise ValueError(scenario)
    return f"""name: {WORKFLOW_NATIVE}

on:
  push:
    branches:
      - 'govai-ci-injection/**'

jobs:
  native-baseline:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      SCENARIO: {scenario}
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Native baseline (no GovAI / no audit API)
        shell: bash
        run: |
          set -euo pipefail
          python scripts/native_baseline.py
"""


def govai_audit_workflow_yaml(scenario: str) -> str:
    if scenario not in SCENARIOS:
        raise ValueError(scenario)
    gh_secret_url = "${{{{ secrets.GOVAI_AUDIT_BASE_URL }}}}"
    gh_secret_key = "${{{{ secrets.GOVAI_API_KEY }}}}"
    gh_env_check = "${{{{ env.GOVAI_CHECK_RUN_ID }}}}"
    gh_env_emit = "${{{{ env.GOVAI_EMIT_RUN_ID }}}}"
    gh_env_run = "${{{{ env.GOVAI_CHECK_RUN_ID }}}}"
    bash_pipestatus = "${PIPESTATUS[0]}"
    install_lines = ["set -euo pipefail", *govai_pip_install_snippet().splitlines()]
    pip_block = "\n".join("          " + ln for ln in install_lines)
    return f"""name: {WORKFLOW_GOVAI}

on:
  push:
    branches:
      - 'govai-ci-injection/**'

jobs:
  audit-test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      SCENARIO: {scenario}
      GOVAI_PROJECT: github-actions
      GOVAI_AUDIT_BASE_URL: {gh_secret_url}
      GOVAI_API_KEY: {gh_secret_key}
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install GovAI (pinned)
        run: |
{pip_block}

      - name: Configure run identifiers
        shell: bash
        run: |
          set -euo pipefail
          R="rwci-$GITHUB_RUN_ID-$GITHUB_RUN_NUMBER-$GITHUB_RUN_ATTEMPT-${{GITHUB_SHA:0:7}}"
          echo "GOVAI_CHECK_RUN_ID=$R" >> "$GITHUB_ENV"
          if [ "{scenario}" = "broken_traceability" ]; then
            echo "GOVAI_EMIT_RUN_ID=$R-emit" >> "$GITHUB_ENV"
          else
            echo "GOVAI_EMIT_RUN_ID=$R" >> "$GITHUB_ENV"
          fi

      - name: Emit evidence (scenario dependent)
        shell: bash
        env:
          GOVAI_AUDIT_BASE_URL: {gh_secret_url}
          GOVAI_API_KEY: {gh_secret_key}
          GOVAI_PROJECT: github-actions
          GOVAI_CHECK_RUN_ID: {gh_env_check}
          GOVAI_EMIT_RUN_ID: {gh_env_emit}
          SCENARIO: {scenario}
        run: |
          set -euo pipefail
          python scripts/emit_scenario.py --scenario "{scenario}"

      - name: Run GovAI check
        shell: bash
        env:
          GOVAI_AUDIT_BASE_URL: {gh_secret_url}
          GOVAI_API_KEY: {gh_secret_key}
          GOVAI_PROJECT: github-actions
          GOVAI_RUN_ID: {gh_env_run}
        run: |
          set +e
          set -o pipefail
          tmp="$(mktemp)"
          govai check --run-id "$GOVAI_RUN_ID" 2>&1 | tee "$tmp"
          ec={bash_pipestatus}
          set -e
          echo "RWCI_GOVAI_EXIT_CODE=$ec"
          if [ -f "$tmp" ]; then
            echo "RWCI_GOVAI_VERDICT_LINE=$(tail -n 1 "$tmp" | tr -d '\\r')"
          fi
          exit "$ec"
"""


def _git(
    cwd: Path,
    args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> None:
    p = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or "").strip()
        raise RuntimeError(f"git {' '.join(args)} failed ({p.returncode}): {msg}")


def _clone_push_injection(
    *,
    token: str,
    fork_full_name: str,
    scenario: str,
    default_branch: str,
) -> str:
    emit_body = _emit_script_source()
    native_body = _native_baseline_script_source()
    audit_yml = govai_audit_workflow_yaml(scenario)
    native_yml = native_workflow_yaml(scenario)
    branch = f"govai-ci-injection/{scenario}"

    url = f"https://x-access-token:{token}@github.com/{fork_full_name}.git"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _git(root, ["clone", "--depth", "1", "--branch", default_branch, url, "repo"])
        repo_dir = root / "repo"
        wf_dir = repo_dir / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        script_dir = repo_dir / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        (wf_dir / "govai-native-baseline.yml").write_text(native_yml, encoding="utf-8")
        (wf_dir / "govai-audit.yml").write_text(audit_yml, encoding="utf-8")
        (script_dir / "emit_scenario.py").write_text(emit_body, encoding="utf-8")
        (script_dir / "native_baseline.py").write_text(native_body, encoding="utf-8")

        _git(repo_dir, ["checkout", "-B", branch])
        _git(repo_dir, ["config", "user.email", "rwci-runner@local"])
        _git(repo_dir, ["config", "user.name", "GovAI RWCI Runner"])
        _git(
            repo_dir,
            [
                "add",
                ".github/workflows/govai-native-baseline.yml",
                ".github/workflows/govai-audit.yml",
                "scripts/emit_scenario.py",
                "scripts/native_baseline.py",
            ],
        )
        _git(repo_dir, ["commit", "-m", f"ci: GovAI native + audit injection ({scenario})"])

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        _git(repo_dir, ["push", "-u", "origin", branch, "--force"], env=env)

        cp = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            check=True,
            capture_output=True,
            text=True,
        )
        return cp.stdout.strip()


def _get_default_branch(session: requests.Session, full_name: str) -> str:
    r = _request_with_retry(
        "GET",
        f"https://api.github.com/repos/{full_name}",
        session=session,
    )
    r.raise_for_status()
    data = r.json()
    db = data.get("default_branch")
    if not isinstance(db, str):
        return "main"
    return db


def _wait_both_runs_complete(
    session: requests.Session,
    *,
    repo_full: str,
    head_sha: str,
    deadline: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    want = {WORKFLOW_NATIVE, WORKFLOW_GOVAI}
    done: dict[str, dict[str, Any]] = {}
    while time.time() < deadline:
        url = (
            f"https://api.github.com/repos/{repo_full}/actions/runs"
            f"?head_sha={head_sha}&per_page=30"
        )
        r = _request_with_retry("GET", url, session=session)
        if r.status_code == 404:
            time.sleep(POLL_SEC)
            continue
        r.raise_for_status()
        runs = r.json().get("workflow_runs")
        if not isinstance(runs, list):
            time.sleep(POLL_SEC)
            continue
        for run in runs:
            if str(run.get("head_sha") or "") != head_sha:
                continue
            name = str(run.get("name") or "")
            if name not in want:
                continue
            if str(run.get("status") or "") != "completed":
                continue
            done[name] = dict(run)

        if want <= done.keys():
            return done[WORKFLOW_NATIVE], done[WORKFLOW_GOVAI]

        time.sleep(POLL_SEC)

    raise TimeoutError(f"Timed out waiting for {want} runs at sha={head_sha}")


_VERDICT_LINE = re.compile(r"^(VALID|INVALID|BLOCKED)\s*$")
_BASELINE_METHOD = re.compile(r"^RWCI_BASELINE_METHOD=(\S+)\s*$")
_BASELINE_TYPE = re.compile(r"^RWCI_BASELINE_TYPE=(\S+)\s*$")
_GOVAI_EXIT = re.compile(r"^RWCI_GOVAI_EXIT_CODE=(\d+)\s*$")


def _parse_verdict_from_logs(log_text: str) -> str:
    verdict = ""
    for line in log_text.splitlines():
        if _VERDICT_LINE.match(line.strip()):
            verdict = line.strip()
    return verdict


def _parse_baseline_method_from_logs(log_text: str) -> str:
    for line in log_text.splitlines():
        m = _BASELINE_METHOD.match(line.strip())
        if m:
            return m.group(1)
    return ""


def _parse_baseline_type_from_logs(log_text: str) -> str:
    for line in log_text.splitlines():
        m = _BASELINE_TYPE.match(line.strip())
        if m:
            return m.group(1)
    return ""


_GOVAI_VERDICT_LINE_RE = re.compile(r"^RWCI_GOVAI_VERDICT_LINE=(.+)$", re.MULTILINE)


def _resolve_govai_verdict(log_text: str) -> tuple[str, str, str]:
    """Return (govai_status, parse_notes, govai_verdict_source).

    Verdict is parsed from captured CLI-related log text first (standalone verdict lines
    and RWCI_GOVAI_VERDICT_LINE from tee). RWCI_GOVAI_EXIT_CODE is used only as fallback.
    """
    v = _parse_verdict_from_logs(log_text)
    if v:
        return v, "", "stdout"

    tl = _GOVAI_VERDICT_LINE_RE.search(log_text)
    if tl:
        tail = tl.group(1).strip()
        if tail in {"VALID", "INVALID", "BLOCKED"}:
            return tail, "verdict_from_RWCI_GOVAI_VERDICT_LINE", "stdout"

    for line in log_text.splitlines():
        m = _GOVAI_EXIT.match(line.strip())
        if m:
            ec = int(m.group(1))
            if ec == 0:
                return "VALID", "verdict_inferred_from_RWCI_GOVAI_EXIT_CODE", "exit_code_fallback"
            if ec == 2:
                return "INVALID", "verdict_inferred_from_RWCI_GOVAI_EXIT_CODE", "exit_code_fallback"
            if ec == 3:
                return "BLOCKED", "verdict_inferred_from_RWCI_GOVAI_EXIT_CODE", "exit_code_fallback"
            return (
                "UNKNOWN",
                f"verdict_inferred_from_RWCI_GOVAI_EXIT_CODE_unmapped_ec={ec}",
                "exit_code_fallback",
            )

    return "UNKNOWN", "verdict_not_found_in_logs", "unknown"


METRIC_DEFINITIONS: dict[str, str] = {
    "native_false_acceptance_rate": (
        "Successful CI completion under injected auditability-failure conditions. "
        "Does not imply CI is expected to detect such failures."
    ),
    "govai_detection_rate": (
        "Fraction of injected failure scenarios classified as BLOCKED or INVALID "
        "by decision-level enforcement."
    ),
    "completed_rows": (
        "Rows where both native and GovAI workflows completed and produced parseable outputs."
    ),
}


def _verdict_source_counts(completed: list[dict[str, Any]]) -> dict[str, int]:
    out = {"stdout": 0, "exit_code_fallback": 0}
    for r in completed:
        src = str(r.get("govai_verdict_source") or "")
        if src in out:
            out[src] += 1
    return out


def _verdict_stdout_ratio(counts: dict[str, int]) -> float:
    s = counts.get("stdout", 0)
    f = counts.get("exit_code_fallback", 0)
    denom = s + f
    if denom == 0:
        return 1.0
    return s / denom


def _redact_log_excerpt(text: str) -> str:
    """Remove likely secrets from a log excerpt (best-effort)."""
    t = text
    t = re.sub(r"https://x-access-token:[^@\s]+@", "https://x-access-token:<redacted>@", t)
    t = re.sub(r"\bgh[pousr]_[A-Za-z0-9_]+\b", "gh_token_<redacted>", t)
    t = re.sub(r"(?i)bearer\s+[A-Za-z0-9._\-]+", "Bearer <redacted>", t)
    t = re.sub(
        r"(?i)(api[_-]?key|password|secret)\s*=\s*\S+",
        lambda m: f"{m.group(1)}=<redacted>",
        t,
    )
    return t


def _format_log_excerpt(log_text: str, *, max_lines: int = 20) -> str:
    """Build a ≤max_lines excerpt that includes a verdict token if present in the log."""
    lines = log_text.splitlines()
    verdict_idx = -1
    for i, line in enumerate(lines):
        if _VERDICT_LINE.match(line.strip()):
            verdict_idx = i
            break
        if re.search(r"\b(VALID|INVALID|BLOCKED)\b", line):
            verdict_idx = i
            break
    if verdict_idx < 0:
        chunk = lines[-max_lines:] if len(lines) > max_lines else lines
    else:
        half = max_lines // 2
        start = max(0, verdict_idx - half)
        end = min(len(lines), start + max_lines)
        if end - start < max_lines:
            start = max(0, end - max_lines)
        chunk = lines[start:end]
    excerpt = _redact_log_excerpt("\n".join(chunk))
    lines_out = excerpt.splitlines()
    if len(lines_out) > max_lines:
        excerpt = "\n".join(lines_out[-max_lines:])
    return excerpt


def _select_case_studies(
    rows: list[dict[str, Any]],
    out_base: Path,
    *,
    max_studies: int = 5,
) -> list[dict[str, Any]]:
    """Pick representative runs: native CI succeeded while GovAI blocked (paper contrast)."""
    candidates: list[dict[str, Any]] = []
    for r in rows:
        if r.get("error"):
            continue
        if str(r.get("baseline_type") or "") != "native_ci_detected":
            continue
        if str(r.get("native_ci_status") or "") != "success":
            continue
        g = str(r.get("govai_status") or "")
        if g not in {"BLOCKED", "INVALID"}:
            continue
        candidates.append(r)
    candidates.sort(key=lambda x: (str(x.get("repo") or ""), str(x.get("scenario") or "")))

    out: list[dict[str, Any]] = []
    for r in candidates:
        if len(out) >= max_studies:
            break
        rel = str(r.get("govai_log_path") or "")
        log_path = out_base / rel if rel else None
        log_text = ""
        if log_path and log_path.is_file():
            log_text = log_path.read_text(encoding="utf-8", errors="replace")[:500000]
        excerpt = _format_log_excerpt(log_text, max_lines=20)
        if not excerpt or not re.search(r"\b(VALID|INVALID|BLOCKED)\b", excerpt):
            continue
        out.append(
            {
                "repo": str(r.get("repo") or ""),
                "scenario": str(r.get("scenario") or ""),
                "native_ci_status": str(r.get("native_ci_status") or ""),
                "govai_status": str(r.get("govai_status") or ""),
                "log_excerpt": excerpt,
                "govai_run_url": str(r.get("govai_run_url") or ""),
            }
        )
    return out


def _write_paper_table_csv(out_base: Path, completed_native: list[dict[str, Any]]) -> Path:
    """Per-scenario rates on native_ci_detected completed rows only (two decimal places)."""
    path = out_base / "paper_table.csv"
    lines_out = ["scenario,native_success_rate,govai_detection_rate"]
    for scenario in SCENARIOS:
        rs = [r for r in completed_native if str(r.get("scenario")) == scenario]
        if not rs:
            lines_out.append(f"{scenario},0.00,0.00")
            continue
        n_ok = sum(1 for x in rs if str(x.get("native_ci_status")) == "success")
        g_det = sum(1 for x in rs if str(x.get("govai_status")) in {"BLOCKED", "INVALID"})
        nsr = round(n_ok / len(rs), 2)
        gdr = round(g_det / len(rs), 2)
        lines_out.append(f"{scenario},{nsr:.2f},{gdr:.2f}")
    path.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    return path


def _paper_consistency_errors(
    *,
    summary: dict[str, Any],
    case_studies: list[dict[str, Any]],
    native_only_completed: list[dict[str, Any]],
    verdict_counts: dict[str, int],
) -> list[str]:
    errs: list[str] = []
    if len(native_only_completed) < 10:
        errs.append(
            f"RWCI paper check: native_ci_detected completed rows ({len(native_only_completed)}) "
            f"must be >= 10 (full dataset run required for publication)."
        )
    if not case_studies:
        errs.append(
            "RWCI paper check: no case_studies produced "
            "(need native success + GovAI BLOCKED/INVALID with readable GovAI logs)."
        )
    det = float(summary.get("govai_detection_rate_native_ci_only") or 0.0)
    if det < 0.95:
        errs.append(
            f"RWCI paper check: govai_detection_rate_native_ci_only ({det:.4f}) must be >= 0.95."
        )
    ratio = _verdict_stdout_ratio(verdict_counts)
    if ratio < 0.80:
        errs.append(
            f"RWCI paper check: stdout verdict share ({ratio:.2%}) must be >= 80% "
            f"(counts={verdict_counts})."
        )
    return errs


def _enforce_paper_consistency(
    *,
    summary: dict[str, Any],
    case_studies: list[dict[str, Any]],
    native_only_completed: list[dict[str, Any]],
    verdict_counts: dict[str, int],
) -> None:
    if (os.environ.get("RWCI_SKIP_PAPER_CHECKS") or "").strip() in {"1", "true", "yes"}:
        return
    errs = _paper_consistency_errors(
        summary=summary,
        case_studies=case_studies,
        native_only_completed=native_only_completed,
        verdict_counts=verdict_counts,
    )
    for msg in errs:
        print(f"FATAL: {msg}", file=sys.stderr)
    if errs:
        sys.exit(3)


def _download_job_log(
    session: requests.Session,
    *,
    repo_full: str,
    jobs_url: str | None,
) -> str:
    if not jobs_url:
        return ""
    r = _request_with_retry("GET", jobs_url, session=session)
    if r.status_code != 200:
        return ""
    jobs_data = r.json()
    jobs_list = jobs_data.get("jobs") if isinstance(jobs_data, dict) else None
    if not isinstance(jobs_list, list) or not jobs_list:
        return ""
    job_id = jobs_list[0].get("id")
    if not isinstance(job_id, int):
        return ""
    log_url = f"https://api.github.com/repos/{repo_full}/actions/jobs/{job_id}/logs"
    lr = _request_with_retry("GET", log_url, session=session)
    if lr.status_code != 200:
        return ""
    return lr.text


def _download_run_logs_zip(session: requests.Session, logs_url: str) -> str:
    r = _request_with_retry("GET", logs_url, session=session)
    if r.status_code != 200:
        return ""
    buf = BytesIO(r.content)
    text_parts: list[str] = []
    try:
        with zipfile.ZipFile(buf) as zf:
            for name in zf.namelist():
                if name.endswith(".txt"):
                    text_parts.append(zf.read(name).decode("utf-8", errors="replace"))
    except zipfile.BadZipFile:
        return ""
    return "\n".join(text_parts)


def _fetch_run_logs(
    session: requests.Session,
    *,
    repo_full: str,
    run_obj: dict[str, Any],
) -> str:
    logs_combined = ""
    jobs_url = run_obj.get("jobs_url")
    if isinstance(jobs_url, str):
        logs_combined = _download_job_log(session, repo_full=repo_full, jobs_url=jobs_url)
    if not logs_combined:
        lz = run_obj.get("logs_url")
        if isinstance(lz, str):
            logs_combined = _download_run_logs_zip(session, lz)
    return logs_combined


def _safe_slug(repo_name: str, scenario: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", f"{repo_name}__{scenario}")
    return s.strip("_") or "run"


def _run_record(
    *,
    repo_name: str,
    scenario: str,
    workflow_display_name: str,
    head_sha: str,
    branch: str,
    run_obj: dict[str, Any],
) -> dict[str, Any]:
    rid = run_obj.get("id")
    return {
        "repo": repo_name,
        "scenario": scenario,
        "workflow_name": workflow_display_name,
        "run_id": str(rid) if rid is not None else "",
        "run_url": run_obj.get("html_url") or "",
        "conclusion": run_obj.get("conclusion") or "",
        "started_at": run_obj.get("run_started_at") or run_obj.get("created_at") or "",
        "completed_at": run_obj.get("updated_at") or "",
        "head_sha": run_obj.get("head_sha") or head_sha,
        "branch": branch,
    }


def run_experiment(
    *,
    output_dir: Path,
    limit: int,
    repo_filter: str | None = None,
    scenario_filter: str | None = None,
) -> dict[str, Any]:
    _require_env()
    token = os.environ["GITHUB_TOKEN"].strip()

    session = _gh_session(token)
    me = _me(session)

    all_repos = rwci_data.load_repos()
    if repo_filter:
        all_repos = [e for e in all_repos if str(e.get("name") or "") == repo_filter]
        if not all_repos:
            print(f"FATAL: --repo {repo_filter!r} not found in datasets/repos.json", file=sys.stderr)
            sys.exit(2)

    repos = all_repos[: max(1, limit)]

    scenarios_iter: tuple[str, ...]
    if scenario_filter:
        if scenario_filter not in SCENARIOS:
            print(
                f"FATAL: --scenario must be one of {list(SCENARIOS)}",
                file=sys.stderr,
            )
            sys.exit(2)
        scenarios_iter = (scenario_filter,)
    else:
        scenarios_iter = SCENARIOS

    rows_out: list[dict[str, Any]] = []
    out_base = output_dir.expanduser().resolve()
    art_native = out_base / "artifacts" / "native"
    art_govai = out_base / "artifacts" / "govai"
    art_native.mkdir(parents=True, exist_ok=True)
    art_govai.mkdir(parents=True, exist_ok=True)

    for entry in repos:
        name = str(entry.get("name") or "unknown")
        repo_url = str(entry.get("repo_url") or "")
        m = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url.strip())
        if not m:
            rows_out.append(_empty_row_dict(name, "", error="bad repo_url"))
            continue
        owner, repo = m.group(1), m.group(2).rstrip("/")

        try:
            fork_full = _ensure_fork(session, owner=owner, repo=repo, me=me)
            default_branch = _get_default_branch(session, fork_full)
        except Exception as e:
            rows_out.append(_empty_row_dict(name, "", error=str(e)))
            time.sleep(2)
            continue

        for scenario in scenarios_iter:
            branch = f"govai-ci-injection/{scenario}"
            row = _empty_row_dict(name, scenario)
            row["expected_govai_status"] = EXPECTED_GOVAI_STATUS.get(scenario, "")
            row["parse_notes"] = ""

            try:
                sha = _clone_push_injection(
                    token=token,
                    fork_full_name=fork_full,
                    scenario=scenario,
                    default_branch=default_branch,
                )
                deadline = time.time() + WORKFLOW_TIMEOUT_SEC
                native_run, govai_run = _wait_both_runs_complete(
                    session,
                    repo_full=fork_full,
                    head_sha=sha,
                    deadline=deadline,
                )

                row["native_ci_status"] = _map_conclusion(native_run.get("conclusion"))
                row["govai_ci_status"] = _map_conclusion(govai_run.get("conclusion"))

                native_logs = _fetch_run_logs(session, repo_full=fork_full, run_obj=native_run)
                govai_logs = _fetch_run_logs(session, repo_full=fork_full, run_obj=govai_run)

                bm = _parse_baseline_method_from_logs(native_logs)
                bt = _parse_baseline_type_from_logs(native_logs)
                row["baseline_method"] = bm or "unknown"
                row["baseline_type"] = bt or "unknown"

                gv, gnotes, gv_src = _resolve_govai_verdict(govai_logs)
                row["govai_status"] = gv
                row["govai_verdict_source"] = gv_src
                if gnotes:
                    row["parse_notes"] = gnotes

                slug = _safe_slug(name, scenario)
                native_log_rel = f"artifacts/native/{slug}.log.txt"
                govai_log_rel = f"artifacts/govai/{slug}.log.txt"
                row["native_log_path"] = native_log_rel
                row["govai_log_path"] = govai_log_rel

                nat_meta = _run_record(
                    repo_name=name,
                    scenario=scenario,
                    workflow_display_name=WORKFLOW_NATIVE,
                    head_sha=sha,
                    branch=branch,
                    run_obj=native_run,
                )
                gov_meta = _run_record(
                    repo_name=name,
                    scenario=scenario,
                    workflow_display_name=WORKFLOW_GOVAI,
                    head_sha=sha,
                    branch=branch,
                    run_obj=govai_run,
                )

                (art_native / f"{slug}.log.txt").write_text(native_logs[:500000], encoding="utf-8")
                (art_native / f"{slug}.run.json").write_text(
                    json.dumps(nat_meta, indent=2)[:200000],
                    encoding="utf-8",
                )
                (art_govai / f"{slug}.log.txt").write_text(govai_logs[:500000], encoding="utf-8")
                (art_govai / f"{slug}.run.json").write_text(
                    json.dumps(gov_meta, indent=2)[:200000],
                    encoding="utf-8",
                )

                nu = native_run.get("html_url")
                gu = govai_run.get("html_url")
                if isinstance(nu, str):
                    row["native_run_url"] = nu
                if isinstance(gu, str):
                    row["govai_run_url"] = gu

            except Exception as e:
                row["native_ci_status"] = "error"
                row["govai_ci_status"] = "error"
                row["govai_status"] = "UNKNOWN"
                row["govai_verdict_source"] = "unknown"
                row["error"] = str(e)

            rows_out.append(row)
            time.sleep(3)

    out_base.mkdir(parents=True, exist_ok=True)
    csv_path = out_base / "real_world_ci_injection.csv"
    json_path = out_base / "real_world_ci_injection.json"

    csv_rows = [_row_for_csv(r) for r in rows_out]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(RWCI_CSV_FIELDNAMES), extrasaction="ignore")
        w.writeheader()
        for rrow in csv_rows:
            w.writerow({k: rrow.get(k, "") for k in RWCI_CSV_FIELDNAMES})

    summary = _summarize(rows_out)
    completed_for_native = [
        r
        for r in rows_out
        if not r.get("error")
        and str(r.get("scenario") or "") in SCENARIOS
        and (r.get("native_ci_status") or "")
        and (r.get("govai_ci_status") or "")
    ]
    native_only_completed = [
        r for r in completed_for_native if str(r.get("baseline_type") or "") == "native_ci_detected"
    ]
    case_studies = _select_case_studies(rows_out, out_base)
    paper_path = _write_paper_table_csv(out_base, native_only_completed)
    vc = summary.get("verdict_source_counts") or {"stdout": 0, "exit_code_fallback": 0}
    if not isinstance(vc, dict):
        vc = {"stdout": 0, "exit_code_fallback": 0}
    _enforce_paper_consistency(
        summary=summary,
        case_studies=case_studies,
        native_only_completed=native_only_completed,
        verdict_counts={
            "stdout": int(vc.get("stdout", 0) or 0),
            "exit_code_fallback": int(vc.get("exit_code_fallback", 0) or 0),
        },
    )
    payload = {"runs": rows_out, "summary": summary, "case_studies": case_studies}
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "paper_table": str(paper_path),
        "artifacts_native": str(art_native),
        "artifacts_govai": str(art_govai),
    }


def _row_for_csv(r: dict[str, Any]) -> dict[str, str]:
    return {k: str(r.get(k, "") or "") for k in RWCI_CSV_FIELDNAMES}


def _empty_row_dict(repo: str, scenario: str, *, error: str = "") -> dict[str, Any]:
    return {
        "repo": repo,
        "scenario": scenario,
        "baseline_type": "",
        "baseline_method": "",
        "native_ci_status": "",
        "govai_ci_status": "",
        "govai_status": "",
        "native_run_url": "",
        "govai_run_url": "",
        "native_log_path": "",
        "govai_log_path": "",
        "error": error,
        "expected_govai_status": EXPECTED_GOVAI_STATUS.get(scenario, ""),
        "parse_notes": "",
        "govai_verdict_source": "",
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_rows = len(rows)

    completed: list[dict[str, Any]] = []
    for r in rows:
        if r.get("error"):
            continue
        if not r.get("scenario"):
            continue
        # Completed when both workflow conclusions mapped and scenario injected.
        if str(r.get("scenario")) not in SCENARIOS:
            continue
        nc = r.get("native_ci_status") or ""
        gc = r.get("govai_ci_status") or ""
        if nc and gc and nc != "" and gc != "":
            completed.append(r)

    def rate_native_ok(rs: list[dict[str, Any]]) -> float:
        if not rs:
            return 0.0
        return sum(1 for x in rs if x.get("native_ci_status") == "success") / len(rs)

    def rate_govai_detect(rs: list[dict[str, Any]]) -> float:
        if not rs:
            return 0.0
        return sum(
            1 for x in rs if str(x.get("govai_status")) in {"BLOCKED", "INVALID"}
        ) / len(rs)

    def count_native_ok(rs: list[dict[str, Any]]) -> int:
        return sum(1 for x in rs if x.get("native_ci_status") == "success")

    def count_govai_bi(rs: list[dict[str, Any]]) -> int:
        return sum(1 for x in rs if str(x.get("govai_status")) in {"BLOCKED", "INVALID"})

    native_only = [r for r in completed if r.get("baseline_type") == "native_ci_detected"]
    fallback_only = [r for r in completed if r.get("baseline_type") == "fallback_minimal"]

    bt_counts: dict[str, int] = {"native_ci_detected": 0, "fallback_minimal": 0, "unknown": 0}
    for r in completed:
        bt = str(r.get("baseline_type") or "unknown")
        if bt in bt_counts:
            bt_counts[bt] += 1
        else:
            bt_counts["unknown"] += 1

    scenario_counts: dict[str, int] = {}
    for s in SCENARIOS:
        scenario_counts[s] = sum(1 for r in completed if r.get("scenario") == s)

    n_done = len(completed)

    verdict_counts = _verdict_source_counts(completed)
    ratio_vs = _verdict_stdout_ratio(verdict_counts)
    warnings: list[str] = []
    denom_vs = verdict_counts.get("stdout", 0) + verdict_counts.get("exit_code_fallback", 0)
    if denom_vs > 0 and ratio_vs <= 0.90:
        warnings.append(
            "govai_verdict_source: stdout share "
            f"{ratio_vs:.2%} is at or below the 90% recommended threshold "
            f"(counts={verdict_counts})."
        )

    return {
        "total_rows": total_rows,
        "completed_rows": n_done,
        "native_false_acceptance_rate_all": rate_native_ok(completed),
        "native_false_acceptance_rate_native_ci_only": rate_native_ok(native_only),
        "native_false_acceptance_rate_fallback_only": rate_native_ok(fallback_only),
        "govai_detection_rate_all": rate_govai_detect(completed),
        "govai_detection_rate_native_ci_only": rate_govai_detect(native_only),
        "govai_detection_rate_fallback_only": rate_govai_detect(fallback_only),
        "native_success_count_all": count_native_ok(completed),
        "native_success_count_native_ci_only": count_native_ok(native_only),
        "native_success_count_fallback_only": count_native_ok(fallback_only),
        "govai_blocked_invalid_count_all": count_govai_bi(completed),
        "govai_blocked_invalid_count_native_ci_only": count_govai_bi(native_only),
        "govai_blocked_invalid_count_fallback_only": count_govai_bi(fallback_only),
        "baseline_type_counts": bt_counts,
        "scenario_counts": scenario_counts,
        "metric_definitions": dict(METRIC_DEFINITIONS),
        "verdict_source_counts": verdict_counts,
        "verdict_source_stdout_ratio": ratio_vs,
        "warnings": warnings,
    }


def main_cli(
    *,
    output: Path,
    limit: int,
    repo: str | None = None,
    scenario: str | None = None,
) -> int:
    paths = run_experiment(
        output_dir=output,
        limit=limit,
        repo_filter=repo.strip() if repo else None,
        scenario_filter=scenario.strip() if scenario else None,
    )
    print("Wrote:")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    return 0


_workflow_yaml = govai_audit_workflow_yaml
