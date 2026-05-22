# ČVUT-style teaching page (minimal)

This page is a teaching-friendly entry point for academic courses and student startups using GovAI as a verifiable CI gate and evidence ledger.

It focuses on **what can be checked mechanically** and what remains out of scope.

---

## Learning goals (what students should be able to explain)

- What `VALID`, `BLOCKED`, and `INVALID` mean **as returned by** `GET /compliance-summary`.
- What counts as “evidence” in this system (events accepted by `POST /evidence`).
- How “required evidence” is represented and why missing required evidence blocks.
- How discovery-driven requirements can change what is required for a run.
- What hash chaining gives you (tamper-evidence) and what it does not (truthfulness of inputs).

---

## Minimal lab: observe `BLOCKED → VALID` and export

### Setup

- Use the canonical onboarding flow: `docs/customer-onboarding-10min.md`
- Or use the local flow: `docs/quickstart-5min.md`

### Task A — observe the decision source

1. Run a deterministic flow that produces a `BLOCKED` verdict first.
2. Confirm the verdict is read from:
   - `GET /compliance-summary?run_id=<your run id>`
3. Append the remaining evidence for the same `run_id`.
4. Confirm the verdict becomes `VALID` by re-reading the same endpoint.

Deliverable: the final `compliance-summary` JSON (saved as a file) and a sentence stating which endpoint is authoritative.

### Task B — export a stable audit artifact

1. Export the run using:
   - `GET /api/export/<run_id>` (or `govai export-run`)
2. Identify:
   - the verdict
   - the policy metadata (`policy_version`, environment)
   - the hash fields included in the export

Deliverable: one exported JSON file suitable for archiving with a CI build.

---

## Discovery exercise (what changes when discovery signals exist)

Goal: understand how discovery can introduce **derived required evidence**.

1. Create a run that reports discovery signals (event like `ai_discovery_reported`).
2. Observe whether `required_evidence` / `missing_evidence` includes items with:
   - `source: discovery`
3. Add the newly required evidence items and observe the verdict transition (if applicable).

Discussion prompt:

- What does discovery *actually prove*?
- What failure mode exists if discovery is false-positive or false-negative?

---

## Integrity exercise (what hash chaining detects)

Goal: reason about tamper-evidence.

1. Run the server’s chain verification (`GET /verify` or `GET /verify-log`).
2. Explain, in one paragraph, what class of tampering would cause verification to fail.

Do **not** claim:

- “the evidence is true”
- “the model was deployed exactly as described”

Claim only:

- “the stored append-only chain has not been modified since it was recorded (under the chain’s integrity assumptions)”

---

## Short checklist students can use in reports

- **Decision authority**: I obtained `verdict` from `GET /compliance-summary`.
- **Evidence scope**: I can list which events were recorded for my `run_id` (bundle/export).
- **Missing evidence**: If blocked, I can name the missing requirement codes.
- **Discovery**: If discovery is enabled, I can list which requirements were derived from discovery.
- **Auditability**: I exported a stable JSON file and can point to its hashes.
- **Non-claims**: I did not claim legal compliance or truthfulness of payloads.

Students must submit (as evidence artifacts) at minimum:

All submitted artifacts must correspond to the same `run_id`.

- the final `GET /compliance-summary` JSON for the run
- the `GET /api/export/<run_id>` JSON for the run
- a list of required evidence items observed (e.g. requirement `code` values)
- Example required evidence items (policy-dependent): `evaluation_reported`, `risk_reviewed`, `human_approved`, `model_promoted`

