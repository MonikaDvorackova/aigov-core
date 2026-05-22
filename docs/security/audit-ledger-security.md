# Audit ledger security

The audit **ledger** records governance-relevant events in an append-oriented model suitable for inspection and export. This page describes **security properties reviewers care about**, not billing or commercial metering semantics (unchanged by Phase 8 documentation).

## Integrity and ordering

- Events should be **tamper-evident** within the deployment’s threat model (file permissions, database controls, or object-store policies depending on backend).
- **Digest and export flows** tie external artefacts back to server-side state; bypass or mismatch is a finding, not a silent success.

## Access control

- Read and write paths must respect **tenant isolation** (see [tenant-isolation.md](tenant-isolation.md)).
- Administrative access (migrations, disk repair, backup restore) is a **high privilege** path requiring break-glass procedures.

## Backup and restore

Restores can **replay** or **duplicate** events if not coordinated with application-level deduplication. Document **who** may restore, **how** integrity is re-verified, and **how** RPO/RTO maps to your compliance story.

## Export surface

Audit export endpoints and CLI flows can emit sensitive material. Gate them with the same authentication model as the rest of the audit API and monitor for abnormal bulk access.

## Related reading

- [security-overview.md](security-overview.md)
- [incident-response.md](incident-response.md)
- [../../docs/evidence-pack.md](../../docs/evidence-pack.md) (evidence artefacts)
