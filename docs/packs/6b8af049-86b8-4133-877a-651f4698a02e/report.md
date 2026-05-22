# Audit report for run `6b8af049-86b8-4133-877a-651f4698a02e`

run_id=6b8af049-86b8-4133-877a-651f4698a02e
bundle_sha256=a125dd778213445ca6fc12eb3009530629691ee6d7e0013ca4ac3a1656d9d75e
policy_version=v0.4_human_approval

## Summary

- System: `aigov_poc`
- Actor: `monika`
- Policy version: `v0.4_human_approval`
- Evidence bundle: `docs/evidence/6b8af049-86b8-4133-877a-651f4698a02e.json`
- Evidence bundle SHA256: `a125dd778213445ca6fc12eb3009530629691ee6d7e0013ca4ac3a1656d9d75e`
- Model artifact (reported): `python/artifacts/model_6b8af049-86b8-4133-877a-651f4698a02e.joblib`

## Traceability

| Item | Value |
|---|---|
| Dataset | `iris` |
| Dataset fingerprint | `523290e5e80d443207b3d2a2223ac767a9751b305d036cfe3a129e6c59921808` |
| Rows | `150` |
| Features | `4` |

## Evaluation gate

| Metric | Value | Threshold | Passed |
|---|---:|---:|---|
| `accuracy` | `0.9666666666666668` | `0.8` | `True` |

## Human approval gate

| Scope | Decision | Approver | Justification |
|---|---|---|---|
| `model_promoted` | `approve` | `compliance_officer` | `metrics meet threshold and dataset fingerprint verified` |

## Promotion

- Promotion reason: `approved_by_human`
- Artifact path: `python/artifacts/model_6b8af049-86b8-4133-877a-651f4698a02e.joblib`

## Event timeline

| Time (UTC) | Event | Event id |
|---|---|---|
| `2026-02-01T13:35:09.501589Z` | `run_started` | `bf1a8798-2da9-4a60-98fa-16ecda381798` |
| `2026-02-01T13:35:09.527333Z` | `data_registered` | `abf26ee1-5e2f-4963-b556-1ad76a526b58` |
| `2026-02-01T13:35:09.559435Z` | `model_trained` | `211fa685-c49f-4142-a649-141775a5f011` |
| `2026-02-01T13:35:09.562831Z` | `evaluation_reported` | `5a71b06f-2a1d-4acf-b23e-86b9422cb556` |
| `2026-02-01T13:35:21.437937Z` | `human_approved` | `ha_9e5fceea-0617-4551-9d23-9000b62e98f7` |
| `2026-02-01T13:35:24.410989Z` | `model_promoted` | `mp_after_approval_6b8af049-86b8-4133-877a-651f4698a02e` |

## Audit log reference

- Log path (reported by server): `rust/audit_log.jsonl`
