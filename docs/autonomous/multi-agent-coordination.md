# Multi-agent coordination

Multi-agent setups add **coordination** concerns on top of single-agent autonomy: shared state, delegation graphs between agent instances, and approval gateways that may fire mid-workflow.

## Reference sample

See [`../../examples/autonomous/sample-multi-agent-coordination.json`](../../examples/autonomous/sample-multi-agent-coordination.json) for a minimal graph:

- `coordination_model` — for example `supervisor-worker`.
- `agents` — instances with `agent_id` and `role_ref` pointing at [`../../autonomous/role-models.json`](../../autonomous/role-models.json).
- `delegation_graph` — directed capability assignments between agents.
- `approval_gateways` — steps where `requires_human` is mandatory before further autonomous progress.
- `shared_state_policy` — concurrency strategy label (for example `pessimistic_lock`).

## Relationship to agent governance

The agent governance package under [`../agent-governance/`](../agent-governance/) focuses on delegation snapshots and scoring. Use this autonomous bundle for **limits and intervention wiring**, and the agent governance artefacts for **delegation risk** reviews — together they form a layered narrative without duplicating verdict logic.
