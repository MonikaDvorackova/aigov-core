# Epistemic model

This document defines vocabulary for **Knowledge Preservation Architecture** as applied to GovAI Core, and **critiques** that direction. It is written for principal-level architecture review: precise definitions first, adversarial analysis second.

Companion (directional): [knowledge-preservation-layer.md](knowledge-preservation-layer.md).  
Implemented today: append-only ledger, projection, verdicts, export/replay ([governance-semantics.md](governance-semantics.md)).

---

## 1. What is knowledge?

### Engineering definition

**Knowledge** (in this model) is **structured information that remains sufficient to re-derive a justified conclusion under a stated rule set, without access to the original runtime that produced the conclusion.**

Knowledge is not raw volume. It is **justificatory closure**: an auditor (human or program) can answer *why was this outcome warranted?* from retained artifacts alone.

Formally, let:

- `R` = a rule set (policy, schema, replay function) fixed at decision time or recoverable from artifacts
- `A` = a finite set of retained artifacts
- `π` = a deterministic reconstruction procedure

`A` constitutes **knowledge** for conclusion `C` iff `π(R, A) → C` and independent re-execution of `π` by a third party yields `C` with integrity checks passing.

If `π` requires live database state, undisclosed credentials, or privileged memory of operators, `A` is **not** knowledge — it is an index into opaque state.

### Distinctions

| Term | Definition | Typical store | Epistemic status |
|------|------------|---------------|------------------|
| **Data** | Undifferentiated bytes or records without interpretive contract | S3 blobs, log lines, CSV exports | Inert until schema + rules exist |
| **Evidence** | Data **asserted** under a typed contract (`event_type`, `payload` schema) and accepted into a integrity-bound log | GovAI `EvidenceEvent` in hash-chained JSONL | Candidate knowledge; not yet a conclusion |
| **State** | Materialized current view of a system (mutable, optimized for reads) | Postgres rows, K8s desired state, feature flags | **Anti-knowledge** for historical justification unless snapshotted and bound |
| **Telemetry** | Observations of runtime behavior (often high-volume, sampled, lossy) | OpenTelemetry spans, Prometheus metrics, LLM trace UI | Operational signal; rarely justificatory |
| **Knowledge** | Evidence + rules + bindings sufficient for `π` to reproduce a warranted conclusion | Signed export + policy digest + replay | Target artifact class |

**Example (distributed systems):** A Kubernetes `Deployment` YAML is **data**. The etcd revision history plus admission webhook decisions could be **evidence** if append-only and typed. The current pod list is **state**. kube-apiserver audit logs are **telemetry** unless schema-bound to authorization decisions. A signed bundle containing policy version, admission results, and image digests that replays to “deploy allowed” is **knowledge**.

**Example (AI):** A chat transcript is **telemetry/data**. A recorded `human_approved` event with approver id, policy version, and evaluation digest bound in a hash chain is **evidence** toward **governance knowledge**.

---

## 2. What is Decision Knowledge?

### Definition

**Decision Knowledge** is the minimal retained artifact set that allows reconstruction of:

1. **What** decision was recorded (outcome enum and parameters)
2. **Under which rules** it was evaluated (policy identity and version)
3. **From which evidence** the rules fired (event set or digest-bound references)
4. **With which authority** binding actions were attributed (actors, delegation, allowlists)
5. **With what integrity** the record can be trusted (hashes, signatures, chain continuity)

Decision Knowledge is **decision-relative**: it exists for a specific `decision_id` / `run_id` and a specific decision class (for GovAI Core today: **promotion eligibility** — `VALID` / `INVALID` / `BLOCKED`).

### What must survive (years-later reconstruction)

| Must survive | Rationale |
|--------------|-----------|
| Immutable event sequence (or digest with retrievable content) | Without inputs, `π` has nothing to apply |
| Policy version + content or cryptographic digest with retrievable policy artifact | Rules drift; “we used whatever was live” is not reconstructable |
| Decision outcome + structured reason codes | The conclusion itself |
| Authority attribution on binding events | “Who approved” cannot be invented later |
| Integrity bindings (chain head, export digests, optional signatures) | Otherwise tampering is indistinguishable from truth |
| Clock claims as **asserted** timestamps, not trusted wall time | NTP disputes are common in disputes |

