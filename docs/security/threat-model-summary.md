# Threat model summary (GovAI)

## Trust boundary (positive claims)

GovAI aims to provide:

1. **Tamper-evidence** for append-only evidence ledgers via hash chaining (middle-record edits break verification).
2. **Deterministic compliance projection** from accepted evidence and configured policy version (`GET /compliance-summary`).
3. **Tenant-scoped** and **role-gated** access patterns in enterprise deployments (see `rust/src/rbac.rs`, multi-tenant documentation).

## Explicit non-claims

- No guarantee of **truthfulness** of submitted evidence.
- No guarantee of **completeness** of real-world behaviour versus logged events.
- No **legal certification**, court admissibility, or regulatory approval by default.

## Operational assumptions

- Operators retain **authoritative** copies of exports suitable for their jurisdiction.
- Identity strength of `actor` fields depends on deployment authentication, not on the JSON schema alone.

## Validation

```bash
make threat-model-check
```

## Related artefacts

- `examples/security/sample-threat-matrix.json`
- `docs/research/threats-to-validity.md`
- `scripts/threat_model_check.py`
