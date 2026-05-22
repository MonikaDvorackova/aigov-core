# Phase 5: Research and ecosystem program

**Status:** Active program spanning **research**, **interoperable standards**, **ecosystem growth**, and **commercial adoption**, anchored by shipped **Phase 5 ecosystem standards implementation** (see `docs/standards/README.md` and `python/aigov_py/standards/`).

GovAI is positioned as a **decision-centric governance control plane**: the authoritative question is whether a specific deployment or runtime decision is **eligible, evidenced, and reproducibly justified**, not merely whether a model passed offline metrics. **Multi-agent governance**, **cryptographic evidence**, and **fail-closed runtime enforcement** (when enabled by operators) are the long-term differentiators; Phase 5 makes the *interfaces* around those ideas portable so partners, regulators, and open-source contributors can align without forking the core engine.

---

## 1. Research agenda

1. **Auditability gap** — Model-centric validation answers “did metrics look good?” Decision-level governance answers “who approved what, under which policy snapshot, with which evidence artefacts bound by digest?” Phase 5 research targets measurable gaps between these two levels of assurance.
2. **Evidence-gated CI/CD** — Treat promotion as a **decision transaction**: evidence append order, policy snapshots, and artefact digests form a replayable narrative suitable for empirical security and governance studies.
3. **Runtime governance** — Study fail-closed semantics, shadow versus enforced modes, and tenant-scoped enforcement invariants (design intent documented in Phase 3/4 governance docs).
4. **Multi-agent accountability** — Delegation graphs, capability taxonomies, and replayable traces under explicit SoD constraints; formalize minimal graph properties (acyclicity, bounded depth) that match operational policies.
5. **Cryptographic attribution** — Digest-first envelopes, signing plans, and transparency-log style publication for autonomous actions (without claiming post-quantum readiness prematurely).

---

## 2. Publication roadmap (concrete paper tracks)

| Paper | Thesis | Contribution | Evaluation sketch | Target venues (examples) | Artifact | Risk to mitigate |
|-------|--------|--------------|-------------------|---------------------------|----------|------------------|
| **P1 — Evidence-gated CI/CD for decision-level AI governance** | Promotion without digest-linked evidence is non-auditable. | Formalize “decision transaction” + empirical CI bypass rates | Replay benchmarks on public CI traces + synthetic injection | USENIX Security workshops, IEEE TDSC | Reference policies + datasets | Overclaiming security without threat model |
| **P2 — Runtime governance under fail-closed semantics** | Shadow-only telemetry is insufficient for high-risk systems. | Semantics for shadow vs enforced; measurement of false-block rates | Controlled rollout A/B on synthetic workloads | NeurIPS / ICLR workshops | Simulator harness | Weak baseline comparisons |
| **P3 — Multi-agent accountability via delegation graphs** | Delegation edges must be first-class evidence. | Graph validation + SoD properties + trace replay | Property tests + red-team escalation scenarios | ACM FAccT, AIES | Delegation schema + traces | Scope creep beyond verifiable claims |
| **P4 — Cryptographic attribution for autonomous agents** | Non-repudiation requires digest-first signing envelopes. | Envelope preimage standards + key rotation model | Microbenchmarks + formal preimage analysis | USENIX Security | Signing test vectors | Key-management complexity understated |
| **P5 — AI Act readiness via machine-readable controls** | Mapping law to controls requires explicit evidence completeness. | Control graph + evidence completeness metrics | Legal scholar review + technical completeness checks | Legal-tech / AI governance venues | Control mapping YAML + packs | Legal overclaim |

---

## 3. Standards roadmap

### Shipped in repository (Phase 5 implementation)

| Standard | Purpose |
|----------|---------|
| **Open Capability Policy Schema** | Portable capability taxonomy + tool allowlists + evidence refs |
| **Delegation Graph Schema** | Acyclic delegation among humans/agents/services |
| **Trace Verification Plan Schema** | Structured verification outcomes + deterministic `plan_digest` |
| **Governance Evidence Pack Standard** | Digest-linked artefact manifests with optional `run_id` correlation |

