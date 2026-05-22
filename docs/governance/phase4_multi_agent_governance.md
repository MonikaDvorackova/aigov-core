# Phase 4: Multi-agent and autonomous governance (foundation)

**Status:** **Stabilized foundation + consolidated roadmap.** Phase 4 has **shipped helper/metadata milestones (M1–M3)** and **planning-only helper milestones (M4–M7)**. **Nothing in Phase 4 changes runtime enforcement** or verdict semantics; M3 is **shadow-only telemetry**.

## M1–M7 milestone status (consolidated)

| Milestone | Status | Category | What it adds | Where it shows up | What it does **not** do |
|-----------|--------|----------|--------------|-------------------|--------------------------|
| **M1 agent identity metadata** | **Shipped** | Metadata | Optional **`agent_context`** (`agent_id`, `principal_id`, `delegation_id`, `capability_id`) validated and echoed | `POST /v1/runtime/evaluate` response; `runtime_decision.payload.governance_enrichment.agent_context`; `governance_summary.agent_context` | No authentication, no authorization, no registry, no tenant derivation changes, no persistence, no compliance-summary changes |
| **M2 delegation reference metadata** | **Shipped** | Metadata | Optional **`delegation_context`** (`delegation_id` required when present and optional reference fields) validated and echoed | `POST /v1/runtime/evaluate` response; `runtime_decision.payload.governance_enrichment.delegation_context`; `governance_summary.delegation_context` | No graph validation, no storage, no enforcement |
| **M3 capability shadow checks** | **Shipped** | Shadow-only telemetry | Advisory consistency checks comparing declared capability and delegated capability refs | `governance_summary.advisory_control_evaluations` (e.g. `GOVAI.AGENT.*`, `source: capability_shadow`) | No verdict coupling, no merged `control_evaluations`, no blocking |
| **M4 multi-agent trace export planning** | **Planning-only** | Offline helper | Deterministic ordering, digest chain, and **`trace_digest`** over canonical JSON **refs-only** trace | Python helpers (offline); documentation in `multi_agent_traceability.md` | No runtime trace store, no API routes, no ledger/persistence |
| **M5 autonomous action governance planning** | **Planning-only** | Offline helper | Deterministic autonomy policy/decision metadata for **`capability_id`** only; stop/kill/checkpoint semantics | Python helpers (offline); documentation in `autonomous_action_governance.md` | No runtime enforcement, no persistence, no tenant stop/kill hooks |
| **M6 agent action signature planning** | **Planning-only** | Offline helper | Canonical preimage definition and signature envelope shape for agent-attributed events | Documentation in `multi_agent_traceability.md`; helper in `python/aigov_py/agent_action_signatures.py` | No real key binding, no signature generation/verification in runtime, no enforcement |
| **M7 multi-agent trace verification planning** | **Planning-only** | Offline helper | Verification steps for digest chains, planned signature envelopes, and policy snapshot pinning | Documentation in `multi_agent_traceability.md`; helper in `python/aigov_py/multi_agent_trace_verification.py` | No persisted traces, no verification gates in prod runtime |

## Clear boundaries (Phase 4)

- **Implemented (shipped):** **M1–M3** metadata and advisory-only rows on **`POST /v1/runtime/evaluate`**.
- **Planning only:** **M4–M7** offline Python composition helpers and documentation of future formats and verification steps.
- **Shadow only (telemetry):** **M3** emits **advisory** controls under **`governance_summary.advisory_control_evaluations`** with **`source: capability_shadow`**.
- **Not enforcement yet:** delegation validation, capability allow/deny, autonomous action blocks, signature verification, persisted trace store, and kill-switch runtime hooks.

## Integration map (current wiring vs planned)

This section names the integration surfaces used by Phase 4 artifacts so operators know **where to look** and what is **safe to trust** today.

### Runtime (implemented)

- **Runtime evaluate metadata:** `POST /v1/runtime/evaluate`
  - Accepts optional `agent_context` (M1) and `delegation_context` (M2).
  - Emits **advisory** capability rows (M3) under `governance_summary.advisory_control_evaluations` only.
