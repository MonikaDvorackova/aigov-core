# GovAI + healthcare-oriented AI (example customer pattern)

## Target user

Compliance, risk, and engineering leads building **clinical or operational decision support** where audit trails and human oversight are emphasised (for example EU AI Act high-risk posture, ISO-style QMS hooks).

## Scenario

A hospital system or vendor trains or fine-tunes a model, runs validation on curated cohorts, performs clinical safety review, and only then enables inference endpoints — with GovAI recording each milestone.

## Architecture

```text
Regulated data zone (training / eval)
  -> documented evidence artefacts (SOP version, eval protocol digest)
  -> GovAI evidence + approvals
  -> deployment to controlled inference environment
```

## How GovAI is used

- Captures **who approved what**, under which **policy version**, with references to validation artefacts.
- Supports **tenant isolation** so separate hospital networks or business units do not cross-read ledgers.

## Expected evidence pack flow

1. Record dataset governance metadata (access approvals, de-identification steps) as your policy allows and requires.
2. Attach evaluation and clinical review summaries with stable digests.
3. Export evidence packs for **procurement / diligence** alongside internal QMS records.

## Compliance gate narrative

**“No clinical or high-risk deployment without the evidence chain the policy mandates.”** Missing audit context, incomplete evidence packs, or missing human approvals should yield **`BLOCKED`** until resolved.

## Commands (pseudo-commands)

```bash
export RUN_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
govai emit --run-id "$RUN_ID" --event-type evaluation_completed --payload @clinical_eval_summary.json
govai emit --run-id "$RUN_ID" --event-type approval_recorded --payload @clinical_safety_board.json
govai check --run-id "$RUN_ID"
```

## Non-goals

- **Not** medical device certification, **not** legal advice, **not** a substitute for regulated clinical validation processes.
- No patient data, imaging samples, or real PHI — only integration patterns.