### Next standards (draft targets)

- **Runtime Governance Summary Schema** — Interchange of summarized control evaluations (aligned with runtime governance summaries, not verdict replacement).
- **Governance Evidence Pack extensions** — Optional signed manifest and registry pointers.
- **Agent Action Signing Envelope** — Align with `agent_action_signatures` planning module.
- **AI Act Control Mapping Schema** — Machine-readable control ↔ evidence requirements (extends existing policy module direction).

**Adoption path:** ship JSON fixtures + validators → publish docs → gather implementer feedback → propose version bumps with migration notes.

---

## 4. MCP and tool governance integration

- Map each MCP **tool name** to a **`capability_id`** declared in capability policies.
- Record **tool invocation evidence** as digest-linked events (no raw payloads in standards JSON).
- Classify tools by **risk class** and require **delegation graph edges** for high-risk tool use.
- Support **per-tool governance policies** and **delegation chains** (`parent_delegation_id`) in graph documents.
- **Future MCP governance adapter** — optional sidecar that validates tool calls against capability policy + delegation graph before execution (out of scope for core ledger).

---

## 5. Cryptographic attestation roadmap

- **Content-addressed evidence** — Normalize on `sha256:` digest tokens (implemented in Phase 5 common utilities).
- **Signing envelopes** — Build on Phase 4 `AgentActionSigningEnvelope` planning (digest-only preimages).
- **Trace digest chains** — Align trace verification plans with `multi_agent_trace` export hashing conventions.
- **Policy snapshot IDs** — Bind evaluations to immutable policy versions (already a GovAI theme).
- **Verification plans** — Shipped schema for structured human/tool-assisted verification.
- **Transparency log (Rekor-style)** — Future public append-only publication of pack digests (research; not shipped in core service by default).
- **Key management** — Document enterprise HSM/KMS models separately; avoid implying GovAI operates keys without explicit deployment mode.
- **Enterprise signing model** — Separate keys for operators vs tenants vs agents; require documented trust assumptions.

---

## 6. AI Act and legal governance roadmap

- **High-risk AI controls** — Map to explicit evidence requirements in policy modules (existing YAML direction).
- **Prohibited practices guardrails** — Represent as capability classes (`PROHIBITED`) and enforcement hooks in policy, not hard-coded in engine core.
- **Transparency obligations** — Export-oriented docs and evidence packs as machine-readable disclosure artefacts.
- **Human oversight evidence** — Link approvals and overrides to control references in evidence packs.
- **Data governance evidence** — Dataset lineage digests already appear in runtime governance contexts; keep standards digest-first.
- **Post-market monitoring** — Evidence pack series over time keyed by `run_id` and release identifiers.
- **Audit package exports** — Governance evidence pack standard is a building block for “what shipped with which digests”.
- **Legal defensibility** — Always pair technical artefacts with legal review; Phase 5 standards are **not** legal opinions.

---

## 7. Commercialization strategy

- **Open-source credibility** — Deterministic validators, examples, and transparent non-goals.
- **Hosted SaaS** — Operator-managed pilots today; standards reduce onboarding friction for enterprise integrations.
- **Enterprise control plane** — Delegation + capability policies as configuration artefacts.
- **Compliance reporting** — Evidence packs as customer deliverables.
- **AI Act readiness assessment** — Services that measure evidence completeness; not “compliance guarantees”.
- **Vendor risk assessment** — Third-party MCP/tool risk captured in capability policies.
- **Audit export tooling** — CLI + CI gates + standards validators as a unified story.
- **Professional services** — Mapping customer org structure into delegation graphs and capability taxonomies.
- **Certification / assurance** — Partner-led assurance programs referencing GovAI artefacts (no self-certification claims).

---

## 8. Product packaging (editions)

