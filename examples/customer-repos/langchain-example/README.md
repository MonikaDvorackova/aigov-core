# GovAI + LangChain-style agents (example customer pattern)

## Target user

Application teams orchestrating **tool-using agents** who need traceable governance over tool policies, model versions, and release decisions.

## Scenario

An agent stack (LangChain, LangGraph, or similar) runs in staging with constrained tools. Before production enablement, the team records:

- Tool allowlist version and policy digest.
- Red-team or safety evaluation summary for the agent graph.
- Maintainer approval for expanded tool permissions.

## Architecture

```text
Agent runtime (staging)
  -> evaluation / red-team harness
  -> evidence emission (tool policy digest, eval outcomes)
  -> GovAI audit API
  -> compliance summary gates production routing flip
```

## How GovAI is used

- Captures **decision-level** events: what configuration is approved, by whom, under which policy version.
- Prevents “shadow” production deployments when **`GET /compliance-summary`** is not **`VALID`** for the candidate **`run_id`**.

## Expected evidence pack flow

1. Emit events for graph version, tool manifest digest, and evaluation completion.
2. Attach human approval where your policy mandates human-in-the-loop for elevated risk tools.
3. Export the evidence pack for security review questionnaires alongside **`GET /api/export/:run_id`**.

## Compliance gate narrative

**“Agents do not gain production privileges without evidence that evaluations and approvals match the declared policy.”** Missing audit context or incomplete packs keeps the verdict from **`VALID`**.

## Commands (pseudo-commands)

```bash
export RUN_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
govai emit --run-id "$RUN_ID" --event-type evaluation_completed --payload @agent_eval.json
govai emit --run-id "$RUN_ID" --event-type approval_recorded --payload @maintainer_approval.json
govai check --run-id "$RUN_ID"
```

## Non-goals

- No LangChain code samples in-repo; integrate using your application’s HTTP client or the **`govai`** CLI.
- GovAI is not an agent memory store or observability backend — it is the **governance verdict and audit ledger** surface.
