---
title: Runtime governance roadmap (future, docs-only)
audience: customers, operators
scope: docs-only
status: roadmap
---

## Not implemented yet

This document is a **design note** only.

It does **not** add:

- new verdicts
- new backend logic
- schema changes
- runtime monitoring implementation

---

## Why runtime governance

GovAI should evolve from a deployment-time CI gate into a deterministic governance execution layer that supports lifecycle decisions such as:

- may this model be deployed?
- may this model remain active?
- must this model be re-reviewed?
- must this model be disabled?

The core design principle remains the same:

**evidence events + static policy requirements → flat required evidence → deterministic verdict**

---

## Future evidence events (concepts)

These are proposed evidence event concepts that could be recorded in the append-only ledger in a future iteration:

- `drift_detected`
- `incident_reported`
- `model_disabled`
- `revalidation_completed`
- `runtime_monitoring_enabled`

These names are placeholders for discussion and must not be treated as implemented APIs.

---

## Future decision timeline concept

A future “decision timeline” (for auditability and operator clarity) could structure a run’s lifecycle as explicit, ordered milestones:

- `discovery_completed`
- `policy_requirements_derived`
- `evidence_submitted`
- `missing_evidence_detected`
- `human_approval_recorded`
- `verdict_emitted`

Purpose:

- make decisions explainable without changing semantics
- align CI-time and runtime decisions to the same evidence-first model