### What need not survive (for GovAI’s decision class)

| Need not survive | Rationale |
|------------------|-----------|
| Full prompt and completion text | Not part of eligibility verdict in current `policy.rs` |
| Model weights | Identifiers (`model_version_id`) may suffice |
| All tool calls | Unless policy explicitly requires them as evidence codes |
| Operator dashboard screenshots | Derivative, non-canonical |

**Concrete gap in current Core:** `aigov.audit_export.v1` is a strong **Decision Knowledge carrier** for eligibility, but **policy file bytes** are not always embedded in the export — only `policy_version`. Years later, reconstruction requires a separate policy archive. That is a continuity break (see §5).

---

## 3. What is Governance Knowledge?

### Definition

**Governance Knowledge** is Decision Knowledge where the decision class is **organizational permission**: whether an entity (model, system, deployment, delegation) was **eligible** for an action under institutional rules.

GovAI Core’s implemented slice is **governance eligibility knowledge**: ledger → projection → verdict.

### Contrasts

| Category | Subject matter | Typical questions | GovAI Core today |
|----------|----------------|-------------------|----------------|
| **Governance knowledge** | Permission, duty, approval, policy conformance | “Were we allowed to promote?” | **Primary** |
| **System knowledge** | Infrastructure topology, config, dependencies | “What was running in prod?” | Partial via identifiers in events; not full CMDB |
| **Model knowledge** | Capabilities, limitations, training data claims | “What could the model do?” | Only if asserted in evidence payloads |
| **Operational knowledge** | Incidents, latency, errors, on-call actions | “What broke when?” | `ai_decision_audit` telemetry; non-authoritative |

**Governance knowledge is not a superset.** A complete system snapshot (system knowledge) does not imply governance knowledge: you may know every pod image digest and still lack a hash-chained approval for promotion.

**Model knowledge is not governance knowledge.** Knowing training data statistics does not establish who authorized deployment.

**Operational knowledge can contradict governance knowledge without invalidating the ledger.** Traces may show an agent “succeeded” while compliance summary is `BLOCKED`. That tension is architecturally intentional: operations observe behavior; governance records permission.

---

## 4. What is reconstructability?

### Formal definition

A decision `D` is **reconstructable** at time `t₂` with respect to rule set `R` if there exists artifact set `A` retained from decision time `t₁` and procedure `π` such that:

1. `π(R, A) = D'` where `D'` is decision-equivalent to `D` under a published equivalence relation `≡`
2. Integrity checks `I(A) = ok` (hash chain, signatures, digest match)
3. `π` is **public** (specified algorithm, implementable by third parties — GovAI replay engine direction)
4. No secret runtime state `S` is required with `S ∉ A`

**Reconstructability is lost** when any of:

| Failure | Example |
|---------|---------|
| **Completeness loss** | Events never ingested; only inferred from logs |
| **Rule loss** | Policy version referenced but artifact destroyed |
| **Authority loss** | Approval recorded without actor or forged actor string |
| **Binding loss** | CI digest not linked to ledger `events_content_sha256` |
| **Integrity loss** | Chain broken; export tampered |
| **Semantic drift** | `π` changed without version bump; old exports fail replay for social reasons not technical |
| **Equivalence ambiguity** | `≡` undefined — “same decision” disputed |

### GovAI Core today

Reconstructability is **partially implemented** for eligibility:

- `replay_audit_export_v1` + `verdict_match` implements `π` for export-shaped `A`
- `GET /compliance-summary` implements live `π` from ledger

Reconstructability is **not claimed** for model behavior or business outcomes.

---

## 5. What is Knowledge Continuity?

### Definition

**Knowledge Continuity** holds when every link in the justificatory chain from evidence → policy → authority → context bindings → verdict is **present, integrity-verified, and resolvable** at reconstruction time.

Continuity is a **chain property**, not a scalar quality.

### What breaks continuity

