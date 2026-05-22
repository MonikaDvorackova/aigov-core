# Agent delegation graph (Phase 4 foundation)

**Status:** planning and architecture only. No graph storage or runtime enforcement in this phase.

This document participates in the **Phase 4 M1–M7** foundation set. For consolidated status/boundaries/integration mapping and forward roadmap, see **`phase4_multi_agent_governance.md`**.

## Purpose

Model how authority flows between humans and agents so that **multi-step automation** remains **explainable**, **bounded**, and **revocable**. The delegation structure is a **directed graph** (typically acyclic in the authority layer; cycles may exist only if explicitly allowed for peer coordination and flagged for review).

## Graph model

- **Nodes:** **`principal_id`** values (humans, service accounts, **registered agents** identified by **`agent_id`**).
- **Edges:** Each edge is a **delegation** identified by **`delegation_id`** with attributes:
  - **Grantor** (`principal_id`) and **grantee** (`principal_id` or **`agent_id`** mapped to principal).
  - **Granted `capability_id` set** (or references to policy bundles).
  - **Valid from / valid until** (time-bounded grants).
  - **Scope:** tenant, environment (`prod` / `staging`), resource patterns, max monetary or rate limits (product-defined).
  - **Parent `delegation_id`** (optional): supports **delegation chains** without flattening policy.

## Delegation chains across agents and humans

1. **Human → agent:** Operator or owner delegates a subset of capabilities to an agent (e.g. “summarize incidents,” “open ticket”).
2. **Agent → agent:** **Upstream agent** delegates to **downstream agent** only if **human-originated or policy-originated** root delegation exists and **SoD rules** allow the pair (see `agent_capability_policies.md`).
3. **Human in the loop:** Certain **`capability_id`** values may require a **human `principal_id`** on the approval step even when intermediate steps are automated; the graph records **which human organization unit** may approve.

## Cross-agent approval and override semantics (structural)

- **Approval** on an edge means a **decision record** ties **`delegation_id`** (or request ID) to **`principal_id`** of approver — human or **approval-agent** if explicitly modeled as a **`principal_id`** with restricted **`capability_id`**.
- **Override** (break-glass) is **not** a normal delegation edge; it references a **separate override artifact** (aligned with `overrides.md`) and must **not** extend delegation without audit. Phase 4 foundation: overrides **break or supersede** a specific decision while leaving the delegation graph **unchanged** unless governance explicitly revokes a **`delegation_id`**.

## Constraints (design intent)

- **Acyclicity (default):** The **authority delegation** layer should remain a **DAG** to prevent indefinite authority recursion. Product may allow **tagged cycles** for consensus protocols only with explicit **`capability_id`** and risk review.
- **Depth limits:** Maximum chain length from human root to leaf agent prevents **unbounded autonomy creep**.
- **Revocation:** Revoking **`delegation_id`** removes the edge; downstream delegations **must** be invalidated (cascade) unless re-rooted under a new grant.

## Replay and audit

- **Replayable traces** (see `multi_agent_traceability.md`) include the **sequence of `delegation_id` references** valid at each step so historical runs can be verified.

## EU AI Act and enterprise mapping (high level)

- **Oversight and human intervention:** Explicit **human nodes** and **approval edges** in the graph document where **meaningful human oversight** applies (relevant for high-risk systems and internal TPRM).
- **Third-party AI:** External agents may appear as **`principal_id`** / **`agent_id`** with **contractual scope** modeled as **delegation** limits.

## Runtime evaluate metadata (Phase 4 M2)

**Shipped (additive only):** **`POST /v1/runtime/evaluate`** accepts optional **`delegation_context`** with **`delegation_id`** (required when the object is present) and optional **`parent_delegation_id`**, **`delegator_agent_id`**, **`delegatee_agent_id`**, **`delegated_capability_id`**, **`delegation_scope`**, **`expires_at`** (opaque RFC3339-like text; not parsed server-side in M2). Normalized values are echoed on the HTTP response and under **`runtime_decision.payload.governance_enrichment.delegation_context`** (and **`governance_summary.delegation_context`**). This records **client-asserted** delegation references for future graph traceability — **no** delegation validation, capability enforcement, or verdict coupling in M2.

## Out of scope

Storage format (graph DB vs relational), validation APIs, and enforcement at runtime are deferred.
