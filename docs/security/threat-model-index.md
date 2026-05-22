# Threat model index (security program v0)

`SEC_PROGRAM_THREAT_INDEX`

This index links common threats to **runtime controls** (code) and **operator controls** (runbooks). It does not replace a full product-specific threat model workshop.

| Concern | Runtime / code path | Operator / docs |
| --- | --- | --- |
| Unauthorized audit API use | `rust/src/audit_api_key.rs`, `rust/src/rate_limit.rs` | `docs/security/secrets-management.md` |
| Tenant ledger cross-talk | `rust/src/project.rs`, `rust/src/audit_api_key.rs` | `docs/security/tenant-isolation.md` |
| Evidence tampering | `rust/src/audit_store.rs`, `scripts/disaster_recovery_ledger.py` | `docs/security/audit-ledger-security.md` |
| AI trace repudiation | `rust/src/ai_decision_audit.rs`, `rust/src/ai_decision_integrity.rs` | `docs/operator-runbook.md` |

See also: `docs/security/threat-matrix.md`, `docs/security/security-overview.md`.
