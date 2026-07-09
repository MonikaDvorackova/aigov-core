# Multi-agent lineage

AIGov Core records **append-only evidence** for AI governance. Multi-agent lineage extends reconstructibility beyond a single `run_id` to delegated flows, cross-run parent/child relationships, and governance graphs suitable for audit replay.

## Lineage fields (evidence)

Optional fields on each evidence event (top-level or mirrored in `payload`):

| Field | Meaning |
|-------|---------|
| `parent_run_id` | Run that delegated or spawned this run |
| `root_run_id` | Top-level orchestration run (defaults to `run_id` when unset) |
| `delegated_from_event_id` | Event id in parent/root run that triggered delegation |
| `agent_id` | Agent identity for this step |
| `agent_role` | Role label (orchestrator, reviewer, tool worker, …) |
| `delegation_reason` | Human-readable reason code or text |

Semantics are **append-only**: corrections are new events, never in-place edits.

### `agent_delegated` events

Use `event_type: agent_delegated` for explicit cross-run delegation:

```json
{
  "event_id": "deleg-001",
  "event_type": "agent_delegated",
  "run_id": "run-orchestrator",
  "root_run_id": "run-orchestrator",
  "agent_id": "planner",
  "agent_role": "orchestrator",
  "delegation_reason": "specialist_review",
  "payload": {
    "child_run_id": "run-specialist",
    "parent_run_id": "run-orchestrator"
  }
}
```

Ingest the child run's events under `run_id: run-specialist` with `parent_run_id` and `delegated_from_event_id` set.

## Governance graph

From a single `aigov.audit_export.v1` document, Core projects:

- **Nodes** — runs, agents, events, tools, governance gates
- **Edges** — sequence, delegation, tool execution, approval/evaluation gates
- **Integrity** — cycles, orphans, missing parents, inconsistent `root_run_id`

Export includes a backward-compatible `lineage` block (extra field; schema_version remains `aigov.audit_export.v1`).

## Replay and lineage validation

`govai replay-audit-export` continues to validate schema v1, hash chain, and verdict projection. When lineage is present, replay also reports lineage validation issues (cycles, orphans, missing parent runs in export scope).

Lineage validation **warnings** for `parent_run_id` not present in the same export are expected for multi-export reconstructions.

## CLI

```bash
govai lineage-graph --path export.json
govai lineage-graph --path export.json --json
govai lineage-graph --path export.json --mermaid > graph.mmd
```

Offline binary: `lineage_graph_once` (same logic as CLI).

## Reconstructible agent systems

A reconstructible multi-agent system must:

1. Assign stable `run_id` per agent invocation scope
2. Emit `agent_delegated` (or equivalent lineage fields) when spawning sub-agents
3. Record tool calls with `tool_call` events and `agent_id`
4. Record `evaluation_reported` and `human_approved` on the correct run scope
5. Export each run (or a combined audit trail) for offline graph and replay tooling

## Difference from distributed tracing

| Concern | Distributed tracing (OTel) | GovAI lineage |
|---------|---------------------------|---------------|
| Primary goal | Latency, request flow | Governance verdicts and evidence |
| Authority | Trace backend | Append-only ledger |
| Mutability | Ephemeral spans | Immutable events |
| Legal replay | Secondary | Primary (`replay-audit-export`, graph) |

You may correlate `external_trace` (W3C `traceparent`) with lineage fields; they do not replace ledger evidence.

## Why governance lineage matters

- Proves **which agent** acted under **which policy** at each step
- Surfaces **hidden sub-agents** when parent/child runs are linked
- Supports **approval inheritance** visibility across delegation chains
- Enables **deterministic** offline audit without proprietary dashboards

## Limitations

- Single-export graphs do not resolve parent runs that were not exported (warnings only)
- No built-in graph UI — use `--mermaid` or external tools
- Agent identity is operator-supplied metadata unless bound by separate identity integrations
- Cross-tenant lineage is not inferred automatically; tenant scope follows API key mapping per run
