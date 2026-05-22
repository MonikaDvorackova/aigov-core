# GovAI Runtime Governance Flow

This diagram describes how GovAI supports runtime governance.

## Flow

1. A runtime system requests governance evaluation.

2. Runtime context is collected.

3. Evidence is attached to the request.

4. Policies are evaluated against the runtime context.

5. Required approvals and evidence continuity are checked.

6. A governance verdict is returned.

7. The runtime system allows, rejects, or blocks the operation.

## Text diagram

Runtime system
  ->
Runtime governance request
  ->
Context and evidence collection
  ->
Policy evaluation
  ->
Approval and evidence checks
  ->
Governance verdict
  ->
Runtime allow / reject / block

## Runtime verdicts

VALID:
The runtime operation may proceed.

INVALID:
The runtime operation fails policy or evaluation checks.

BLOCKED:
The runtime operation lacks required governance evidence or approval.

## Design principle

Runtime governance must preserve the same fail-closed semantics as CI governance.
