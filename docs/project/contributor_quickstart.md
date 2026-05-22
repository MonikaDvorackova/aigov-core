# Contributor Quickstart

This guide helps new contributors make their first GovAI contribution. For the **canonical** machine-oriented setup (venv location, Compose, gates, tests), prefer **[`local_development.md`](local_development.md)** — this page stays aligned with that flow.

**Documentation changes:** Canonical Markdown lives under `docs/`. The dashboard serves a curated subset at `/docs` and `/help` via `dashboard/lib/publicSite/publicDocsRegistry.ts` — add or update registry entries when introducing reader-facing pages.

## 1. Fork and clone

Fork the repository on GitHub, then clone your fork.

```bash
git clone https://github.com/<your-username>/aigov-compliance-engine.git
cd aigov-compliance-engine
```

## 2. Create a feature branch

Do not work directly on `main` or `staging`.

```bash
git fetch origin
git switch -c feat/my-contribution origin/staging
```

Open pull requests **to `staging`** for normal work. See **[`contributor_workflow.md`](contributor_workflow.md)** and **[`GOVERNANCE.md`](../../GOVERNANCE.md)**.

## 3. Install Python tooling (canonical layout)

The CLI and tests live under **`python/`**. Create the venv **inside** `python/` (matches `Makefile` targets):

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
cd ..
```

## 4. Run tests

With **`python/.venv`** activated:

```bash
cd python
python -m pytest
cd ..
```

Rust workspace:

```bash
cargo test --manifest-path rust/Cargo.toml
```

## 5. Documentation report gate (repository root)

Uses system **`python3`** (same as CI helpers):

```bash
python3 scripts/gate_reports.py
make gate
```

## 5b. OSS diagnostics and OSS diagnostics gate

From the repository root (system **`python3`**, no venv required for these scripts):

```bash
make oss-diagnostics   # one JSON line: layout, file checks, strict links, docs/reports vs origin/staging
make oss-diagnostics      # includes oss-diagnostics, repo health, metrics, strict doc links, then make gate
make enterprise-readiness-check      # security-trust documentation bundle check, then oss-diagnostics (matches OSS CI)
```

**`make local-demo`** is read-only (no keys, no evidence). **`make fail-closed-demo`** proves the BLOCKED / exit-code-3 contract when the audit stack is running — see **`examples/local-demo/CONTRACT.md`**. CI also publishes **`repo-health.json`**, **`docs-links.json`**, and **`oss-diagnostics.json`** (workflow **`oss-developer-experience`**).

## 6. Pick an issue

Good first contribution areas:

- documentation improvements
- examples
- architecture diagrams
- GitHub Actions examples
- local development setup

Look for issues labeled: **good first issue**, **help wanted**, **documentation**, **examples**.

## 7. Make a focused change

Keep the first PR small and reviewable when possible.

## 8. Open a pull request

Your PR should include:

- summary of the change
- linked issue when possible
- validation steps
- screenshots or logs if relevant
- documentation updates if needed

## 9. Governance-sensitive changes

If your change affects enforcement behavior, audit evidence, tenant isolation, approvals, or policy evaluation, explain the governance impact clearly.

GovAI prioritizes:

- deterministic behavior
- fail-closed enforcement
- auditability
- traceability
- evidence continuity
