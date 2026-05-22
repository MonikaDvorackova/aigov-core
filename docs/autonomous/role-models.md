# Role models

Autonomous systems should assign each agent a **stable role** from the machine-readable catalogue in [`../../autonomous/role-models.json`](../../autonomous/role-models.json).

## Fields

| Field | Meaning |
| --- | --- |
| `role_id` | Stable identifier referenced by delegation graphs and coordination samples. |
| `authority_scope` | Machine-oriented label describing what the role may attempt before approval gateways apply. |
| `description` | Human-readable scope statement for operators and auditors. |

## Design rules

- **Separation of duties:** orchestration (`supervisor`) must not silently inherit execution privileges without an explicit delegation edge.
- **Narrow executors:** default executors should start in `read_only_tools` until policy and monitoring prove a broader scope.
- **Governance officer:** reserved for human or tightly controlled approval paths; not delegable from autonomous agents in the sample bundle.
