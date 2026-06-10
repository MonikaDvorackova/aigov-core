# GovAI Evidence Lifecycle (diagram)

Narrative and state model: [../evidence-lifecycle.md](../evidence-lifecycle.md). Enterprise hub: [../README.md](../README.md).

This diagram describes how evidence moves through GovAI from collection to replay.

## Flow

1. A developer, CI workflow, or runtime system produces governance-relevant activity.

2. GovAI collects evidence from:
- discovery outputs
- evaluation results
- human approvals
- promotion events
- artifact digests
- runtime context
- policy results

3. Evidence is normalized into structured audit events.

4. Audit events are written to the audit ledger.

5. Evidence bundles are exported for verification or audit review.

6. Digest continuity links exported artifacts to recorded audit events.

7. The compliance gate evaluates the evidence state.

8. GovAI returns one of three verdicts:
- VALID
- INVALID
- BLOCKED

9. Exported evidence can be replayed later to verify the decision.

## Text diagram

Source activity
  ->
Evidence collection
  ->
Structured audit events
  ->
Audit ledger
  ->
Evidence bundle export
  ->
Digest continuity verification
  ->
Governance verdict
  ->
Replay verification

## Verdict behavior

VALID:
Required evidence is present, evaluation passed, approvals are satisfied, and artifact continuity is intact.

INVALID:
Evidence exists, but evaluation or policy checks failed.

BLOCKED:
Required evidence, approval, audit context, or integrity guarantees are missing.

## Design principle

GovAI treats missing governance evidence as BLOCKED, not as success.
