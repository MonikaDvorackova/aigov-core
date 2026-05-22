# Agent accountability

Accountability ties **agent identities** to **human or organisational owners** who answer for outcomes, data handling, and retention.

## Practices

- **Owner registry**: each agent id maps to a service account, team, and escalation path.
- **Artefact export**: decision traces and delegation edges exportable for audits (`decision_artifacts_exported` in snapshots).
- **Retention acknowledgement**: operators confirm records meet policy (`retention_policy_acknowledged`).

## Auditability linkage

The auditability block in delegation snapshots is intentionally small: correlation coverage, export flags, edge logging, and retention acknowledgement. Expand in your own control plane; the schema version can increment when you do.
