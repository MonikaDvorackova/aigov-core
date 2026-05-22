# Phase 6 OSS developer experience (gap fill)

This note summarizes the **Phase 6 OSS developer experience** work on this branch: contributor hygiene, copy-paste onboarding, examples, and architecture links — **without** changing product runtime behavior.

## What was already in place before this pass

- Contributor guides (`CONTRIBUTING.md`, `docs/project/contributor_quickstart.md`, maintainer docs).
- Security policy (`SECURITY.md`), PR template, branch workflow docs.
- Rich Markdown documentation under `docs/` (quickstarts, architecture, GitHub Action reference).
- Local Docker Compose and Makefile targets for audit and gates.
- Strict audit report heading gate (`scripts/gate_reports.py`, `make gate`).

## What this branch adds (incremental)

### Initial gap fill

- Root **`CODE_OF_CONDUCT.md`**.
- **`.env.example`** with safe placeholders and comments (no secrets).
- GitHub **issue templates** (`feature_request`, `question`) and **`config.yml`** security contact link.
- **`examples/ci/govai-check.yml`** — downstream workflow example (not under `.github/workflows/` here).
- Earlier compliance report (archived narrative): **`docs/reports/repo-debt-audit-and-cleanup.md`** — superseded for OSS Phase 6 completion by **`docs/reports/repo-debt-audit-and-cleanup.md`**.

### Expanded Phase 6 (documentation only)

- **`docs/project/local_development.md`** — clone, `python/.venv`, `pip install -e ".[dev]"`, Docker Compose, `/health` and `/ready`, `make gate`, `cargo test`, `pytest` / missing-deps note.
- **`examples/README.md`** plus **`examples/ci/README.md`**, **`examples/runtime-evaluate/`** (minimal JSON + curl), **`examples/evidence-pack/README.md`** — all marked **non-production**, no secrets.
- **`docs/architecture/developer_onboarding_flow.md`** — Mermaid overview linking runtime evaluate, evidence pack, CI gate, ledger, hosted URL.
- **`docs/project/contributor_workflow.md`** — branch flow, report rules, one-report-per-PR expectation, validation commands, **advisory-only** runtime controls.

### OSS tooling (stdlib scripts + Makefile)

- **`scripts/repo_health_check.py`** — required OSS file presence; **`make oss-health`**.
- **`scripts/oss_metrics.py`** — counts for docs, reports, examples, templates, tests; **`--json`** optional; **`make oss-metrics`**.
- **`scripts/validate_docs_links.py`** — local relative links in `README.md` and `docs/**/*.md`; default **warn / exit 0**, **`--strict`** exits 1; **`make docs-links`** / **`make docs-links-strict`**.
- **`make oss-diagnostics`** — runs **`oss-health`**, **`oss-metrics`**, **`docs-links-strict`**, then **`gate`** (does **not** require a running audit service). Enforced in CI via **`.github/workflows/oss-developer-experience.yml`**.

### Runnable local demo harness (read-only)

- **`scripts/run_local_demo.py`** — stdlib-only **`GET /health`**, **`/ready`**, **`/status`** against **`GOVAI_AUDIT_BASE_URL`** (default **`http://127.0.0.1:8088`**), loopback-only; **no** API keys, **no** evidence POST, **no** ledger mutation.
- **`make local-demo`** / **`make local-demo-curl`** — Makefile wrappers; **`examples/local-demo/`** documents expected output and troubleshooting.

### Public docs (dashboard)

- Reader **`/docs`** and **`/help`** on **govbase.dev** are implemented in **`dashboard/`** and read canonical Markdown from **`docs/`** (see **`docs/project/local_development.md`** for preview commands).

## Explicit non-goals

- No runtime enforcement changes.
- No database migrations.
- No ledger semantics or storage changes.
- No tenant identity derivation changes.
- No `GET /compliance-summary` contract or behavior changes.
- No `VALID` / `INVALID` / `BLOCKED` verdict semantics changes.
- **Update (Phase 6 completion):** OSS checks run from **`.github/workflows/oss-developer-experience.yml`**; other product gates remain unchanged. Historical “no workflow edits” applied only to the original gap-fill slice.
- No wholesale **migration** of the **`docs/`** corpus out of GitHub—production reader UI consumes the same tree.
