# # Multi-agent decision traceability (Phase 4 foundation)

**Status:** architectural foundation plus **Phase 4 M1** optional **`agent_context`**, **M2** optional **`delegation_context`**, and **M3** advisory capability shadow rows (**`governance_summary.advisory_control_evaluations`**, **`source: capability_shadow`**) on **`POST /v1/runtime/evaluate`** (additive metadata echoed to **`runtime_decision`** enrichment). **Phase 4 M4** adds **offline export planning** in Python (`aigov_py.multi_agent_trace`): deterministic ordering (**`sequence_number`**, then **`event_id`**), per-event digest chain, and a top-level **`trace_digest`** over canonical JSON (**excluding** **`trace_digest`** itself). This layer is **refs-only** (identifiers, digests, correlation ids) — **no** prompts, raw datasets, or payload bodies in the model; **no** runtime trace store and **no** ledger writes in M4.

This document participates in the **Phase 4 M1–M7** foundation set. For consolidated status/boundaries/integration mapping and forward roadmap, see **`phase4_multi_agent_governance.md`**.

Replay signing, **`prev_event_hash`** at the HTTP transport layer, deterministic **`inputs_hash`** / **`outputs_hash`** for raw payloads, and **persisted** multi-agent trace storage remain **future** work beyond M4 planning.

## Phase 4 M6 — agent action signature planning (offline)

**Goal:** define a stable **signature envelope** and canonical **preimage** for agent-attributed events so M8 can implement real signing and verification without revisiting field semantics.

**Planning constraints (M6):**

- **No key registry**, no key binding to `agent_id`, no cryptographic enforcement.
- **No runtime signing** and **no verification gates**.
- Signature planning is compatible with **refs-only** traces: the preimage MUST NOT require raw prompts, datasets, or request bodies.

**Envelope shape (planned fields):**

- `signature_alg` (e.g. `ed25519`, `p256-sha256` — exact set defined at implementation)
- `key_id` (public key identifier within an agent registry; future)
- `signed_at` (UTC RFC3339)
- `signature_b64` (detached signature over canonical preimage)
- `preimage_digest` (digest of canonical preimage to support external indexing)

**Canonical preimage (planned):**

- Deterministic JSON including: `trace_id`, `event_id`, `sequence_number`, `timestamp`, `agent_id`, `principal_id` (when applicable), `delegation_id`, `capability_id`, `policy_snapshot_id`, `inputs_hash`, `outputs_hash`, `prev_event_hash`.
- Explicitly excludes: raw payloads, free-form text content, and any mutable transport metadata.

## Phase 4 M7 — multi-agent trace verification planning (offline)

**Goal:** define deterministic verification steps for a refs-only trace so operators and future automated gates can detect tampering and attribution failures.

**Verification steps (planned):**

1. **Schema + ordering**: validate required fields; recompute total ordering by `(sequence_number, event_id)` and ensure it matches the stored order.
2. **Digest chain**: recompute each `prev_event_hash` link and validate the terminal `trace_digest`.
3. **Policy pinning**: ensure each event references a `policy_snapshot_id` and that the snapshot set is consistent with the replay context.
4. **Signature envelope (when present)**: for events with signatures, recompute canonical preimage digest and verify signature using `agent_id` → public keys (registry is future).
5. **Cross-reference runtime metadata**: where an event is derived from `POST /v1/runtime/evaluate`, confirm `agent_context`/`delegation_context` and advisory rows are consistent with the event refs (telemetry-only, non-enforcing).

**Non-goals (M7):** no persisted trace store, no production enforcement, and no blocking runtime gate.

## Purpose

Define **replayable multi-agent execution traces**: ordered, verifiable records of **decisions**, **delegations**, **tool invocations**, and **approvals** so operators can **reconstruct why** an outcome occurred and **detect tampering**.

## Trace identity

- **`trace_id`:** Unique identifier for one **end-to-end** governed run (workflow instance, request orchestration, or batch job).
- **`span_id` / `parent_span_id`:** Optional hierarchical subdivision (aligned with common observability conventions) for nested agent calls.

## Event record (schema sketch)

Each **immutable event** in the trace SHOULD include:

| Field | Description |
|-------|-------------|
| **`event_id`** | Monotonic or ULID within **`trace_id`**. |
| **`timestamp`** | UTC, from a **single clock policy** per tenant. |
| **`agent_id`** | Acting agent when applicable. **M1:** MAY appear via evaluate **`agent_context`** (opaque client string; echoed in **`governance_summary`** + ledger enrichment). |
| **`principal_id`** | IAM subject when distinct (e.g. human approval). **M1:** MAY appear via **`agent_context`** (same caveat). |
| **`delegation_id`** | Active delegation governing the step, if any. **M1:** MAY appear via **`agent_context`**. **M2:** SHOULD use **`delegation_context.delegation_id`** when attaching explicit delegation-edge metadata (**`parent_delegation_id`**, **`delegator_agent_id`**, **`delegatee_agent_id`**, etc.). |
| **`capability_id`** | Action class. **M1:** MAY appear via **`agent_context`**. **M2:** MAY appear as **`delegation_context.delegated_capability_id`** when modeling the delegated capability on an edge. **M3:** Optional shadow advisory controls (**`GOVAI.AGENT.*`**) compare these fields for consistency; outcomes are under **`governance_summary.advisory_control_evaluations`** only (see **`agent_capability_policies.md`**). |
| **`inputs_hash`** | Cryptographic hash of canonicalized inputs (privacy: may be redacted with hash of redacted form). |
| **`outputs_hash`** | Same for outputs. |
| **`policy_snapshot_id`** | Reference to **versioned** policy bundle used for the decision. |
| **`decision`** | Allow / deny / defer / escalate / complete (enum TBD at implementation). |
| **`reason_code`** | Stable code for governance explainability (align with `reason_codes.v1.yaml` where possible). |
| **`signature`** | Optional detached signature over a **canonical serialization** of the fields (see below). |
| **`prev_event_hash`** | Optional **hash chain** link to prior event in **`trace_id`** for tamper evidence. |

