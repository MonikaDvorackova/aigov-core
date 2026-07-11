---
name: Governance RFC
about: Propose a governance, CI gate, or contributor-policy change for AIGov Core
title: "[RFC-GOV] "
labels: governance
assignees: ""
---

## Problem statement

What policy friction or risk are we addressing?

## Proposal

Describe the change at a level maintainers can evaluate (scope, defaults, migration for contributors).

## Alternatives considered

What other policies or mechanisms did you evaluate?

## Impact on core invariants

- [ ] Does **not** weaken append-only ledger semantics.
- [ ] Does **not** weaken tenant isolation (`GOVAI_API_KEYS` + `GOVAI_API_KEYS_JSON`; `X-GovAI-Project` remains metadata only).
- [ ] Does **not** make `GET /ready` mutating.
- [ ] Does **not** bypass ledger-authoritative `GET /compliance-summary` verdict derivation.
- [ ] Does **not** remove or weaken existing CI governance gates without maintainer approval.

## Auditability

- [ ] Identifies whether a new **`docs/reports/*.md`** audit file is required (see **`docs/community/rfc-process.md`**).

## Rollout plan

How will you communicate to contributors (`README.md`, `CONTRIBUTING.md`, `docs/community/*`)?

## Additional context

Links to prior issues, diagrams, or external standards (non-binding references).
