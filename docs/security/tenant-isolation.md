# Tenant isolation

Tenant isolation determines **which tenant’s ledger and audit state** a request may read or write. Misunderstanding this boundary is a common source of false confidence in reviews.

## Source of truth

For ledger-touching routes in configured non-dev environments, **tenant context is resolved from the API key** (for example via `GOVAI_API_KEYS_JSON` mapping). Client headers such as **`X-GovAI-Project`** are **metadata** for correlation or metering and must not be treated as the sole security selector for ledger access.

This model is also stated in root [SECURITY.md](../../SECURITY.md). Product behaviour details live in service code and integration tests; this document is for **security reviewers**.

## Threat considerations

- **Key confusion:** two teams sharing one key share one tenant boundary. Issue distinct keys per tenant where isolation matters.
- **Header spoofing:** without a valid mapped key, spoofed project headers must not grant access to another tenant’s ledger.
- **Logs:** ensure structured logs do not accidentally print bearer tokens or full key material.

## Testing

The repository includes HTTP-level tests around tenant behaviour; operators should add **environment-specific** penetration tests and periodic access reviews.

## Related reading

- [audit-ledger-security.md](audit-ledger-security.md)
- [data-handling.md](data-handling.md)
- [../trust/enterprise-faq.md](../trust/enterprise-faq.md)