| Break | Mechanism | Example |
|-------|-----------|---------|
| **Missing approval rationale** | Event records `approve` without payload fields required by policy | `human_approved` with empty justification when policy expects it |
| **Missing authority provenance** | Actor string present but no link to IdP, delegation, or allowlist proof | `actor: "alice"` with no corroboration |
| **Missing dependency snapshot** | Identifiers reference artifacts not digested or archived | `model_version_id` points to deleted artifact store |
| **Missing policy version** | Export cites `policy_version` but policy blob unavailable | Replay uses wrong rules silently if fallback defaults apply — **catastrophic** |
| **Broken digest bridge** | CI artifact hash not in export | Cannot connect pipeline to ledger |
| **Lineage orphan** | `agent_delegated` child run never recorded | Graph integrity `invalid` in `governance_graph.rs` |
| **Unsigned attachment** | Bundle references unsigned dependency | Verifier flags `unsigned_dependency_detected` |

GovAI’s signed bundle path explicitly surfaces some breaks; others remain **organizational** (policy archive discipline).

---

## 6. What is Knowledge Coverage?

### Definition

**Knowledge Coverage** measures how much of a declared **Knowledge Requirement set** `K = {k₁…kₙ}` is satisfied by artifact set `A` at time `t₁`.

Coverage is **not** verdict. A run may be `VALID` with low coverage for long-term epistemic goals, or `BLOCKED` with high coverage for post-mortem analysis.

### Measurement

Let each requirement `kᵢ` be boolean or weighted.

```
coverage(A) = |{ kᵢ ∈ K : satisfied(kᵢ, A) }| / |K|
```

Prefer **structured reporting** over a single float:

| Dimension | Example requirements |
|-----------|---------------------|
| **Evidence** | Required event types present; discovery-driven codes satisfied (today: `EvidenceRequirements`) |
| **Policy** | Version resolvable; digest matches; rules retrievable |
| **Authority** | Approver on allowlist; delegation chain complete |
| **Integrity** | Chain verify ok; export digest match; signature valid |
| **Context binding** | Model/dataset identifiers resolvable to archived artifacts |
| **Temporal** | Ordered events; no impossible timestamps relative to policy |
| **Lineage** | Graph integrity `ok`; no orphaned delegations |

**Anti-pattern:** collapsing coverage into `VALID`. That confuses permission with epistemic completeness.

---

## 7. What is Reconstruction Confidence?

### Definition

**Reconstruction Confidence** is a **derived, non-authoritative** assessment of how likely an independent party is to successfully execute `π(R, A)` and accept `D' ≡ D` **without extrinsic assumptions**.

Unlike verdict, confidence can be graded: `{high, medium, low, none}`.

### Increases confidence

- `verdict_match == true` on replay
- Full event list in export (not digest-only with lost content)
- Policy artifact bundled or content-addressed and present
- Ed25519 signature verified with trusted key rotation documented
- Lineage integrity `ok`
- Independent CI digest matches `events_content_sha256`
- Multiple redundant carriers (ledger + signed bundle + immutable store anchor)

### Decreases confidence

- Digest-only export; content held by single custodian
- Policy version without retrievable policy
- Actor strings without identity binding
- Unsigned dependencies in bundle
- Replay warnings in `ReplayValidationReport`
- Known semantic drift between replay code versions
- Selective event ingestion (only success path reported)

### Derivation (sketch)

```
confidence = f(
  integrity_ok,
  coverage_vector,
  verdict_match,
  lineage_status,
  external_binding_count,
  policy_resolvable,
  replay_warnings
)
```

GovAI should **never** gate promotion on `confidence` alone unless policy explicitly maps it — otherwise operators optimize the score, not truth.

---

## 8. What is Epistemic Readiness?

### Definition

**Epistemic Readiness** is the property that a system (or a specific `run_id`) has preserved enough Decision Knowledge to support **future investigation, challenge, and reconstruction** — independent of whether the system is allowed to operate **now**.

### Operational readiness ≠ epistemic readiness

