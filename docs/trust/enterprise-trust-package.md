# Enterprise trust package

This page is the **procurement and security entry** for GovAI trust posture. It states what the software provides, what operators and customers must provide, and explicit **non-goals** — without fabricated certifications or compliance guarantees.

## What GovAI is

GovAI is **evidence-grade AI governance infrastructure**:

- Append-only **audit evidence** with hash-chained integrity
- **Fail-closed** compliance verdicts (`VALID`, `INVALID`, `BLOCKED`)
- Deterministic **policy evaluation** at ingest and projection
- Exportable artefacts for GRC, internal audit, and indicative regulatory narratives

GovAI is **not** a generic AI observability product, a copilot wrapper, or a substitute for legal counsel or notified-body conformity assessment.

## Trust principles

| Principle | Implementation pointer |
|-----------|-------------------------|
| Single authoritative verdict | `GET /compliance-summary` — [trust-model.md](../trust-model.md) |
| Evidence integrity | `GET /verify`, bundle hashes, evidence packs — [audit-ledger-security.md](../security/audit-ledger-security.md) |
| Tenant isolation | API key → `tenant_id` mapping — [tenant-isolation.md](../security/tenant-isolation.md) |
| Readiness discipline | `GET /ready` for dependency-safe traffic — [security-overview.md](../security/security-overview.md) |
| Cryptographic optional layer | Signing and attestation — [immutable-trust-chain.md](immutable-trust-chain.md) |

## Deployment responsibilities

| Area | Hosted Professional | Self-host Enterprise |
|------|---------------------|----------------------|
| Runtime availability | GovAI Platform operator | Customer |
| Postgres and migrations | Operator | Customer |
| API keys and rotation | Platform onboarding + operator | Customer |
| Ledger backup / DR | Operator per contract | Customer |
| Network ingress / WAF | Operator | Customer |
| Evidence export archive | Customer GRC systems | Customer GRC systems |
| Legal conformity decisions | Customer + counsel | Customer + counsel |

Full RACI: [shared-responsibility-model.md](shared-responsibility-model.md).

## Threat assumptions (summary)

Reviews should assume:

- **Stolen API keys** grant ledger write and read within a tenant until rotation.
- **Insider with operator access** can affect hosted availability and configuration; cryptographic signing reduces undetected export tampering when enabled.
- **Incomplete submission** produces **BLOCKED**, not silent pass — attackers cannot bypass policy by omitting events unless your gate is misconfigured to ignore summary.
- **Client headers** (`X-GovAI-Project`) are not isolation controls.

Deeper material: [threat-model-summary.md](../security/threat-model-summary.md), [../standards/threat-model.md](../standards/threat-model.md).

## Evidence limitations (explicit)

GovAI **does not** by itself prove:

- Truthfulness of model inputs or outputs
- That all production traffic was logged
- Runtime equivalence between described and deployed models
- Regulatory conformity or CE marking
- SOC 2, ISO 27001, or FedRAMP certification (unless your organization attains them separately)

GovAI **does** support:

- Tamper-evident recording of submitted events
- Deterministic verdict given recorded events and `policy_version`
- Reproducible export and replay for independent review

## Retention semantics

| Data class | Typical locus | Retention driver |
|------------|---------------|------------------|
| Ledger (`audit_log.jsonl`) | Operator or customer volume | Contract, legal hold, AI system lifecycle |
| Postgres product tables | Same deployment | Platform workflow and billing |
| Customer exports | Customer artefact store | GRC policy |
| Telemetry (operational) | Operator monitoring stack | SLO and incident needs — **does not** change verdict |

Detail: [data-handling.md](../security/data-handling.md).

## Governance limitations

| Limitation | Mitigation |
|------------|------------|
| Policy version drift | Pin `policy_version` in CI; change management |
| Workflow vs ledger mismatch | Reconcile Platform queue with compliance summary |
| Discovery false positives/negatives | Human review of discovery-derived **BLOCKED** |
| Preview runtime evaluate | Treat as advisory only |

## Regulatory positioning (non-certifying)

EU AI Act **mapping is indicative** — see [../regulatory/ai-act-mapping.md](../regulatory/ai-act-mapping.md) and [../regulatory/ai-act-enterprise-positioning.md](../regulatory/ai-act-enterprise-positioning.md). GovAI supplies technical evidence artefacts; **providers and deployers** remain responsible for legal classification and conformity.

## Document map for reviewers

| Review type | Documents |
|-------------|-----------|
| Architecture | [../architecture/README.md](../architecture/README.md) |
| Semantics | [../architecture/governance-semantics.md](../architecture/governance-semantics.md) |
| Security | [../security/security-overview.md](../security/security-overview.md) |
| Compliance mapping aid | [compliance-mapping.md](compliance-mapping.md) |
| FAQ | [enterprise-faq.md](enterprise-faq.md) |
| Disclosure | [responsible-disclosure.md](responsible-disclosure.md) |

## Machine-readable checks

Operators can run repository diagnostics (not a certification):

```bash
python3 scripts/security_trust_check.py --json
make enterprise-readiness-check
```

See [trust-manifest.json](trust-manifest.json).
