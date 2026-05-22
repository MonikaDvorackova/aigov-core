# Auditability failures benchmark — run report (template)

## Suite

- **Suite id:** `auditability-failures`
- **Runner:** `benchmarks/auditability-failures/run_benchmark.py`
- **Date:** YYYY-MM-DD
- **Operator:** name or team

## Metadata validation

| Check | Result |
| --- | --- |
| Scenario count | 8 |
| Categories match required set | pass / fail |
| Expected results coverage | pass / fail |

## Scenario table

| Scenario id | Title | Expected primary signal (teaching) |
| --- | --- | --- |
| `missing_evidence` | Missing evidence | BLOCKED |
| `missing_approval` | Missing approval | BLOCKED |
| `invalid_evaluation` | Invalid evaluation | INVALID |
| `broken_digest_continuity` | Broken digest continuity | INVALID |
| `duplicate_event_id` | Duplicate event id | INVALID |
| `tenant_isolation_spoofing` | Tenant isolation spoofing | INVALID |
| `missing_audit_context` | Missing audit context | BLOCKED |
| `incomplete_evidence_pack` | Incomplete evidence pack | BLOCKED |

## Notes

- Signals in this template are **pedagogical** labels aligned with `expected-results.json`, not a substitute for `GET /compliance-summary` on a live service.

## Follow-ups

- Link failing CI jobs to the scenario id that best matches the `blocked_reasons` / `missing_evidence` fields returned by your deployment.
