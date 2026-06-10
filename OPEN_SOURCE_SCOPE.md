# GovAI Core open-source scope

This repository **is** [GovAI Core](https://github.com/MonikaDvorackova/govai-core): the ledger-authoritative audit runtime, portable contracts, integrator SDKs, and offline validation tooling.

The **GovAI Platform** (hosted SaaS, billing, dashboard, enterprise control plane) is a **separate product** and is not implemented by the `aigov_audit` HTTP surface in this tree.

Canonical terminology: [docs/terminology.md](docs/terminology.md). Architecture boundary: [docs/architecture/platform-vs-core-boundary.md](docs/architecture/platform-vs-core-boundary.md).

## License

See [LICENSE](LICENSE) for terms governing this repository.

## Included in GovAI Core (this repository)

| Area | Examples |
|------|----------|
| Audit runtime | `rust/` — `aigov_audit` binary, core HTTP routes |
| Evidence & ledger | Append-only ingest, tenant-scoped JSONL, chain verify |
| Compliance reads | `GET /compliance-summary`, `GET /api/export/{run_id}` |
| Readiness | Non-mutating `GET /ready` (no ledger append probes) |
| Python integrators | `python/aigov_py/` — CLI, runtime SDK, standards validators |
| Contracts | `api/govai-http-v1.openapi.yaml` (core routes tagged `x-govai-runtime-mount: aigov_audit`) |
| Examples | `examples/basic-runtime-client/`, `examples/python-runtime-client/` |
| CI | `govai-ci.yml`, portable digest smoke, `make core-runtime-examples-check` |

## Excluded from GovAI Core (platform-only)

These may appear in documentation or directories for **reference** but are **not** mounted on `aigov_audit`:

| Area | Examples in tree (platform reference) |
|------|----------------------------------------|
| Hosted SaaS | `hosted/`, `docs/hosted/` |
| Billing & metering | Stripe, `docs/billing.md` |
| Onboarding & tenant console | `docs/customer-onboarding-10min.md`, dashboard flows |
| Enterprise control plane | JWT `/api/me`, `/api/compliance-workflow*`, `/api/functions/v2/*` |
| Dashboard & commercial site | `dashboard/` |
| Commercial ops | `docs/commercial/`, `docs/pricing/` |

## Contributor invariants (must not weaken)

Contributors must preserve:

- **Append-only** ledger semantics (no silent rewrite of committed evidence)
- **Tenant isolation** via `GOVAI_API_KEYS` + `GOVAI_API_KEYS_JSON` (fail-closed when allowlist is set)
- **Deterministic reconstruction** (bundle, export, digest stability)
- **Non-mutating readiness** (`GET /ready` must not append evidence)
- **Ledger-authoritative verdicts** on `GET /compliance-summary` (no trace/Postgres override)
- **Reproducible audit exports** (`aigov.audit_export.v1` schema conformance)

## Semantic layers inside the tree

1. **Core runtime** — regulation-agnostic ledger and compliance summary (authoritative for integrators).
2. **Portable standards** — offline JSON validators and digests (`python/aigov_py/standards/`).
3. **Platform reference docs** — historical hosted/enterprise narrative; label as outside core.

## Integrator surfaces

| Surface | Where | Notes |
|---------|-------|-------|
| `aigov_audit` HTTP API | This repo | Core routes only |
| Python (`aigov-py`) | This repo | CLI + `RuntimeGovernanceClient` |
| TypeScript SDK | Published from core releases when available | See `packages/` / docs |
| GovAI Platform | Separate product / repository | Proprietary hosted APIs |

## Out of scope (product claims)

- No legal or regulatory certification from software alone.
- No promise that documentation satisfies EU AI Act or other obligations without your organization's process.
