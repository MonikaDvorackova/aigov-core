# Retention policy fields

Snapshots include a **`retention`** object with **`classification`** (`public`, `internal`, `confidential`, or `restricted`), an integer **`retention_days`** between 1 and 36500, and a boolean **`legal_hold`**. When `legal_hold` is true, **`policy_reference`** must be a non-empty string pointing to the governing retention policy document or ticket.

## Interaction with scoring

The retention dimension contributes to the composite evidence quality score and to the lineage risk heuristic. Missing or inconsistent retention metadata reduces scores predictably so operators can prioritize remediation.

## Non-goals

These fields do not trigger automatic deletion jobs or cloud storage lifecycle changes inside GovAI.