| Scenario | Operational | Epistemic |
|----------|-------------|-----------|
| Model serves traffic with low latency | Ready | — |
| Promotion `VALID`, policy file archived, signed export stored | Ready | **Ready** |
| Promotion `VALID`, policy version string only, events in ledger | Ready | **Unready** (policy continuity break) |
| `BLOCKED` for missing evaluation, full trace + export for post-mortem | Not promotion-ready | **Partially ready** for investigation |
| Agent demo with no evidence ingest | May “work” | **Unready** |
| Replay passes but unsigned external report required for rationale | Deployed | **Low readiness** for dispute |

**Example:** A team ships after `VALID` from CI gate. Two years later, legal asks why a model was approved. Ledger exists; policy JSON from that quarter was deleted. Operationally the ship was valid; epistemically the organization is **unready** — reconstructability is lost at the policy link.

---

## 9. Native Knowledge Graph

### Question

Should GovAI evolve from **event log + projection** toward an explicit **knowledge graph** (nodes: actors, policies, artifacts, decisions; edges: authorized-by, derived-from, supersedes)?

### Potential benefits

| Benefit | Mechanism |
|---------|-----------|
| Cross-run queries | “Which deployments depended on dataset X?” |
| Delegation visualization | Already partial in `governance_graph.rs` |
| Impact analysis | Policy change blast radius |
| Continuity analysis | Graph algorithms detect orphan authority edges |
| Unified export | Single navigable artifact for auditors |

### Risks

| Risk | Why it matters |
|------|----------------|
| **Dual write** | Graph derived from ledger is fine; authoritative graph written separately is a second source of truth |
| **Materialization drift** | Graph DB state diverges from ledger unless purely derived |
| **Scope creep** | Becomes CMDB + observability + GRC warehouse |
| **False completeness** | Rich graph implies knowledge; edges without evidence are fiction |
| **Query ≠ justify** | Graph traversal answers “what connected to what,” not “why permitted” without `π` |
| **Cost and ops** | Neo4j in the governance path invites availability coupling |

### Recommendation (architectural, not product)

Treat the graph as a **derived view** of evidence + policy, like projection today — not a new write path. GovAI already projects `GovernanceGraphDocument`; extending that is lower risk than a native mutable knowledge graph store.

A **native knowledge graph architecture** is justified only if cross-run analytic queries become a first-class requirement **and** every edge is backed by digest-linked evidence. Otherwise it is visualization on event sourcing.

---

## 10. Critique of the proposal

Assume **Knowledge Preservation Architecture is wrong** until proven otherwise. Below: attacks on whether this is a **distinct category** or **rebranded event sourcing + audit**.

### 10.1 Conceptual flaws

**1. “Knowledge” is doing moral work.**  
Renaming “audit trail” to “knowledge” suggests epistemic completeness the system cannot deliver. GovAI records **assertions**, not facts. A forged `human_approved` event is valid knowledge under `π` but false in the world.

**2. Decision Knowledge conflates permission with understanding.**  
Reconstructing `VALID` ≠ reconstructing **why the model is safe**. Eligibility replay answers a workflow question, not a scientific one.

**3. Epistemic Readiness duplicates records management.**  
Policy archives, artifact retention, and WORM storage are **information governance** problems dressed in AI vocabulary. The architecture may be a checklist for things competent compliance teams already do.

**4. Reconstruction Confidence invites gaming.**  
Any scored epistemology becomes a metric to optimize. Teams will maximize confidence without maximizing truth (bundle padding, low-value evidence events).

**5. The hypothesis is unfalsifiable without defining decision class.**  
“Critical AI system decisions” is unbounded. Without scope, the proposal expands until it equals “store everything forever.”

### 10.2 Implementation risks

| Risk | Detail |
|------|--------|
| **Schema explosion** | `DecisionKnowledge`, `KnowledgeRequirement`, etc. become parallel contract surface to export v1 |
| **Double projection** | Coverage + verdict + confidence triples deterministic logic paths |
| **Policy embedding size** | Bundling full policy in every export may be prohibitive |
| **Version skew** | Replay code v2028 on export v2024 — confidence collapses |
| **Client burden** | If knowledge requirements grow, ingest becomes heavy; teams skip Core |

