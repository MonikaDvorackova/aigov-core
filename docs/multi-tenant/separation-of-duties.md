# Separation of duties

The [`separation-of-duties.json`](../../multi-tenant/separation-of-duties.json) artefact encodes **mutually exclusive role sets**, **dual control** on sensitive actions, and **minimum reviewer pool** size.

## Mutually exclusive roles

Each entry lists two or more roles that should not be held by the same person **without** a documented exception process. Examples include:

- operators vs read-only auditors for the same change window;
- platform superadmin vs default read-only support;
- billing administration vs full tenant engineering administration.

## Dual control

Actions such as production promotion, policy edits, and break-glass requests require two independent approvers. Map these labels to your ticketing or PAM system.

## Evidence retention

Approval records should be timestamped and retained for at least the minimum period in the JSON bundle to satisfy downstream audits.
