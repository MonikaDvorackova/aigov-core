# GovAI + GitHub Actions (example customer pattern)

## Target user

Platform or DevSecOps engineers who want **deterministic CI gates** tied to a hosted or self-hosted GovAI audit service.

## Scenario

Every pull request that touches governed artefacts (policy files, evidence manifests, promotion scripts) runs a workflow that:

1. Emits or refreshes evidence for a `run_id`.
2. Calls **`GET /compliance-summary`** (or the **`govai check`** CLI equivalent).
3. Fails the job unless the verdict is **`VALID`** (per your policy).

## Architecture

```text
GitHub Actions job
  -> build / test / lint
  -> govai CLI or curl (evidence POST + summary GET)
  -> GovAI audit API (append-only ledger, tenant-scoped)
  -> compliance verdict (VALID / INVALID / BLOCKED)
```

## How GovAI is used

- **Evidence-first**: training, evaluation, approval, and promotion events are recorded before deployment is allowed.
- **Fail-closed**: missing prerequisites surface as **`BLOCKED`** with machine-readable reasons — not silent green builds.

Canonical integration notes live in [`docs/github-action.md`](../../docs/github-action.md) and the published composite action under **`.github/actions/govai-check/`**.

## Expected evidence pack flow

1. Pipeline generates artefacts (logs, digests, evaluation summaries).
2. Evidence pack JSON (or equivalent bundle references) is attached to the run.
3. Human or automated approval step records an explicit approval event when policy requires it.
4. **`GET /api/export/:run_id`** (or repository tooling) materialises the audit bundle for archival.

## Compliance gate narrative

The merge gate answers: **“Is this change supported by complete, consistent evidence under the active policy version?”** If digest continuity breaks, required evaluations are invalid, or approvals are missing, the gate stays **closed** until remediation.

## Commands (pseudo-commands)

```bash
# After configuring GOVAI_* env vars to match your operator deployment:
govai emit --run-id "$RUN_ID" --event-type training_completed --payload @training.json
govai check --run-id "$RUN_ID"
# CI: exit non-zero when check does not report VALID
```

## Non-goals

- This README does not vendor a full reusable workflow YAML for every language stack; copy patterns from **`examples/ci/`** and adapt.
