# Governance semantics (formal)

This document defines **deterministic, technically defensible** governance semantics for AIGov Core. It extends the concise [trust-model.md](../trust-model.md) with lifecycle, integrity, and export vocabulary suitable for architecture and security review.

## Authoritative decision surface

The **only authoritative compliance verdict** for a `run_id` is:

`GET /compliance-summary?run_id=<id>`

Consumers (CLI, CI, dashboard widgets, workflow UIs, copied JSON) must treat that response as the decision source. Everything else is derivative or operational overlay.

## Compliance verdict enum

| Verdict | Definition | Typical projection signals | CI / promotion meaning |
|---------|------------|----------------------------|-------------------------|
| **VALID** | Policy version evaluated; no required evidence missing; decisive policy rules satisfied | Empty `missing_evidence`; no blocking `blocked_reasons` | Gate may allow promotion when your policy requires `VALID` |
| **INVALID** | Enough evidence to evaluate at least one decisive rule; a rule fails (for example evaluation not passed) | Failed evaluation or policy finding with evidence present | Reject; rework and new evidence on a new or updated run |
| **BLOCKED** | Run not eligible for `VALID` under current policy | Non-empty `missing_evidence` and/or `blocked_reasons`; approval or promotion prerequisites unmet | Halt until eligibility is restored |

**Fail-closed rule:** Absence of evidence or integrity failure does **not** imply success. Unmet prerequisites surface as **BLOCKED**, not as implicit `VALID`.

**Non-claims:** `VALID` is **process compliance** for the recorded evidence and `policy_version`. It is not outcome correctness, safety certification, or legal conformity.

## Governance state vs workflow state

| Layer | Storage | Purpose |
|-------|---------|---------|
| **Governance state (authoritative)** | Immutable ledger + derived projection in compliance summary | Eligibility for promotion per policy |
| **Workflow state (Platform)** | Postgres `compliance_workflow` | Team-scoped operational queue (register, approve/reject) |

Workflow transitions **must be reconciled** with the compliance summary. Platform APIs expose `decision_authority` on successful workflow calls to mark when workflow action does not override the ledger projection ([strong-core-contract-note.md](../strong-core-contract-note.md)).

## Evidence integrity

### Append-only ledger

Accepted events are appended to `audit_log.jsonl` with hash chaining (`prev_hash` → `record_hash`). Properties:

- **Tamper detection:** Altering or removing a middle record breaks `GET /verify` / `GET /verify-log`
- **Not completeness:** Integrity does not prove all relevant real-world events were submitted
- **Reject duplicates:** Policy and schema reject invalid or duplicate ingest attempts before append

See [append-only-ledger-semantics.md](append-only-ledger-semantics.md).

### Bundle and digest continuity

| Artefact | Role |
|----------|------|
| `GET /bundle` | Canonical bundle document derived from ledger events |
| `GET /bundle-hash` | `bundle_sha256`, `events_content_sha256` for CI artefact binding |
| Evidence pack (offline) | Customer-held export with manifest and digests |

**Digest continuity:** Exported artefact hashes must match ledger-derived digests. Mismatch is a **security-relevant** failure (replay failure, verify failure), not a soft warning.

## Reconstructibility and audit replay

**Reconstructibility:** Given a retained ledger slice or export for a `run_id`, any party can re-derive bundle, projection, and compliance verdict with the same `policy_version`.

**Audit replay (offline):** Load exported bundle → verify manifest and digests → reconstruct evidence state → reproduce verdict. Replay **succeeds** only when verdict matches recorded state and integrity checks pass. See [diagrams/audit_replay_architecture.md](diagrams/audit_replay_architecture.md).

Replay proves **consistency of the export with stated policy**, not that the export was the only copy ever held.

## Chain of custody (operator and customer roles)

| Stage | Custodian | Record |
|-------|-----------|--------|
| Event submission | Integrator (CI, runtime, CLI) | `POST /evidence` acceptance or rejection |
| Ledger authority | Core runtime operator | Append-only log per tenant |
| Export handoff | Customer or auditor | `GET /api/export/:run_id`, evidence packs |
| Independent verification | Auditor or second system | `govai verify-evidence-pack`, replay CLI |

GovAI records **what was accepted** into the ledger. Strong identity of human actors requires your IdP and submission controls outside Core unless you bind authenticated actors in evidence events explicitly.

## Event classes (governance execution)

| Event category | Examples | Affects verdict |
|----------------|----------|-----------------|
| **Policy evaluation** | Evaluation passed/failed, capability checks | `INVALID` or `VALID` when evidence complete |
| **Human approval** | Approval recorded, promotion allowed/blocked | `BLOCKED` until prerequisites met |
| **Discovery-derived requirements** | `ai_discovery_reported` → additional required evidence | `BLOCKED` until satisfied |
| **Artifact binding** | Model/dataset/version identifiers, digests | Integrity and eligibility |

Human approval events are **evidence facts**, not a separate verdict channel.

## Trace export semantics

**Decision trace** (portable standard) interchange describes multi-step agent or tool graphs for **offline** validation and partner exchange ([../standards/interchange-specification.md](../standards/interchange-specification.md)). Binding a trace to a run requires explicit evidence events and ledger history; interchange validation alone does not imply a hosted `VALID`.

**Runtime evaluate (`POST /v1/runtime/evaluate`, preview):** May surface advisory overlays. Advisory output is **not** a replacement for compliance-summary verdicts ([../runtime/overview.md](../runtime/overview.md)).

## Retention and limitations

| Topic | GovAI provides | Operator / customer provides |
|-------|----------------|------------------------------|
| Ledger retention duration | Configurable storage; documented expectations in [../security/data-handling.md](../security/data-handling.md) | Backup policy, legal hold, deletion after contract |
| Export retention | Export API semantics | Long-term archive in customer GRC or WORM storage |
| Right to be forgotten | Not automatic on ledger | Process design for run_id lifecycle (operational) |

## Determinism statement

For fixed inputs (ledger events for `run_id`, `policy_version`, schema versions), compliance summary fields and verdict are **reproducible**. Non-determinism in your pipelines (floating evaluation, external policy drift without version bump) is outside Core guarantees.

## Related documents

- [governance-execution-flow.md](governance-execution-flow.md)
- [policy-evaluation-lifecycle.md](policy-evaluation-lifecycle.md)
- [evidence-lifecycle.md](evidence-lifecycle.md)
- [decision-trace-lifecycle.md](decision-trace-lifecycle.md)