- **`governance_summary`** carries normalized copies of `agent_context`, `delegation_context`, and advisory evaluations for downstream tooling.
- **`advisory_control_evaluations`** is a shadow-only evaluation list and must not be treated as an allow/deny source.

### Offline helpers (planning-only)

- **Trace export helpers (M4):** deterministic assembly of a refs-only `MultiAgentTrace` with digest chaining.
- **Autonomous action governance helpers (M5):** deterministic autonomy policy/decision metadata for `capability_id` only.
- **Signature planning helpers (M6):** canonical serialization and signature envelope shape for future signing.
- **Trace verification planning helpers (M7):** step-by-step verification plan for digest chains and future signatures.

## Operator notes (strict)

- **No new env vars** introduced by **M1–M7** beyond what existed before these milestones shipped.
- **No DB migrations**, **no persistence changes**, **no tenant identity changes**.
- **No production enforcement changes:** no deny/allow changes, no verdict coupling, no runtime kill-switch hooks in this phase.

## Objectives

1. **Agent identity model** — `agent_identity.md`
2. **Delegation graph model** — `agent_delegation_graph.md`
3. **Agent capability policies** — `agent_capability_policies.md`
4. **Multi-agent decision trace schema** — `multi_agent_traceability.md`
5. **Cross-agent approval and override semantics** — distributed across delegation, capability, and trace docs; human overrides remain aligned with `overrides.md`
6. **Agent-to-agent accountability** — `agent_identity.md`, `multi_agent_traceability.md`, `autonomous_action_governance.md`
7. **Autonomous action governance** — `autonomous_action_governance.md`
8. **Research and product roadmap** — this document, §Research directions, and `docs/reports/repo-debt-audit-and-cleanup.md`

## Identifier summary

| ID | Purpose |
|----|---------|
| **`agent_id`** | Governed software actor. |
| **`principal_id`** | IAM subject (human, service, or agent-as-principal). |
| **`delegation_id`** | Specific delegation grant edge in the graph. |
| **`capability_id`** | Versioned class of action under policy. |

## Cross-cutting guarantees (design intent)

- **Replayable traces** with **`policy_snapshot_id`** and optional **hash chains** and **signatures**.
- **Separation of duties** between agents via **SoD rules** on **`capability_id`** pairs and workflow scope.
- **Cryptographically attributable** actions for agents (keys bound to **`agent_id`**).
- **Emergency stop and kill switch** layered so autonomous systems cannot silently disable safety.

## EU AI Act and enterprise alignment

Foundation documents map concepts to **logging (Art. 12)**, **risk management and oversight**, and **documentation** expectations. Detailed requirement IDs continue to live in **`aiact_requirements.v1.yaml`** and **`aiact_mappings.v1.yaml`**; future phases add **explicit control mappings** for multi-agent artifacts (trace signing, delegation registry).

## Product roadmap (high level)

