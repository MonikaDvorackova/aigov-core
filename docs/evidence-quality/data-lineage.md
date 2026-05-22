# Data lineage

Lineage is expressed as **`lineage_edges`** from upstream dataset identifiers plus a controlled **`relation`** vocabulary (`derived_from`, `merged_with`, `copied_from`, `sampled_from`, `aggregated_from`). Transformations list **`id`**, **`kind`**, and **`code_reference`** (for example a git commit pinned path) so automation can verify structural completeness without executing pipelines.

## Why structured edges

Graph-style edges keep risk heuristics explainable: missing parents or ambiguous relations increase the advisory risk index in the scorer while remaining separate from audit enforcement.

## Limitations

This repository does not execute external data pipelines; validators check **shape and referential discipline** only.
