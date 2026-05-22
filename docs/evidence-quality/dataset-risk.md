# Dataset risk heuristics

**Risk level** summarizes lineage and retention stress using deterministic arithmetic on integer subscores. It is intentionally coarse (`low`, `medium`, `high`) so dashboards and PR comments can reason about posture without implying legal certification.

## What increases risk

- Lower provenance scores (for example partial checksum coverage across sources).
- Lower lineage scores when edges or transformation references are incomplete.
- Lower retention scores when classification or day counts are invalid, or legal hold lacks a policy reference.
- Missing `quality_metrics.documented_limitations` boolean truth increases the risk numerator slightly to encourage explicit limitation statements.

## What risk does not do

Risk heuristics **do not** change billing, ledgers, database migrations, or runtime enforcement semantics for the audit service.
