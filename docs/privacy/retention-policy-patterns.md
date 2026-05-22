# Retention policy patterns

Retention balances **regulatory needs**, **debuggability**, and **cost**. GovAI supports conceptual tiers; exact enforcement is operator-configured.

## Tiers (illustrative)

| Tier | Contents | Typical retention driver |
|------|----------|---------------------------|
| Hot | Recent JSONL ledger segments, fast query | Active development window |
| Warm | Compressed archives, bundle exports | Audit window (e.g. 12–36 months) |
| Cold | Object-lock buckets, tape-class storage | Legal hold, sector rules |

## Differential retention

- **High-volume telemetry** may expire before **approval and promotion** records.
- **AI decision traces** (where enabled) may use shorter TTL than financial approval events.

## Conflicts with immutability

Legal erasure requests against immutable logs require architectural choices: cryptographic erasure of keys, segmented ledgers, or counsel-approved exceptions.

## Related

- `docs/operations/scalability-and-retention-patterns.md`
- `docs/operations/evidence-tiering.md`
