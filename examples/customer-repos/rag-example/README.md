# GovAI + RAG deployment (example customer pattern)

## Target user

ML or applied AI engineers shipping **retrieval-augmented generation** into production with auditable evaluation and release decisions.

## Scenario

A team indexes documents, runs offline retrieval quality checks, performs model/reranker updates, and promotes a retrieval configuration only after **evidence-backed** sign-off.

## Architecture

```text
Data prep -> offline eval (nDCG / faithfulness harness)
  -> evidence events (eval digest, dataset fingerprint)
  -> human approval (when required)
  -> GovAI ledger + compliance summary
  -> deployment orchestrator reads verdict before rollout
```

## How GovAI is used

- Binds **evaluation artefacts** (reports, digest manifests) to a **`run_id`**.
- Surfaces **INVALID** when policy rules reject an evaluation configuration (for example stale benchmarks vs declared dataset version).
- Keeps **BLOCKED** when mandatory human steps are incomplete.

## Expected evidence pack flow

1. Record dataset and index versions with cryptographic digests where your policy requires them.
2. Attach evaluation summaries referencing the same digest chain as training or fine-tuning events, if applicable.
3. Store approval and promotion events before enabling the new retriever in production routing.

## Compliance gate narrative

The gate enforces: **“No silent promotion of a retrieval stack without verifiable evaluation evidence and approvals.”** Missing evidence or broken digest continuity prevents **`VALID`**.

## Commands (pseudo-commands)

```bash
export RUN_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
# Pseudocode: emit structured events with your CLI or HTTP client
govai emit --run-id "$RUN_ID" --event-type evaluation_completed --payload @eval_summary.json
govai emit --run-id "$RUN_ID" --event-type approval_recorded --payload @approval.json
govai check --run-id "$RUN_ID"
```

## Non-goals

- No sample corpus, embeddings, or vector database dumps in this repository.
- GovAI does not perform retrieval quality scoring by itself; it records and governs **decisions** about those scores.