| Edition | Users | Features | Monetization | Governance boundary |
|---------|-------|----------|--------------|---------------------|
| **Community** | Developers | Core OSS, examples, standards CLI | Sponsorship / OSS | Self-hosted only |
| **Team** | Product teams | Hosted pilots, CI integration | Seat-based or usage | Operator-managed tenants |
| **Enterprise** | Regulated industry | SSO, higher limits, audit support | Contract | Customer policy modules |
| **Regulated Enterprise** | High-risk AI operators | Dedicated deployments, stronger logging evidence | Custom | Legal + security review |
| **Research / Academic** | Labs | Early schemas, datasets, citations | Grants | Non-production semantics |

---

## 9. Five-year vision

1. **Year 1** — Widespread developer adoption; first workshop papers; standards validators in CI.
2. **Year 2** — Enterprise pilots; initial delegation/capability interop with partner IdPs and agent frameworks.
3. **Year 3** — Ecosystem integrations (MCP marketplaces, GRC exports); partner assurance templates.
4. **Year 4** — Regulated-market expansion with explicit key management and transparency log pilots.
5. **Year 5** — Reference **de facto** interchange formats for AI governance control planes (competitive neutrality via open standards).

---

## 10. Competitive positioning

| Category | Typical focus | GovAI differentiation |
|----------|---------------|------------------------|
| Model monitoring | Metrics/drift | **Decision-level evidence** and promotion gating |
| MLOps | Pipelines/artifacts | **Fail-closed** policy + digest-linked CI |
| GRC | Control libraries | **Runtime** + **execution** evidence, not spreadsheets only |
| AI security | Prompt injection / guardrails | **Multi-agent traceability** + delegation accountability |
| Policy documentation | Text policies | **Machine-readable** schemas + validators |

Cross-cutting: **cryptographic attribution** and **AI Act mapping** live adjacent to policy modules, not as unverifiable marketing claims.

---

## 11. Risk register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Legal overclaim | Loss of trust / liability | NO-GO rules; partner legal review for customer packs |
| Weak evaluation | Research not credible | Public datasets + reproducible harnesses |
| Integration complexity | Low adoption | Examples + CLI + narrow schemas |
| Long enterprise sales | Revenue delay | Pilot playbook + standards-based PoCs |
| Standards friction | Forking / fragmentation | Versioned schemas + explicit compatibility promises |
| Key management mistakes | False security | Document KMS models; ship digest-first only until signing is production-ready |
| Governance fatigue | Teams bypass gates | Shadow mode + incremental enforcement |
| OSS sustainability | Maintenance drain | Hosted tier + enterprise funding |

---

## 12. Execution plan

- **Next 30 days** — Stabilize schema versions from pilot feedback; expand examples; blog-style “how to map MCP tools”.
- **Next 90 days** — Reference integrations with one agent framework + one CI template; workshop submission prep.
- **Next 6 months** — Second schema revision if needed; evidence pack linking to export JSON documented end-to-end.
- **Next 12 months** — Partner assurance pack; expanded cryptographic roadmap with test vectors.

---

## 13. Success metrics

- GitHub stars/forks; PyPI downloads for `aigov-py`
- CI integrations using validators
- Hosted tenants / pilot customers
- Publications and citations
- Standards adoption (external repos importing JSON shapes)
- Revenue (hosted + enterprise)
- Count of governance evidence packs produced in pilots

---

## 14. Phase 5 NO-GO conditions

- **No empirical security claims** without reproducible experiments and a threat model.
- **No AI Act “compliance” claims** without qualified legal review for the specific deployment context.
- **No enforcement guarantees** without tests tied to explicit operator configuration.
- **No cryptographic guarantees** without a documented key and trust model.
- **No enterprise readiness claims** without operator runbooks and support commitments.

---

## 15. Implementation pointer (this repository)

Phase 5 **ecosystem standards implementation** ships:

- Python package: `aigov_py.standards` (`common`, per-standard modules, `cli`)
- Examples: `examples/standards/*.valid.json`
- Tests: `python/tests/test_phase5_standards_*.py`
- Report: `docs/reports/repo-debt-audit-and-cleanup.md`

This is **real implementation** (validators + digests + CLI + tests), explicitly **not** documentation-only, and **does not** change runtime enforcement, database migrations, persistence, ledger writes, compliance summary semantics, tenant identity derivation, or billing.
