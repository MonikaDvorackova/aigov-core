# Roadmap

Public-facing plan for GovAI / GovBase. **Shipped** items exist in this repository today. **In progress** items have partial implementation or active PR streams. **Planned** items are directionally committed but not yet productized—timelines shift with pilot feedback.

```docs
preset: roadmap-board
```

## Current production surface (shipped)

- **Audit ledger HTTP API** — Evidence append (`POST /evidence`), bundle and bundle-hash reads, **`GET /compliance-summary`** verdict projection (`VALID` / `INVALID` / `BLOCKED`), stable **`GET /api/export/:run_id`**, usage metering hooks, operational `/health`, `/status`, `/ready`. See [`api/govai-http-v1.openapi.yaml`](../api/govai-http-v1.openapi.yaml).
- **`govai` CLI** — Check, evidence-pack init/submit, verify-evidence-pack, export, report, preflight, and supporting tooling (`python/aigov_py/cli.py`).
- **GitHub Actions composite gate** — Artefact-bound `submit-evidence-pack` + `verify-evidence-pack` with export cross-check default on ([`github-action.md`](github-action.md)).
- **Stripe billing routes** — Checkout, status, portal, invoices, reconciliation, usage reporting (when operator enables Stripe). See [`billing.md`](billing.md).
- **Reader documentation on govbase.dev** — Dashboard serves `/docs` and `/help` from canonical Markdown under `docs/` (no separate Mintlify production host in this path).

## Near-term documentation and onboarding (in progress / tightening)

- Expand worked examples linking **local quickstart**, **hosted onboarding**, and **CI gate** with a single narrative.
- Keep **OpenAPI** and **ARCHITECTURE** tables aligned when routes evolve.
- Operator checklists for **readiness probes** and **digest gates** ([`hosted-backend-deployment.md`](hosted-backend-deployment.md), [`github-action.md`](github-action.md)).

## Runtime governance (in progress)

- **`POST /v1/runtime/evaluate`** — Preview namespace; OpenAPI describes fail-closed and shadow semantics. **Does not** replace `GET /compliance-summary` as the authoritative promotion verdict.
- **Governance enforcement modes** — Environment-driven enforcement overlays (see OpenAPI and `GET /status` / `GET /ready` diagnostics). **Planned:** broader rollout guidance and dashboards surfacing enforcement mode per tenant.

## AI Act / enterprise governance (planned / partial)

- **Evidence pack interchange** — [`standards/governance_evidence_pack_standard.md`](standards/governance_evidence_pack_standard.md) and validators (`python -m aigov_py.standards.cli …`). **Planned:** deeper mapping tables to regulatory annexes (documentation-only; not legal advice).
- **Trust center and procurement packs** — See [`trust/trust-center.md`](trust/trust-center.md) and commercial docs under `docs/commercial/`. **Planned:** more buyer-ready one-pagers derived from shipped behaviour only.

## Standards and interoperability (in progress)

- **Phase 5 / Phase 6 standards tooling** — Capability policies, delegation graphs, trace verification plans under `docs/standards/` and `python/aigov_py/standards/`.
- **Planned:** additional export formats only when backward-compatible per OpenAPI breaking-change rules.

## Long-term governance control plane (planned)

- **Unified policy lifecycle** — Stronger versioning UX across repos, policies, and evidence packs (no weakening of fail-closed defaults).
- **Immutability options** — Optional external immutability anchors for exports (design phase; not a commitment to a specific vendor).
- **Multi-region and DR** — Operational patterns for ledger durability beyond single-region Postgres (planned; depends on enterprise demand).

## Non-goals (explicit)

- Weakening CI governance gates or verdict semantics to chase adoption metrics.
- Silent auto-migration of customer evidence packs without explicit operator action.
- Replacing Postgres durability guarantees with best-effort caches for **authoritative** verdicts.

## How to influence priorities

Open a discussion or issue referencing your deployment topology, compliance regime, and evidence volume characteristics. Security-sensitive requests may be routed privately per `SECURITY.md` in the repository root.

## Planning artefacts

Historical consolidation notes: [`reports/repo-debt-audit-and-cleanup.md`](reports/repo-debt-audit-and-cleanup.md).
