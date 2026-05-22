# Delegated administration

Delegated administration lets enterprises grant **narrow** administrative rights to partners or internal teams without handing out full tenant ownership.

## Delegation scopes

The [`delegated-administration.json`](../../multi-tenant/delegated-administration.json) artefact lists scopes such as:

- **nonprod_only** — actions limited to development and staging tags.
- **read_export_only** — read compliance summaries and exports where policy already allows.
- **integration_limited** — manage webhooks and integration settings in non-production.

Each scope is intended to pair with your identity provider groups and approval workflows.

## Time bounds

`max_scope_duration_hours` caps how long an elevation may remain valid without renewal. Operators should align this field with corporate policy (often eight hours or less).

## Break-glass

Break-glass roles require MFA, ticket references, peer approval, and short session windows. Events such as `break_glass.started` should land in your SIEM for retrospective review.

## Attestation

`attestation_required` signals that delegated access grants should store a **human-readable attestation** (for example change ticket or approver id) alongside the grant record.
