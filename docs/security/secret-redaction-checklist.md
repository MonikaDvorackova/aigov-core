# Secret redaction checklist (security program v0)

`SEC_PROGRAM_SECRET_REDACTION`

- [ ] Never log raw `Authorization` bearer tokens or `GOVAI_API_KEYS` entries.
- [ ] Redact database URLs in diagnostics (`postgresql://...`).
- [ ] Keep `/metrics` free of tenant identifiers, prompts, and evidence payloads (counters and bounded route labels only).
- [ ] Structured ops logs must omit payloads; use fingerprints already emitted by `audit_api_key` diagnostics.

Code reference: `rust/src/ops_log.rs`, `rust/src/audit_api_key.rs`.