### 10.3 Overlap with observability

OpenTelemetry, Langfuse, Phoenix, Weights & Biases already preserve **traces** with causality and retention policies.

**Attack:** Knowledge Preservation duplicates trace retention with worse ergonomics for engineers and no advantage unless narrowly scoped to **authorization replay**.

**Defense (weak):** Traces are not typically hash-chained, policy-bound, or verdict-replayable. Overlap is real at the “we logged something” layer; distinction exists only if **π** is public and integrity-bound.

**Verdict:** Distinct only in the **governance eligibility** niche — not in general AI observability.

### 10.4 Overlap with event sourcing

GovAI Core **is** event sourcing:

- Events = `EvidenceEvent`
- Aggregate = `run_id`
- Projection = `ComplianceCurrentState`
- Snapshot = audit export

**Attack:** Knowledge Preservation Architecture adds vocabulary around what Martin Fowler’s event-sourcing literature already describes: events, projections, snapshots, replay.

**Defense:** Commercial event-sourcing frameworks rarely ship **policy-versioned eligibility verdicts** and **signed offline replay packs** as defaults.

**Verdict:** Not a new paradigm — a **domain-specific event-sourced compliance kernel**. The proposal is valuable if it names the domain precisely; it is rebranding if sold as novel CS.

### 10.5 Overlap with provenance (W3C PROV, in-toto, SLSA)

Supply-chain provenance already models entities, activities, agents, and bundles.

**Attack:** `AuthorityProvenance` and signed bundles reinvent in-toto/SLSA attestations with a custom schema.

**Defense:** ML governance lifecycle (human approval, risk review, promotion gates) is not identical to build provenance.

**Verdict:** Interoperate or embed PROV/in-toto — otherwise duplicate an ecosystem fighting for adoption.

### 10.6 Overlap with governance frameworks

ISO 42001, NIST AI RMF, EU AI Act documentation expectations — all require **records**.

**Attack:** Knowledge Preservation is **control framework documentation** automated into software — not architecture.

**Defense:** Automation of replay beats paper binders if `π` is real.

**Verdict:** The **mechanism** (replay) may be distinctive; the **goal** (records) is not.

### 10.7 Is this a genuinely distinct architectural category?

| Criterion | Distinct? |
|-----------|-----------|
| New storage primitive | **No** — append-only log exists |
| New computation model | **No** — deterministic projection/replay |
| New trust model | **Partial** — hash chain + signed export is stronger than typical traces |
| New problem domain | **Yes, narrowly** — **eligibility justification** for AI lifecycle promotion |
| New epistemology | **No** — applied epistemology for audit |

**Ruthless conclusion:**

Knowledge Preservation Architecture is **not** a new category comparable to microservices or stream processing. It is a **well-scoped refinement** of event-sourced governance for AI promotion decisions, with explicit epistemic vocabulary.

It becomes **harmful rebranding** if it:

- Claims to preserve “model knowledge” or “decision understanding”
- Implies observability replacement
- Promises legal reconstructability without policy/artifact discipline
- Introduces confidence scores that compete with verdicts

It remains **worth building** if it:

- Names continuity breaks (policy archive, authority binding)
- Separates `VALID` from epistemic readiness
- Keeps `π` public and integrity-checked
- Stays out of prompt/token capture

GovAI Core’s honest positioning in engineering terms:

> **An event-sourced, policy-versioned, replayable eligibility ledger for AI lifecycle promotion — not a knowledge graph of AI cognition.**

---

## References (internal)

| Topic | Document |
|-------|----------|
| Runtime implementation | [../epistemic-readiness.md](../epistemic-readiness.md) |
| Current direction | [knowledge-preservation-layer.md](knowledge-preservation-layer.md) |
| Verdict semantics | [governance-semantics.md](governance-semantics.md) |
| Ledger | [append-only-ledger-semantics.md](append-only-ledger-semantics.md) |
| Platform boundary | [platform-vs-core-boundary.md](platform-vs-core-boundary.md) |
