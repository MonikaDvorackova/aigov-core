# # Agent identity model (Phase 4 foundation)

**Status:** architecture plus **Phase 4 M1 optional metadata** on **`POST /v1/runtime/evaluate`** (see below). M1 is **additive only** — it does **not** authenticate agents, authorize capabilities, enforce delegation, migrate DB columns, touch **`GET /compliance-summary`**, or change tenant resolution.

This document participates in the **Phase 4 M1–M7** foundation set. For consolidated status/boundaries/integration mapping and forward roadmap, see **`phase4_multi_agent_governance.md`**.

## Phase 4 M1: runtime audit metadata (**shipped**, additive)

**`POST /v1/runtime/evaluate`** (see `api/govai-http-v1.openapi.yaml`) accepts optional **`agent_context`** with up to four **non-empty** (after trim) opaque strings:

- **`agent_id`**
- **`principal_id`**
- **`delegation_id`**
- **`capability_id`**

Validated values are echoed in the HTTP body (**top-level **`agent_context`** and nested **`governance_summary.agent_context`**) and written to **`runtime_decision.payload.governance_enrichment.agent_context`** (same normalized JSON). Omitted **`agent_context`** / **`null`** / effectively empty object ⇒ **`null`** everywhere. Invalid empty field when the key is present ⇒ **`400`** **`VALIDATION_ERROR`**. This path records **client-asserted** identifiers for downstream multi-agent tracing only; cryptographic proof and registry binding remain future milestones (see roadmap in **`phase4_multi_agent_governance.md`**).

## Purpose

Define stable identifiers and relationships so autonomous and delegated agents can be authorized, audited, and held accountable alongside human principals and existing tenant scoping.

## Core identifiers

| Identifier | Definition | Stability |
|------------|------------|-----------|
| **`agent_id`** | Globally unique identifier for a **governed software actor** that can initiate or carry out actions (tool use, approvals, delegation) under policy. Distinct from a single HTTP request or ephemeral process PID. | Allocated at registration; rotated only through explicit lifecycle (re-key, decommission) with audit trail. |
| **`principal_id`** | **Authentication and authorization subject**: human user, service account, workload identity, or **agent acting as a first-class principal** after registration. Used in RBAC, audit logs, and approval records. | Tied to IdP or internal IAM registry; may equal **`agent_id`** when the subject is solely an agent. |
| **`delegation_id`** | Unique key for a **specific grant** of authority from one principal to another (including agent→agent). References policy scope, validity window, and parent delegation when nested. See `agent_delegation_graph.md`. | New ID per grant; revocation does not reuse IDs. |
| **`capability_id`** | **Versioned name** for an allowed action class (e.g. `govai.audit.emit`, `agent.workflow.resume`, `tool.external.http_post`). Policies attach limits to **`capability_id`**, not raw OS permissions. | Registry-defined; deprecated capabilities retain IDs for trace replay. |

## Relationships

- Every **`agent_id`** maps to exactly one **primary `principal_id`** for IAM (may be the same string if the product uses a unified namespace).
- **Humans** have **`principal_id`** and optionally linked **`agent_id`** only if modeled as bot-assisted personas; typically humans remain human **`principal_id`** only.
- **Delegation** always references **`delegation_id`** and never conflates “who acts” (**`agent_id`** / **`principal_id`**) with “what they may do” (**`capability_id`**).

## Binding to tenants and credentials

- **Tenant scope:** All identifiers are interpreted within a **tenant** (or org) boundary already used by the compliance engine; **`agent_id`** is unique within tenant unless the registry is explicitly global.
- **Credentials:** Long-lived secrets or workload JWTs are **bound** to **`principal_id`** (and thus to **`agent_id`** when applicable). Rotation updates credential metadata without changing **`agent_id`** unless the agent is decommissioned and replaced.

## Cryptographic attribution (foundation)

- Each **`agent_id`** is associated with one or more **signing keys** (asymmetric) held in a secure store; **actions intended to be non-repudiable** carry a **detached signature** over a canonical payload (see `multi_agent_traceability.md`).
- **Humans** continue to use existing IdP authentication; human approvals in chains may be represented as signed assertions or IdP-backed tokens, product-specific.

## Phase 4 M6: signing envelope planning (Python helper only)

**`python/aigov_py/agent_action_signatures.py`** defines **planning-only** dataclasses (**`AgentActionSigningEnvelope`**, **`AgentActionSignaturePlan`**, **`AgentSigningKeyRef`**, **`AgentActionDigest`**, **`SignatureVerificationExpectation`**) that describe:

- Required correlation fields: **`tenant_id`**, **`agent_id`**, **`principal_id`**, **`action_id`**, **`capability_id`**, **`policy_snapshot_id`**.
- Optional opaque refs only: **`delegation_id`**, **`trace_id`**.
- **Payload binding** via **`payload_digest`** only (**64 hex** or **`sha256:<64 hex>`**); **no raw action payload** is modeled.
- Opaque **`signing_key_ref`** plus allow-listed **`signature_algorithm`** (**`ED25519`**, **`ECDSA_P256_SHA256`**).
- Deterministic **`envelope_digest`**: SHA-256 hex over canonical JSON of the preimage **excluding** **`envelope_digest`** itself.

M6 performs **no real signing**, adds **no runtime enforcement** or API behavior, and does **not** persist keys or signatures.

## Phase 4 M7: trace verification planning (planning-only)

Phase 4 M7 adds a **planning helper** that prepares deterministic verification requirements for multi-agent traces **without** introducing a registry, key management, or real cryptographic verification.

Key points:

- The plan can require that every agent action carries a **`signing_key_ref`** and **`signature_algorithm`** field in its envelope.
- The plan may include an **`expected_signature_ref`** per action as an optional planning affordance; missing values are:
  - **WARN** when `strict_signatures=False`
  - **FAIL** when `strict_signatures=True`
- This milestone does **not** bind keys to `agent_id`, and does **not** validate signatures.

## EU AI Act and enterprise mapping (high level)

- **Art. 12 (logging)** / governance metadata: **`agent_id`** on each logged event supports identification of the automated actor.
- **Risk management and oversight:** **`principal_id`** distinguishes accountable **human** approvers from **automated** agents.
- **Enterprise IAM:** Align **`principal_id`** with corporate directory **`sub`** / **`objectId`** and service principals; **`agent_id`** maps to “AI agent” or “workflow runner” inventory records.

## Out of scope (still)

Authenticated agent registry, asymmetric key binding per **`agent_id`**, RBAC coupling of **`principal_id`** to engine authorization, delegation graph validation — **beyond M1**. M1 ledger fields mirror HTTP echo **only** as metadata; operators must not interpret them as IdP-backed truth without separate integration.

Database migrations for first-class registry storage and compliance-summary ingestion of agent identity remain **explicitly excluded** until later milestones (see **`phase4_multi_agent_governance.md`**).