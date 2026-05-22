# Chain of custody (technical evidence)

**Chain of custody** in legal proceedings is a procedural concept: who handled a record, when, and under what controls. GovAI contributes **technical primitives** that operators can map into their legal procedures; it does not replace counsel or notaries.

## Technical hooks

- **Append-only ledger** with hash linkage — detects many classes of tampering if an authoritative copy is preserved.
- **Export APIs** — stable JSON suitable for time-stamped archives.
- **RBAC** — restricts who can submit, approve, or export (enterprise layer).

## Operator responsibilities

- Define **custodial roles** (submitter, reviewer, archivist).
- Capture **environment context** (commit SHA, service version, tenant id) in evidence or adjacent records.
- Apply **timestamping** or **notarisation** services where counsel advises (qualified electronic timestamps, commercial TSA, etc.).

## Disclaimer

Technical integrity of a file does not automatically satisfy evidentiary **authentication** rules in any given court. Follow local counsel.

## Related

- `docs/legal/evidentiary-positioning.md`
- `docs/legal/jurisdictional-limitations.md`