## Replayable multi-agent execution traces

**Replay** means: given **the same ordered events** and **the same `policy_snapshot_id`** series, a **deterministic re-evaluation** (or simulation) yields an **equivalent governance outcome** for each step.

Requirements:

1. **Total ordering** per **`trace_id`** (or per shard that is merged deterministically).
2. **No silent mutation** of stored events; corrections are **new events** (**correction** / **voiding** pattern).
3. **Policy version** pinned per decision where evaluation depends on policy.

## Cryptographically attributable agent actions

- **Attribution:** **`agent_id`** + **key identifier** used for **`signature`**.
- **Payload:** Canonical JSON or protobuf (implementation choice) excluding non-deterministic transport metadata.
- **Verification:** Verifier uses **registered public keys** for **`agent_id`** (and human signing certs if used).

### Phase 4 M6: deterministic signing envelope (planning)

For **offline planning** of detached signatures over agent actions, **`python/aigov_py/agent_action_signatures.py`** specifies a **canonical preimage**: tenant-scoped identifiers, **`policy_snapshot_id`**, normalized **`payload_digest`** (hash of canonical action material — **never** the raw payload in this model), **`signing_key_ref`**, and **`signature_algorithm`**, plus optional **`delegation_id`** and **`trace_id`** as opaque reference strings only. The helper derives a stable **`envelope_digest`** (SHA-256 hex over sorted-key canonical JSON) so future traces can align **signature metadata** with **policy and payload hashes** before any signer or verifier is wired. **No signatures are produced** and **no trace store format** is changed in M6.

## Cross-agent approval in traces

- Approval steps appear as **distinct events** with **`capability_id`** in the approve family and **`principal_id`** of the approver.
- **Deny** and **escalate** are first-class outcomes with **`reason_code`**.

## EU AI Act and enterprise mapping (high level)

- **Art. 12 (logging):** Automatic recording of events with enough **granularity** to reconstruct **major decisions** by **AI components**.
- **Audit and forensic:** Enterprise **SIEM** ingestion maps **`trace_id`** to incidents; **WORM** storage class for immutability.

## Relationship to existing audit exports

- Align terminology with **`audit_exports.md`** when implementing; this foundation **extends** the conceptual model to **multi-agent** graphs without changing current export formats in this phase.

## Phase 4 M4 — export planning (Python)

For operator tooling and future exporters, **`build_multi_agent_trace`** accepts **`tenant_id`**, **`trace_id`**, **`policy_snapshot_id`**, and a sequence of **`MultiAgentTraceEvent`** rows (with optional **`AgentTraceRef`**, **`DelegationTraceRef`**, **`CapabilityTraceRef`**). Events are sorted deterministically; **`trace_event_from_runtime_governance_context`** maps **`RuntimeGovernanceContext`** decision and correlation refs into an event shell (**planning-only** composition). **M4 does not** add HTTP APIs, enforcement, database tables, or **`compliance-summary`** changes.

## Autonomous action governance metadata (Phase 4 M5, planning)

For **autonomous** steps, traces SHOULD eventually correlate **`capability_id`** with **planning outcomes** from **`AutonomousActionPolicy`** and **`AutonomousActionDecision`** (see **`autonomous_action_governance.md`** and **`python/aigov_py/autonomous_action_governance.py`**):

- **`blocked_reason_codes`** and **`accountability_requirements`** from the planning decision are **explainability inputs** for **`reason_code`** and audit narrative (no raw action body).
- Stop and kill-switch states are **environmental facts** recorded alongside **`trace_id`** when wired in a later milestone and are not emitted by the planning helper today.

This keeps **replay** focused on **ordered, versioned policy** and **hashed inputs and outputs**, while autonomy level and approval tokens document **why** a path was or was not permitted autonomously.

## Phase 4 M7: multi-agent trace verification planning (planning-only)

This milestone introduces a **deterministic verification plan** for a multi-agent trace **without** performing real cryptographic verification.

The plan is intended to:

- Validate required identifiers (**`tenant_id`**, **`trace_id`**, **`trace_digest`**, **`policy_snapshot_id`**).
- Encode expectations for **action signing envelopes** (presence checks only; **no** signature verification).
- Encode expectations for **event digest chain references** (presence checks only; **no** chain reconstruction).
- Produce a stable **`plan_digest`** so that the same inputs always yield the same plan.

Implementation lives in **Python helper only**:

- `python/aigov_py/multi_agent_trace_verification.py`

Out of scope for M7:

- Public and private key handling, signature verification, or any cryptographic attestation beyond digest formatting checks.
- Runtime enforcement, ledger writes, persistence, or compliance-summary changes.

## Out of scope

Binary formats, retention SLAs, and PII redaction pipelines are implementation concerns.