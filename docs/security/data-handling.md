# Data handling

Enterprise teams typically ask what data GovAI touches, where it flows, and what operators must protect. This page frames **categories** of data and **practical handling expectations** without redefining product semantics (those remain in canonical architecture and API docs).

## Data categories

1. **Audit and compliance artefacts** — evidence bundles, run identifiers, policy snapshots, exported reports, and related digests. Often sensitive because they encode **deployment and governance decisions**.
2. **API credentials** — bearer tokens and service keys used to authenticate to the audit API. Must be treated as **secrets** (see [secrets-management.md](secrets-management.md)).
3. **Tenant metadata** — project labels and headers used for metering or correlation. **Not** a substitute for tenant isolation for ledger routes; see [tenant-isolation.md](tenant-isolation.md).
4. **Operational telemetry** — depends on your deployment (logs, metrics, APM). Not prescribed by this repo alone; classify according to your retention policy.

## Storage locations

- **Self-hosted:** operators choose Postgres, ledger file paths, and object storage (if used). You control encryption at rest, backups, and access logging.
- **OSS workspace:** local clones may contain sample evidence under `docs/` or generated artefacts during demos; do not commit production secrets or customer evidence.

## Retention and deletion

Retention is a **joint** decision between your organization and your GovAI deployment policy. The engine supports append-only audit semantics; **legal holds**, **data subject requests**, and **tenant offboarding** must be designed in your control plane and contracts.

## Cross-border and residency

The codebase does not enforce a region. Hosted or self-hosted deployments must document **where** primary data resides and which subprocessors apply.

## Related reading

- [security-overview.md](security-overview.md)
- [audit-ledger-security.md](audit-ledger-security.md)
- [../trust/trust-center.md](../trust/trust-center.md)
