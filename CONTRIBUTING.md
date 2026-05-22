# Contributing to GovAI

Thank you for contributing to GovAI.

**Repository license:** this **platform repository** is **proprietary** ([LICENSE](LICENSE)). Contributions are accepted under maintainer process and do not grant redistribution rights unless agreed in writing. **Open-core runtime** contributions belong in **[govai-core](https://github.com/govbase-dev/govai-core)**.

GovAI is an evidence-first governance layer for AI systems focused on:
- decision-level auditability
- fail-closed enforcement
- evidence continuity
- operational governance enforcement
- deterministic compliance evaluation

We welcome contributions across:
- Rust services
- Python SDKs
- CI/CD integrations
- governance workflows
- documentation
- examples
- architecture diagrams
- deployment tooling

## Community standards

Contributors are expected to follow **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** in all project spaces. Maintainer model, branch flow, and escalation paths: **[GOVERNANCE.md](GOVERNANCE.md)**.

**Contributor funnel** (first visit through first merged PR) and **issue triage** expectations: **[docs/community/contributor-funnel.md](docs/community/contributor-funnel.md)**, **[docs/community/issue-triage.md](docs/community/issue-triage.md)**.

## Local configuration (optional)

Some `Makefile` targets optionally load a root **`.env`** file. Use **`.env.example`** as a template of safe placeholders; never commit real secrets. See also **`SECURITY.md`** for vulnerability reporting (private channels, not public issues).

**Step-by-step local setup** (venv in `python/`, Docker Compose, `make gate`, `cargo test`, `python -m pytest`): **[docs/project/local_development.md](docs/project/local_development.md)**.

**Read-only local audit check** (optional; needs Docker or `make audit_bg` first): **`make local-demo`** or **`make local-demo-curl`** — no secrets, no evidence submission.

**Public docs:** **Canonical** documentation lives under **`docs/`**. The **`dashboard/`** app renders it on **`/docs`** and **`/help`** for **[govbase.dev](https://govbase.dev)**; edit Markdown in `docs/` and run `cd dashboard && npm run dev` to preview.

## Development workflow

End-to-end branch policy, report rules, and validation commands: **[docs/project/contributor_workflow.md](docs/project/contributor_workflow.md)**.

### Branching model

Do not push directly to main.

Recommended workflow:

feature branch -> staging -> main

All production-facing changes should flow through:
1. feature branch
2. staging
3. main

### Pull requests

PRs should:
- link to an issue when possible
- include a clear summary
- explain verification steps
- explain operational impact
- include documentation updates where appropriate

For governance-critical changes, explain:
- enforcement behavior
- fail-closed implications
- auditability impact
- evidence continuity implications

## Required reports for core changes

Core governance changes may require an audit report under docs/reports/.

Some CI workflows validate:
- report presence
- required report headings
- single run_id consistency

Typical required headings include:
- Evaluation gate
- Human approval gate

## Testing expectations

Contributors should validate changes locally whenever possible.

Typical validation includes:
- pytest
- cargo test
- cargo check
- local audit startup
- evidence verification flow
- readiness endpoint validation

## Operational principles

GovAI uses fail-closed semantics.

Decision states:
- VALID
- INVALID
- BLOCKED

Missing evidence or approvals should not silently pass.

Operational correctness is prioritized over permissive behavior.

## Readiness and health semantics

/health is liveness only.

/ready is the authoritative operational readiness endpoint.

Production systems should rely on /ready.

## Tenant isolation

Tenant isolation is derived from API key mapping.

X-GovAI-Project must not be treated as a security isolation boundary.

## Persistence expectations

Production ledger storage must be durable.

Ephemeral storage such as /tmp is discouraged for production environments.

## Releases and changelog

- Read **`docs/releases/`** for versioning, compatibility, deprecation, security releases, and cadence — start with **[docs/releases/versioning-policy.md](docs/releases/versioning-policy.md)**.
- User-visible changes should include a bullet under **`[Unreleased]`** in **[CHANGELOG.md](CHANGELOG.md)** when maintainers request it during review (semantic intent: **[docs/releases/versioning-policy.md](docs/releases/versioning-policy.md)**).
- Maintainers cut releases using **[docs/releases/release-checklist.md](docs/releases/release-checklist.md)** and **[docs/releases/release-runbook.md](docs/releases/release-runbook.md)**. Machine-readable scope: **[docs/releases/release-manifest.json](docs/releases/release-manifest.json)** (`python3 scripts/validate_release_manifest.py --json`). Run **`make release-operations-check`** for the full static gate; **`make release-readiness-check`** runs **`release-operations-check`**, **`release-manifest`**, **`validate-changelog`**, **`release-readiness-report`**, **`docs-links-strict`**, and **`make gate`**. Example shell drivers: **`examples/releases/README.md`**.

## Documentation contributions

High quality documentation contributions are encouraged.

Especially valuable:
- architecture diagrams
- deployment examples
- CI examples
- governance workflows
- policy examples
- operational troubleshooting

## Release notes: runtime governance enforcement (Phase 3 final)

Operators should be aware of **`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT=off|shadow|enforced`** (default **`off`**) and the tenant allowlist (**`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT_TENANTS`**) before promoting anything to production.

- **Default off:** Legacy **`GOVAI_RUNTIME_EVALUATE`** preview verdicts stay authoritative; HTTP/ledger **`enforcement`** now emits **`off`** instead of legacy **`none`**.
- **Shadow:** Emits **`governance_summary`** telemetry (including optional **`risk_class`**, default **`LIMITED`**) without rewriting runtime verdicts.
- **Enforced:** Optional hard gate for **`HIGH`**-risk missing lineage and unknown reason-code sentinel handling, only for tenants named in the comma-separated allowlist. Tenants outside the list keep non-blocking **`shadow`** response hints.
- **Overrides:** Sending **`override_ref`** still does **not** constitute approval and **cannot** downgrade **`BLOCKED`/`INVALID`** to **`VALID`** in this release.

## Security

Please avoid publicly disclosing unpatched vulnerabilities.

Security related reports should follow the guidance in SECURITY.md.

## Contributor philosophy

GovAI is designed as governance infrastructure rather than a model benchmarking framework.

Contributions should prioritize:
- determinism
- auditability
- traceability
- operational clarity
- enforcement correctness
