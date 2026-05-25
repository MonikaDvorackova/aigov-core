# Contributing to GovAI Core

Thank you for contributing to **GovAI Core** — the open-source, ledger-authoritative audit runtime for reconstructible AI governance.

## What GovAI Core is

GovAI Core provides:

- Append-only evidence ingest (`POST /evidence`)
- Ledger integrity verification (`GET /verify`)
- Deterministic compliance summary (`GET /compliance-summary`)
- Audit export (`GET /api/export/{run_id}`)
- Runtime examples and SDK-facing HTTP contracts
- Portable governance standards validators (offline)

## What GovAI Core is not

Do not add to this repository:

- Hosted SaaS control planes
- Stripe or billing flows
- Pricing or commercial onboarding
- Dashboard access control
- Managed tenant provisioning beyond env/DB key maps documented for core

Platform-only features belong in the **GovAI Platform** product, not in `aigov_audit`.

## Technical invariants (do not weaken)

| Invariant | Requirement |
|-----------|-------------|
| Append-only ledger | Evidence files are append-only; duplicate `event_id` rejected deterministically |
| Tenant isolation | Ledger tenant from API key mapping only; `X-GovAI-Project` is metadata only |
| Deterministic reconstruction | Bundle/export hashes stable for the same ledger contents |
| Non-mutating readiness | `GET /ready` must not append evidence or grow chains |
| Ledger-authoritative verdict | `GET /compliance-summary` derives from ledger projection, not Postgres traces |
| Fail-closed API keys | When `GOVAI_API_KEYS` is set, `GOVAI_API_KEYS_JSON` is required; no implicit shared `"default"` tenant for unknown keys |
| Reproducible export | `aigov.audit_export.v1` matches `docs/schemas/aigov.audit_export.v1.schema.json` |

## Community standards

Follow **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)**. Maintainer model: **[GOVERNANCE.md](GOVERNANCE.md)**.

**Local setup:** [docs/project/local_development.md](docs/project/local_development.md) · **Runtime quickstart:** [docs/quickstart-runtime.md](docs/quickstart-runtime.md)

## Development workflow

See **[docs/project/contributor_workflow.md](docs/project/contributor_workflow.md)**.

### Branching

`feature branch` → `staging` → `main`

Do not push directly to `main`.

### Pull requests

Include:

- Clear summary and verification steps
- Documentation updates for API or operator-visible behaviour
- For governance-critical changes: enforcement, tenant isolation, readiness, or export semantics

### Audit reports

Core governance changes may require **`docs/reports/*.md`** with headings:

- `## Evaluation gate`
- `## Human approval gate`

Validated by **`make gate`**.

## Testing expectations

```bash
cd rust && cargo build --locked --bin aigov_audit && cargo test --locked
cd python && python -m pytest
make gate
make core-runtime-examples-check
```

Operator smoke (server running):

```bash
./examples/basic-runtime-client/smoke-runtime.sh
python3 examples/python-runtime-client/run_runtime_smoke.py
```

## Tenant isolation

Configure both:

- `GOVAI_API_KEYS` — bearer allowlist
- `GOVAI_API_KEYS_JSON` — `{"<api_key>": "<ledger_tenant_id>"}`

## Security

Do not disclose unpatched vulnerabilities publicly. See **[SECURITY.md](SECURITY.md)**.

## Philosophy

Contributions should prioritize determinism, auditability, traceability, and enforcement correctness over permissive shortcuts.
