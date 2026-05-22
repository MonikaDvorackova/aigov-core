# Reference: AI Act–style workflow (evidence + policy)

This folder summarizes how teams **use GovAI alongside** EU AI Act programs. GovAI is **governance infrastructure**, not a law firm in a box.

## Start here

1. **Narrative workflow** — `docs/examples/ai-act-compliance-workflow.md`
2. **Policy modules** — `docs/customer-policy-modules.md`, `docs/policies/`
3. **Evidence pack concepts** — `docs/evidence-pack.md`
4. **Standards interchange** (portable JSON) — `docs/standards/interchange-specification.md`

## Practical pattern

- Legal/compliance defines **classification** and **obligations**.
- Engineering maps obligations to **required evidence types** in a **static policy module**.
- GovAI enforces **completeness** and **ordering** at **ingest** and exposes **one verdict** via **`GET /compliance-summary`**.

## What to tell auditors

- Show **append-only** evidence history and **export** JSON for a specific **`run_id`**.
- Explain **BLOCKED** vs **INVALID** using server fields (`blocked_reasons`, evaluation outcome).
- Clarify that **validators** on portable JSON are **not** a substitute for **ledger** proofs unless bound to hosted history.

## Related examples in repo

- `examples/blocked_deployment.sh` — fail-closed demonstration
- `docs/demo/golden-run/` — golden path narrative