| Milestone | Deliverable |
|-----------|-------------|
| **M1 (evaluate metadata)** | **Shipped:** optional **`agent_context`** (`agent_id`, `principal_id`, `delegation_id`, `capability_id`) validated and echoed on **`POST /v1/runtime/evaluate`** and mirrored under **`payload.governance_enrichment.agent_context`** on **`runtime_decision`** (**metadata only**). |
| **M2 (delegation reference metadata)** | **Shipped:** optional **`delegation_context`** (`delegation_id` required when present; optional chain, participant, capability, scope, and expiry strings) validated and echoed on **`POST /v1/runtime/evaluate`** and mirrored under **`payload.governance_enrichment.delegation_context`** (**metadata only**; **no** graph persistence). |
| **M3 (capability shadow checks)** | **Shipped:** advisory **`advisory_control_evaluations`** for capability declaration vs delegation-edge metadata (**shadow-only**; does not merge into **`control_evaluations`** or change **`verdict`**). |
| **M4 (trace export planning)** | **Planning-only:** Python helpers for deterministic **`MultiAgentTrace`** construction — ordered events, per-event digest chain, and **`trace_digest`** over canonical preimage (**refs only**; **no** prompts or raw payloads). **No** runtime enforcement, **no** DB migrations, **no** new persistence, **`GET /compliance-summary`** unchanged. |
| **M5 (autonomous action governance planning)** | **Planning-only:** formal **`AutonomyLevel`**, **`AutonomousActionPolicy`**, **`AutonomousActionDecision`**, **`StopControlState`**, **`KillSwitchState`**, and **`HumanCheckpointRequirement`** in **`autonomous_action_governance.py`**. **No** runtime enforcement or storage. |
| **M6 (signature planning)** | **Planning-only:** canonical preimage and signature envelope definitions for future attribution. **No** key registry binding, no runtime signing, no verification. |
| **M7 (trace verification planning)** | **Planning-only:** deterministic verification steps for digest chains and signature envelopes when present. **No** persisted traces, no verification gate in runtime. |
| **M8** | Real signature verification: public-key registry binding, verification routines, and audit outputs. |
| **M9** | Persisted multi-agent traces: storage, retention, redaction, and export. |
| **M10** | Delegation graph validation: DAG, depth, revocation cascade, and policy-bound edge constraints. |
| **M11** | Capability enforcement: deny/allow coupling and SoD checks; staged rollout from shadow to enforce. |
| **M12** | Autonomous action enforcement: stop/kill gating wired into tool gateways and approval chain enforcement. |
| **M13** | Emergency stop and kill-switch runtime hooks: tenant stop and platform kill switch with runbooks and audit trails. |

## Risk register (Phase 4 focus)

| Risk | Failure mode | Consequence | Current posture (M1–M7) | Mitigations / future milestone |
|------|--------------|-------------|--------------------------|--------------------------------|
| **Raw content leakage** | Traces and exports include prompts, datasets, or sensitive payloads | Privacy and security breach | **Refs-only design intent**; no persisted trace store in M4 | Redaction pipeline and allowlist schemas (M9) |
| **False attribution** | Client-asserted `agent_id` treated as truth | Wrong actor blamed or trusted | **Explicitly non-authenticated** metadata (M1) | Agent registry, key binding, and verification (M8) |
| **Over-trusting shadow checks** | Operators interpret advisory controls as enforcement | Unsafe decisions | M3 rows are **advisory only** | Clear UI and operator docs; enforce only after M11 |
| **Delegation escalation** | Delegation chains exceed intended scope | Privilege creep | No graph validation (M2 is refs only) | Graph validation, depth limits, and revocation cascade (M10) |
| **Missing kill switch** | Autonomous agents cannot be stopped quickly | Increased incident blast radius | M5 is planning-only | Runtime hooks, runbooks, and audit (M13) |
| **Tenant leakage** | Cross-tenant trace correlation or identifier reuse | Data isolation breach | No persistence added; tenant identity unchanged | Tenant-scoped storage, export scoping, and tests (M9) |

## Research directions

- **Formal verification** of delegation graphs (bounded depth, no privilege escalation).
- **Consensus** among agents without cycles violating SoD (blockchain and CRDT analogues).
- **Standardization** of **`capability_id`** taxonomies with **MCP** tool ecosystems.
- **Redacted replay** for privacy-preserving forensics (zero-knowledge proofs of policy compliance — exploratory).

## Document index

| Topic | File |
|-------|------|
| Identity and keys | `agent_identity.md` |
| Delegation | `agent_delegation_graph.md` |
| Capabilities and SoD | `agent_capability_policies.md` |
| Traces and signatures | `multi_agent_traceability.md` |
| Autonomy and kill switch | `autonomous_action_governance.md` |
| Phase 4 report | `../reports/repo-debt-audit-and-cleanup.md` |
| M4 trace export planning report | `../reports/repo-debt-audit-and-cleanup.md` |
| M5 autonomous action report | `../reports/repo-debt-audit-and-cleanup.md` |
| M6 signature planning report | `../reports/repo-debt-audit-and-cleanup.md` |
| M7 trace verification report | `../reports/repo-debt-audit-and-cleanup.md` |
| Phase 5 ecosystem standards (interchange) | `../standards/README.md`, `phase5_research_and_ecosystem.md` |
