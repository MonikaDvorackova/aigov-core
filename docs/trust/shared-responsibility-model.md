# Shared responsibility model

GovAI deployments split obligations between **GovAI Platform (operator)** and **customer** depending on hosted vs self-host mode. This model supports security questionnaires without implying certifications GovAI does not hold.

## Responsibility matrix

| Control area | GovAI Platform (hosted) | Customer (all modes) |
|--------------|-------------------------|----------------------|
| **Governance verdict semantics** | Maintains Core implementation | Configures gates to use `GET /compliance-summary` |
| **Evidence submission** | — | CI, runtime, CLI post events |
| **Policy content** | Provides default/demo policies; hosted config | Adopts policy_version and change control |
| **API key secrecy** | Issues keys via onboarding UI | Stores keys in secret manager; rotation |
| **Tenant mapping** | Operates `GOVAI_API_KEYS_JSON` | Requests separate keys per env/team |
| **Ledger storage & backup** | Operator infrastructure | Self-host: customer DB and volumes |
| **Postgres HA** | Operator | Self-host: customer |
| **Ingress TLS** | Operator certificate | Self-host: customer mTLS/WAF |
| **Stripe billing** | Operator webhook endpoint | Payment method and subscription ownership |
| **Export long-term archive** | — | Customer GRC / WORM |
| **Human oversight process** | — | Customer operational procedures |
| **Legal AI Act classification** | — | Customer + counsel |
| **Conformity assessment** | — | Customer + notified body where required |
| **Incident notification to end users** | Operator security process | Customer comms to their users |

## Hosted Professional — operator boundaries

**GovAI controls:**

- Availability of hosted audit base URL
- Platform dashboard authentication (where enabled)
- Metering and billing webhooks when Stripe is configured
- Baseline migration and readiness checks before accepting traffic

**Customer controls:**

- What evidence is submitted and when
- CI failure thresholds on verdict
- Export retention in their systems
- Identity of humans approving changes in their IdP

## Self-host Enterprise — customer boundaries

**Customer controls:**

- Entire AIGov Core deployment boundary
- Network, secrets, backups, and `GET /ready` routing
- Optional Platform components if licensed separately

**GovAI provides:**

- Software artifacts, contracts, documentation, and support per agreement
- No implied operation of customer VPC resources

## Evidence storage boundary

| Location | Custodian | Notes |
|----------|-----------|-------|
| Live ledger | Runtime operator | Authoritative for verdict |
| `GET /api/export` copy | Customer | Chain-of-custody for audits |
| Evidence pack on disk | Customer | Offline verify/replay |
| Platform workflow rows | Platform operator DB | Not a second ledger |

## Operational boundaries

| Activity | Hosted | Self-host |
|----------|--------|-----------|
| Apply security patches to runtime | Operator | Customer |
| Run `make enterprise-readiness-check` in CI mirror | Customer optional | Customer optional |
| Configure `GOVAI_BILLING_ENFORCEMENT` | Operator env | Customer if billing enabled locally |

## Non-goals (shared)

Neither party should claim:

- Automatic EU AI Act conformity from software
- Replacement for customer risk management system
- Guaranteed detection of all AI usage in the estate

## Related

- [enterprise-trust-package.md](enterprise-trust-package.md)
- [../architecture/hosted-vs-self-host-topology.md](../architecture/hosted-vs-self-host-topology.md)
- [../hosted-backend-deployment.md](../hosted-backend-deployment.md)
