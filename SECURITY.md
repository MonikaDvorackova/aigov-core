# Security Policy

**GovAI Core** is open-source governance infrastructure for AI systems. Security reports are taken seriously because the project handles audit evidence, ledger integrity, tenant isolation, and enforcement behavior in the `aigov_audit` runtime.

## Reporting a vulnerability

Please do not publicly disclose unpatched vulnerabilities.

Report security concerns privately through GitHub Security Advisories or by contacting the project maintainer.

## Scope

Security relevant areas include:
- API key handling
- tenant isolation
- audit ledger integrity
- evidence bundle integrity
- evidence replay correctness
- cryptographic verification
- deployment configuration
- CI compliance gate bypasses
- unauthorized governance actions

## Tenant isolation

GovAI tenant isolation is derived from server-side API key mapping.

Headers such as X-GovAI-Project are metadata only and must not be treated as security boundaries.

## Evidence integrity

Audit evidence must preserve integrity and traceability.

Security reports involving evidence tampering, digest mismatch bypasses, replay inconsistencies, or audit export manipulation are in scope.

## Fail-closed behavior

GovAI should fail closed when required evidence, approval, audit context, or integrity guarantees are missing.

Reports showing fail-open behavior are security relevant.

## Supported versions

Security fixes are prioritized for the latest public release and active development branches.

## Disclosure process

After a report is received:
1. The issue is assessed.
2. A fix is prepared privately where appropriate.
3. Tests are added for the security invariant.
4. A patched release or advisory is published when needed.

## Out of scope

The following are generally out of scope unless they affect GovAI security boundaries:
- purely cosmetic UI issues
- documentation typos
- local misconfiguration without security impact
- issues requiring full maintainer credentials
