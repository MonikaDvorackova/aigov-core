# Auditability failures benchmark (metadata suite)

## Purpose

Provide a **stable vocabulary** of auditability failure modes for docs, training, and CI metadata validation. The runner checks JSON shape and alignment between **`scenarios.json`** and **`expected-results.json`**.

## Scenarios covered

| ID | Theme |
| --- | --- |
| `missing_evidence` | Required artefacts absent from the evidence chain |
| `missing_approval` | Policy expects human or role approval that was never recorded |
| `invalid_evaluation` | Evaluation payload fails structural or policy validation |
| `broken_digest_continuity` | Digest chain does not match prior events |
| `duplicate_event_id` | Replayed or colliding event identifiers |
| `tenant_isolation_spoofing` | Cross-tenant references or mismatched tenant context |
| `missing_audit_context` | Required audit fields (actor, timestamp scope, correlation) absent |
| `incomplete_evidence_pack` | Pack export cannot be assembled without gaps |

## Files

- **`scenarios.json`** — scenario definitions (sorted keys in file for readability).
- **`expected-results.json`** — expected primary signal per scenario for teaching narratives.
- **`run_benchmark.py`** — stdlib validator (no network).
- **`report-template.md`** — human-readable report skeleton after a conceptual evaluation run.

## Safety

The script only reads files next to it and exits with a non-zero status on validation failure. No subprocess calls to Docker, `curl`, or cloud CLIs.
