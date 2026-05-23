# EU AI Act — enterprise positioning

This document positions GovAI for **enterprise and regulatory readers** without claiming product certification or legal conformity.

## Role in the AI value chain

The EU Artificial Intelligence Act distinguishes roles such as **provider**, **deployer**, **importer**, and **distributor**. GovAI is **governance and audit infrastructure** used by those actors; it is not a substitute for their legal obligations.

| Role | Typical GovAI usage |
|------|-------------------|
| **Provider** (develops high-risk AI system) | Record development, evaluation, and release evidence; export technical file inputs |
| **Deployer** (uses AI system in professional context) | Gate deployments; document human oversight and monitoring hooks |
| **Integrator / platform team** | Operate hosted or self-host Core; map tenants and retention |

GovAI does **not** auto-classify your system as high-risk, limited-risk, or minimal-risk. Classification remains with your organization and counsel.

## What GovAI supplies (auditability)

| Theme | GovAI artefact | Limitation |
|-------|----------------|------------|
| Technical documentation inputs | Exports, bundles, regulatory Markdown generator | Not a complete Annex IV file without your content |
| Logging of governance decisions | Append-only ledger + compliance verdict | Not all runtime inference logs unless you submit them |
| Record-keeping | Stable `run_id`, export hashes | Retention period is operator/customer defined |
| Human oversight hooks | Approval evidence events; **BLOCKED** until prerequisites | Does not replace operational stop procedures |
| Post-market monitoring hooks | Evidence and export patterns | Customer defines monitoring process |
| Risk management alignment | Risk lifecycle events in projection | Does not replace your risk register |

Indicative obligation index: [ai-act-obligations.json](ai-act-obligations.json). Matrix: [evidence-obligations.md](evidence-obligations.md).

## What GovAI does not supply

- EU declaration of conformity
- Notified body assessment outcomes
- Legal interpretation of GPAI systemic risk
- “AI Act compliant” product label
- Guaranteed coverage of every Article 9–15 measure without customer process

## High-risk deployment framing

For systems **you** classify as high-risk under Annex III:

1. **Define policy** — required evidence, evaluations, approvals in `policy_version`.
2. **Execute governance** — post evidence; obtain `VALID` before promotion when gates require it.
3. **Export** — `GET /api/export/:run_id` and regulatory export scripts for reviewer packets.
4. **Retain** — customer archive with chain-of-custody.
5. **Oversight** — human approval events + customer runbooks ([human-oversight.md](human-oversight.md)).

GovAI supports **demonstrating process** with integrity; it does not remove conformity assessment where the Act requires it ([conformity-assessment.md](conformity-assessment.md)).

## Provider vs deployer — auditability positioning

| Question | GovAI answer |
|----------|--------------|
| Who is accountable for conformity? | Legal actors (provider/deployer), not the GovAI vendor by default |
| What does GovAI prove? | Recorded evidence and deterministic verdict for that evidence |
| Can deployers use the same Core? | Yes — self-host or hosted; same semantics |
| Does hosted shift provider status? | Hosting does not transfer your AI Act role; contract defines processor terms |

## Human oversight semantics

Article 14-style oversight requires **effective human oversight during use**. GovAI models oversight at the **governance evidence** layer:

- Approval and promotion events in the ledger
- **BLOCKED** when oversight prerequisites are missing
- Engineering report gates in repository workflows (pattern only; not operational kill switch)

Deployers must still define real-world override and stop authority outside GovAI.

## Governance vs legal compliance

| Layer | GovAI |
|-------|-------|
| **Governance execution** | Verdict + evidence + replay |
| **Legal compliance** | Customer process + assessors + counsel |

Use [ai-act-mapping.md](ai-act-mapping.md) as a **navigation aid**, not an attestation.

## Related

- [README.md](README.md)
- [high-risk-system-obligations.md](high-risk-system-obligations.md)
- [regulator-export-guide.md](regulator-export-guide.md)
- [../architecture/governance-semantics.md](../architecture/governance-semantics.md)
