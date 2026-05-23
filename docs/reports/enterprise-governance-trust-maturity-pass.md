# Enterprise governance and trust maturity pass

**Date:** 2026-05-22  
**Scope:** Targeted documentation and trust narrative improvements after platform stabilization, commercial normalization, pricing normalization, `govai-core` runtime extraction, and hosted SaaS boundary separation.  
**Out of scope:** Pricing cleanup, OSS licensing rewrites, tier renaming, marketing landing polish, fake certifications.

## Summary

This pass strengthens GovAI’s presentation as **evidence-grade AI governance infrastructure** for enterprise architects, security reviewers, and AI governance leads. It adds a canonical architecture hub, formal governance semantics, hosted/self-host topology, an enterprise trust package, EU AI Act positioning without over-claims, and enforced terminology — while preserving proprietary Platform vs portable Core boundaries and deterministic `VALID` / `INVALID` / `BLOCKED` semantics.

---

## Changed files

### New documents

| File | Purpose |
|------|---------|
| `docs/architecture/README.md` | Enterprise architecture hub and document map |
| `docs/architecture/platform-vs-core-boundary.md` | GovAI Platform vs GovAI Core; control plane vs runtime |
| `docs/architecture/hosted-vs-self-host-topology.md` | Deployment topologies and evidence location |
| `docs/architecture/governance-semantics.md` | Formal verdict, integrity, replay, chain-of-custody semantics |
| `docs/architecture/governance-execution-flow.md` | End-to-end governance execution sequence |
| `docs/architecture/evidence-lifecycle.md` | Evidence lifecycle narrative and state model |
| `docs/architecture/policy-evaluation-lifecycle.md` | Policy evaluation at ingest and projection |
| `docs/architecture/decision-trace-lifecycle.md` | Decision trace vs ledger authority |
| `docs/architecture/append-only-ledger-semantics.md` | Ledger guarantees and non-guarantees |
| `docs/architecture/tenant-isolation-architecture.md` | Architecture view of tenant isolation |
| `docs/terminology.md` | Canonical terminology and discouraged phrasing |
| `docs/trust/enterprise-trust-package.md` | Procurement/security trust entry |
| `docs/trust/shared-responsibility-model.md` | Hosted vs self-host RACI-style matrix |
| `docs/regulatory/ai-act-enterprise-positioning.md` | Provider/deployer framing without certification claims |
| `docs/reports/enterprise-governance-trust-maturity-pass.md` | This report |

### Updated documents

| File | Change |
|------|--------|
| `docs/architecture/overview.md` | Rewritten for Platform/Core split, lifecycles, enterprise links |
| `docs/index.md` | Role routing and documentation pillars for enterprise governance |
| `docs/security/security-overview.md` | Links to trust package, shared responsibility, governance semantics |
| `docs/trust/trust-center.md` | Enterprise procurement and architecture entry points |
| `docs/regulatory/ai-act-mapping.md` | Provider/deployer and governance vs conformity sections |
| `docs/regulatory/README.md` | Index entry for enterprise positioning |
| `docs/runtime/deployment-guidance.md` | Topology and boundary cross-links |
| `docs/architecture/diagrams/evidence_lifecycle.md` | Cross-link to narrative lifecycle doc |
| `docs/architecture/diagrams/audit_replay_architecture.md` | Cross-link to formal replay semantics |
| `OPEN_SOURCE_SCOPE.md` | GovAI Platform vs GovAI Core naming; architecture links |
| `docs/trust/trust-manifest.json` | Registered new trust and governance semantics paths |

---

## Architecture improvements

- **Single enterprise entry:** `docs/architecture/README.md` routes reviewers through boundary, topology, lifecycles, and diagrams without marketing presets as the only content.
- **Platform vs Core clarity:** Explicit table of what writes the ledger vs what provides workflow, billing, and dashboard (`platform-vs-core-boundary.md`).
- **Hosted vs self-host:** Mermaid topologies showing customer vs operator custody of ledger, Postgres, and exports (`hosted-vs-self-host-topology.md`).
- **Lifecycle coverage:** Dedicated pages for evidence, policy evaluation, decision trace, and governance execution — linked from refreshed `overview.md`.
- **Control plane separation:** Documented that JWT `/api/*` does not append to the ledger or replace `policy.rs`, aligned with `strong-core-contract-note.md` and `ENTERPRISE_LAYER.md`.

---

## Governance formalization improvements

- **Deterministic verdict model:** `governance-semantics.md` defines `VALID`, `INVALID`, `BLOCKED`, fail-closed rules, workflow vs governance state, and determinism statement.
- **Integrity vocabulary:** Append-only guarantees, digest continuity, reconstructibility, and audit replay success/failure criteria documented separately from informal diagrams.
- **Chain of custody:** Stages from submit through export to independent verify/replay, with explicit limits on actor identity.
- **Event classes:** Policy evaluation, human approval, discovery-derived requirements, and artifact binding tied to verdict impact.
- **Trace export semantics:** Decision trace interchange distinguished from authoritative compliance verdict; preview runtime evaluate marked advisory.

---

## Trust maturity improvements

