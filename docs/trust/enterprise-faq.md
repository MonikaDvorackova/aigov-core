# Enterprise FAQ

Frequently asked questions from **security**, **platform**, and **procurement** stakeholders evaluating GovAI.

## Is GovAI a certified compliance product?

No. GovAI is **governance and audit infrastructure**. It helps you **evidence** controls and enforce gates; it does not replace lawyers, auditors, or regulators.

## How is multi-tenant isolation enforced?

For ledger-backed operations, isolation is enforced using **server-side API key → tenant mapping**. Project headers are not the security boundary. See [../security/tenant-isolation.md](../security/tenant-isolation.md).

## Can we run entirely on-premises?

The OSS stack can be self-hosted with your Postgres and networking boundaries. Hosted offerings are subject to separate contracts and subprocessors.

## What data leaves our environment?

By default, **only what you configure** to call external services (for example a hosted GovAI URL, Stripe, or telemetry). Review [../security/data-handling.md](../security/data-handling.md) and your deployment diagram.

## How do we integrate with CI?

Use the composite GitHub Action and `govai` CLI patterns documented in [../../docs/github-action.md](../../docs/github-action.md). CI should fail closed when verdicts or digests do not match policy.

## Where is the SBOM?

Generate from your build (`cargo tree`, Python lockfiles or `pip-licenses`) until a published SBOM is attached to releases you consume.

## Who answers security questionnaires?

Start from [compliance-mapping.md](compliance-mapping.md) and attach **your** environment-specific evidence. Vendor security teams may request a **Vanta/Drata/CAIQ** export you maintain.

## Related reading

- [trust-center.md](trust-center.md)
- [../security/secure-deployment-checklist.md](../security/secure-deployment-checklist.md)
