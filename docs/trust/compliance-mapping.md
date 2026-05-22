# Compliance mapping (informative)

This page helps **map GovAI capabilities** to common questionnaire themes. It is **not** a statement of certification, suitability, or legal compliance for your jurisdiction or industry.

## How to use this document

Treat each row as a **conversation starter** between your risk team and the deployment operator. Evidence should be collected from **your** environment (configuration, logs, contracts), not inferred from OSS docs alone.

## Typical control themes

| Theme | GovAI relevance | Suggested evidence |
|-------|-----------------|--------------------|
| Access control | API keys, optional RBAC in hosted setups | Key rotation policy, IAM screenshots (redacted) |
| Audit logging | Append-oriented ledger and exports | Sample export procedure, log retention policy |
| Integrity | Digests, verify flows | CI job using `govai verify-evidence-pack` or equivalent |
| Change management | Git, semver, migrations | PR history, migration runbooks |
| Incident response | Operator playbooks | Links to [../security/incident-response.md](../security/incident-response.md) + your IR plan |

## Standards frameworks

Mappings to **SOC 2**, **ISO 27001**, **NIST CSF**, **EU AI Act** articles, or **ISO/IEC 42001** clauses require **your** control owners to fill gaps. GovAI supplies **technical hooks** (evidence, verdicts, isolation model); organizational controls remain yours.

| Framework | GovAI artefact | Claim level |
|-----------|----------------|-------------|
| ISO/IEC 42001:2023 | [`../standards/iso-42001-alignment-manifest.json`](../standards/iso-42001-alignment-manifest.json), [`../standards/iso-42001-clause-index.json`](../standards/iso-42001-clause-index.json) | **Readiness support** — indicative mapping and CI-validated paths only; not certification |
| EU AI Act (informative) | [`../regulatory/regulatory-evidence-manifest.json`](../regulatory/regulatory-evidence-manifest.json) | Technical evidence scaffolding; not legal conformity |

## Related reading

- [trust-center.md](trust-center.md)
- [../security/security-overview.md](../security/security-overview.md)