- **Enterprise trust package:** Central page for procurement with principles, limitations, retention, threat assumptions summary, and explicit non-certification statements (`enterprise-trust-package.md`).
- **Shared responsibility model:** Hosted Professional vs self-host Enterprise matrix for runtime, keys, ledger backup, exports, and legal conformity (`shared-responsibility-model.md`).
- **Security overview integration:** Security doc now points to trust package and semantics for RFP-aligned reading order.
- **Trust manifest:** New documents registered for `validate_trust_manifest.py` / enterprise readiness diagnostics.

No fabricated SOC 2, ISO, FedRAMP, or “AI Act compliant” product claims were introduced.

---

## Deployment clarity improvements

- **Trust boundaries:** Ingress, API key mapping, ledger partition, and optional Platform APIs shown per deployment mode.
- **Operational probes:** `/health` vs `/ready` reiterated in topology and security cross-links.
- **SDK/runtime relationship:** Integrators bound to Core HTTP contracts; Platform surfaces called out as proprietary optional layer.
- **Evidence storage:** Authoritative ledger at operator/customer runtime; long-term archive explicitly customer GRC responsibility.

---

## Terminology enforcement

- **`docs/terminology.md`:** GovAI Platform, GovAI Core, Hosted Professional, Enterprise, Strategic Advisory, governance execution, audit evidence, compliance verdict, policy evaluation, evidence replay.
- **Discouraged phrasing:** Observability-platform framing, “AI copilot governance,” “AI Act compliant” guarantees, “certified by GovAI.”
- **Index and trust-center routing** updated so enterprise buyers land on terminology and trust package first.

Existing `docs/observability/` remains for **operational telemetry** with explicit non-authority over verdicts (unchanged scope; not renamed in this pass to avoid broad churn).

---

## Regulatory positioning improvements

- **`ai-act-enterprise-positioning.md`:** Provider/deployer table, high-risk framing as customer classification, human oversight at evidence layer, explicit “does not supply” list.
- **`ai-act-mapping.md`:** Short governance vs conformity table and link to enterprise positioning.
- **No new certification language** or legal conformity guarantees.

---

## Remaining maturity gaps

| Gap | Recommendation |
|-----|----------------|
| **Diagram set not unified** | Some `docs/architecture/diagrams/*.md` files still lack narrative companions (policy engine, CI flow, high-level) — extend cross-links in a follow-up |
| **Product marketing pages** | `docs/product/` may still use legacy “open source vs hosted” framing — align to Platform/Core terminology in a dedicated product pass |
| **Hosted docs scatter** | Hosted material lives under `hosted-backend-deployment.md` and manifests; consider `docs/hosted/README.md` hub mirroring architecture README |
| **Multi-tenant JSON vs prose** | Machine-readable `multi-tenant/` manifests exist; deeper alignment with new tenant isolation architecture page for RFP automation |
| **Runtime observability naming** | Directory name `observability/` is intentional for operators; glossary steers governance readers away from conflating it with verdicts |
| **Separate govai-core repo docs** | If runtime is canonical in external **govai-core** GitHub, mirror or symlink architecture hub there to avoid dual-narrative drift |
| **Pen test / third-party attestations** | No public pen-test summary in tree — add only when real engagements exist |
| **WORM / immutability product options** | Roadmap items; document operator patterns when shipped |

---

## Final enterprise readiness assessment

| Dimension | Assessment | Notes |
|-----------|------------|-------|
| **Architecture clarity** | **Strong** | Platform/Core, hosted/self-host, and lifecycles are now navigable from one hub |
| **Governance semantics** | **Strong** | Verdicts, ledger, replay, and workflow reconciliation are formally documented |
| **Trust / procurement** | **Good → Strong** | Enterprise trust package and shared responsibility suitable for security questionnaires; not a substitute for customer SOC program |
| **Regulatory narrative** | **Good** | Indicative AI Act mapping with explicit non-claims; counsel still required |
| **Terminology consistency** | **Good** | Canonical glossary added; full-repo sweep not performed |
| **Deployment maturity** | **Good** | Topology and boundaries clear; operator runbooks already exist separately |
| **Evidence-grade positioning** | **Strong** | Narrative emphasizes audit infrastructure over observability SaaS |

**Overall:** GovAI documentation now presents a **coherent enterprise AI governance infrastructure** story suitable for architects and procurement, with technically defensible semantics and honest limitation statements. Further maturity is primarily **product copy alignment**, **hosted doc hub consolidation**, and **external govai-core repo parity** — not additional compliance buzzwords.

---

## Validation checklist (pass)

- [x] Terminology references GovAI Platform and GovAI Core consistently in new material
- [x] Hosted vs self-host boundaries explicit with custody tables
- [x] Governance semantics remain deterministic and linked to `GET /compliance-summary`
- [x] No fake regulatory or certification claims added
- [x] Enterprise readers have a single architecture README and trust package entry
- [x] Exactly one report generated at `docs/reports/enterprise-governance-trust-maturity-pass.md`

## Evaluation gate

Passed. The branch was evaluated against the repository governance and compliance gate expectations.

## Human approval gate

Pending maintainer review before merge.
