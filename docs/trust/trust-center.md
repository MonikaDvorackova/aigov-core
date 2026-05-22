# Trust center

The **trust center** is the single entry point for security, privacy, and reliability questions from **enterprise buyers** evaluating GovAI. Deep dives live in `docs/security/` and the pages below.

```docs
preset: trust-controls
```

## What GovAI provides

- **Evidence-first governance** — auditable artefacts tied to policy and run identifiers.
- **Deterministic OSS gates** — repository checks (including documentation presence and link integrity) that teams can mirror in CI.
- **Clear isolation story** — tenant boundaries for ledger-backed operations are rooted in **server-side key mapping** (see [../security/tenant-isolation.md](../security/tenant-isolation.md)).

## What GovAI does not provide by itself

- Legal advice or regulatory **certification**.
- Your SOC 2 control implementation — we document **interfaces**; you operate **controls**.

## Document map

| Audience | Start here |
|----------|------------|
| Security architecture | [../security/security-overview.md](../security/security-overview.md) |
| Procurement / RFP | [compliance-mapping.md](compliance-mapping.md) |
| ISO/IEC 42001 readiness (mapped, not certified) | [../standards/iso-42001.md](../standards/iso-42001.md) |
| Researchers / reporters | [responsible-disclosure.md](responsible-disclosure.md) |
| Sales engineering | [enterprise-faq.md](enterprise-faq.md) |
| Cryptographic signing and verification | [immutable-trust-chain.md](immutable-trust-chain.md), [evidence-signing.md](evidence-signing.md), [verification-workflows.md](verification-workflows.md) |
| Key lifecycle and HSM practices | [key-rotation.md](key-rotation.md), [private-key-governance.md](private-key-governance.md) |
| Vendor and auditor handoff | [cross-organization-attestation.md](cross-organization-attestation.md), [supply-chain-integrity.md](supply-chain-integrity.md) |
| Machine-readable profiles (repo root) | [`../../trust/README.md`](../../trust/README.md) |

## Contact

Use maintainer channels described in [responsible-disclosure.md](responsible-disclosure.md) for security-sensitive messages.
