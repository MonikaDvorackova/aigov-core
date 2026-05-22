# Privacy architecture (deployment-oriented)

GovAI’s privacy posture combines **technical controls** (tenant isolation, RBAC, optional encryption) with **policy-driven minimisation** of what enters the evidence ledger. Final compliance with GDPR, CCPA, or other regimes remains **organisational** and **deployment-specific**.

## Tenant isolation

- Evidence ledgers and API responses are **scoped** to tenant context in hosted and enterprise deployments (see `docs/multi-tenant/overview.md`, `ARCHITECTURE.md` core vs enterprise split).

## RBAC

- Product roles gate review queues, exports, tenant console reads, and sensitive operations (`rust/src/rbac.rs`).

## Encryption

- **In transit:** TLS for HTTP clients.
- **At rest:** depends on Postgres and object storage configuration (TDE, volume encryption, KMS-managed keys).

## Selective redaction

- Operators may strip or hash PII **before** emitting evidence events; policy modules can require minimised fields.

## GDPR / CCPA considerations (non-exhaustive)

- Lawful basis and purpose limitation for telemetry stored as evidence.
- Data subject access and erasure requests may conflict with immutable logs — require **legal process design** (retention tiers, pseudonymisation keys held separately).

## Caveats

Enterprise marketing copy may describe SAML, retention, or air-gap options that require **SKU and contract** alignment; always verify against your deployed build.

## Related

- `docs/privacy/data-minimization-patterns.md`
- `docs/privacy/retention-policy-patterns.md`
- `docs/commercial/enterprise-features.md`
