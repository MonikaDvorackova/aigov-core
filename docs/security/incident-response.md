# Security incident response

This document outlines a **practical incident response outline** for teams operating GovAI. Adapt roles, SLAs, and tooling to your organization.

## Detection

Potential signals include: unexpected **401/403** spikes, **digest verification failures** in CI, abnormal **export** volume, database **integrity errors**, or reports of **tenant cross-talk** (should never occur when keys are scoped correctly).

## Containment

1. **Rotate** suspected API keys and invalidate sessions if your IdP is in path.
2. **Freeze** high-risk changes (policy, ledger migrations) until scope is understood.
3. **Preserve** logs and ledger snapshots for forensics without destroying evidence.

## Eradication and recovery

- Patch vulnerable components; redeploy with verified configuration.
- Re-run **integrity checks** (for example evidence verify flows and compliance summary) on affected `run_id` values where applicable.
- Document **timeline** and **root cause** for post-incident review.

## Communication

- Follow your legal and PR playbooks for customer notification.
- For **upstream vulnerabilities** in GovAI OSS, use the process in [../trust/responsible-disclosure.md](../trust/responsible-disclosure.md) and root [SECURITY.md](../../SECURITY.md).

## Post-incident

Update threat models, runbooks, and training. Add regression tests where gaps were found.

## Related reading

- [secrets-management.md](secrets-management.md)
- [secure-deployment-checklist.md](secure-deployment-checklist.md)
