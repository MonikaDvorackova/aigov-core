# First contribution guide

Welcome. GovAI merges **evidence-first** discipline into contributor mechanics: CI documentation gates, branch policy, and explicit review for anything touching verdicts, enforcement, or tenant isolation.

## Set up the repository

1. **Fork and clone** (or clone with write access if you are a maintainer).

2. **Branch from `staging`** (not `main`):

```bash
git fetch origin
git switch staging
git pull --ff-only origin staging
git switch -c your-handle/short-topic
```

3. **Python environment** (for CLI, tests, gates):

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ..
```

4. **Local audit service (optional)** for integration checks: see [local development](../project/local_development.md) and `docker compose up -d --build`.

Canonical quickstart pointers: [contributor quickstart](../project/contributor_quickstart.md), [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Run checks (before opening a PR)

From repository root (with `python/.venv` activated when running pytest):

```bash
make oss-diagnostics          # oss-health + oss-metrics + docs-links + gate
python3 scripts/gate_reports.py
make cursor-plugin-check    # if you touched .cursor-plugin/
python3 scripts/validate_docs_links.py
```

Rust and Python tests (adjust paths if your CI differs):

```bash
cargo test --manifest-path rust/Cargo.toml
cd python && pytest && cd ..
```

If your change is **documentation-only**, still run **`make gate`**—audit reports under `docs/reports/` must retain required headings (see [contributor workflow](../project/contributor_workflow.md)).

## Pick an issue

- Use GitHub labels: **`good first issue`**, **`help wanted`**, **`documentation`**, **`examples`**.
- Read [good first issues](good-first-issues.md) for curated themes.
- Comment on the issue to avoid duplicate work; link the issue in your PR.

## Prepare a pull request

1. Use the repository **[pull request template](../../.github/pull_request_template.md)**.
2. Open PRs **to `staging`** for normal work—see [feature branch → staging → main policy](#feature-branch-to-staging-to-main-policy) below.
3. If you touch **enforcement**, **evidence formats**, **tenant isolation**, or **verdict semantics**, call it out explicitly in the PR description and expect stricter review.
4. **Core-affecting** PRs may require **exactly one** `docs/reports/<name>.md` change per policy—see contributor workflow.

## Governance-specific contribution rules

- **Authoritative verdict** remains **`GET /compliance-summary`**. Do not document advisory overlays (for example runtime evaluate summaries) as replacing that contract.
- **Do not weaken CI governance gates** (for example removing compliance workflows or bypassing digest/export requirements in documentation that operators treat as normative).
- **Advisory vs enforced** runtime paths: follow [runtime integration](../governance/runtime_integration.md); do not imply shadow mode changes promotion eligibility unless product docs explicitly say so.
- **Secrets:** never commit API keys; use `.env.example` patterns from [local development](../project/local_development.md).

## Feature branch → staging → main policy

| Step | Branch | Who |
| --- | --- | --- |
| Daily work | `your-handle/topic` from up-to-date `staging` | Contributor |
| Integration | PR **into `staging`** | Maintainer review |
| Release promotion | PR **`staging` → `main`** | Maintainers only |

**Do not** push directly to `main` or `staging`. **Do not** open contributor PRs **from** `main`.

Extended detail: [contributor workflow](../project/contributor_workflow.md), [contributor branch workflow](../contributor-branch-workflow.md) if present.

## Where next

- [Contributor pathways](contributor-pathways.md)
- [Good first issues](good-first-issues.md)
- [Roadmap](../project/roadmap.md)
