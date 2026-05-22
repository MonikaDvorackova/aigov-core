# Local demo contract (read-only vs fail-closed)

This document defines what **`make local-demo`** / **`scripts/run_local_demo.py`** prove, how that differs from **`make fail-closed-demo`**, and which environment variables apply.

## Read-only local demo (`make local-demo`)

**Purpose:** Probe the audit HTTP API on **loopback only** with **GET** requests. No evidence submission, no API keys, no ledger mutation.

**Scripts:** `scripts/run_local_demo.py`, optional `examples/local-demo/curl-health-ready.sh` via **`make local-demo-curl`**.

**Endpoints:** `GET /health`, `GET /ready`, `GET /status` (non-200 on `/status` may be informational).

**Exit codes (Python harness):**

| Code | Meaning |
|------|---------|
| `0` | `/health` and `/ready` returned HTTP **200** (service reachable and operationally ready). |
| `1` | Non-loopback URL, or service unreachable. |
| `2` | `/health` not 200, or `/ready` not 200 (service up but not ready). |

**Environment:**

- **`GOVAI_AUDIT_BASE_URL`** — default `http://127.0.0.1:8088`.

**What is *not* proven:** compliance verdicts, **`govai check`** exit semantics, **`BLOCKED` / `VALID`**, digest continuity, or fail-closed enforcement on incomplete evidence.

## Fail-closed demo (`make fail-closed-demo`)

**Purpose:** After **`GET /ready`** is **200**, run **`examples/blocked_deployment.sh`**, which posts minimal evidence and asserts **`govai check`** exits with code **3** (**`BLOCKED`**) for incomplete evidence. Confirms the same contract used in CI.

**Scripts:** `scripts/run_fail_closed_demo.py` (wrapper) + **`examples/blocked_deployment.sh`**.

**Prerequisites:** Running Postgres + audit service (e.g. **`docker compose up -d --build`**), **`python/.venv`** with **`govai`** installed (`pip install -e ".[dev]"` from **`python/`**).

**Environment:**

- **`GOVAI_AUDIT_BASE_URL`** — audit base URL (must match your stack; root **`docker-compose.yml`** defaults to `http://127.0.0.1:8088` from the host).
- **`GOVAI_API_KEY`** — bearer token accepted by the server (root compose commonly uses **`test-key`**).
- **`GOVAI_PROJECT`** — optional; default in the bash script is **`github-actions`**.

**Exit codes (wrapper):**

| Code | Meaning |
|------|---------|
| `0` | `/ready` was **200** and the blocked deployment script confirmed **`govai check`** exit **3** (BLOCKED). |
| `1` | Non-loopback URL, or missing **`GOVAI_API_KEY`**. |
| `2` | `/ready` not **200** (audit not ready — *not* a product failure if Docker is not running). |
| `3` | `/ready` ok but **`examples/blocked_deployment.sh`** did not confirm exit **3** (script exited non-zero). |

**Stdout:** one deterministic JSON line (sorted keys). **Stderr:** short progress lines.

**What is proven:** incomplete-evidence path yields **BLOCKED** with exit code **3** for **`govai check`**, consistent with CI expectations.

**What is *not* proven:** full golden-path **`VALID`** flow, hosted tenant isolation, billing, or production hardening.

## Relationship

| Concern | Use |
|--------|-----|
| “Is the audit process up and **ready**?” | **`make local-demo`** (read-only). |
| “Does **BLOCKED** / exit **3** work end-to-end locally?” | **`make fail-closed-demo`** (needs **`govai`** + keys + running stack). |
| “Do OSS files, links, and gates pass?” | **`make enterprise-readiness-check`** (includes **`make security-trust`** and **`make oss-diagnostics`** / **`make oss-diagnostics`**). |

## CI and automation

- **`make enterprise-readiness-check`** runs **`security-trust`**, **`trust-manifest`**, claim gates, and **`oss-diagnostics`**. **`oss-diagnostics`** re-validates strict doc links and compares **`docs/reports/`** to **`origin/staging`** when that ref exists (warnings if the ref or diff is missing; failure if multiple report files differ or the single diff is not an allowed report for the branch policy in use — allowed basenames include historical audit reports such as **`phase6-oss-developer-experience-completion.md`**, **`phase6-oss-ecosystem-completion-package.md`**, and **`phase8-enterprise-security-trust.md`**).

Canonical contributor setup remains **`docs/project/local_development.md`**.
