# Control plane reporting

The governance control plane emits **deterministic artefacts** suitable for CI upload and human review.

## JSON outputs

- `scripts/policy_intelligence_check.py --json` — diagnostics bundle (`ok`, `score`, `checks`, `failures`, `warnings`, `checked_paths`).
- `scripts/validate_policy_intelligence_manifest.py --json` — manifest validation payload.
- `scripts/validate_governance_control_snapshot.py --json` — snapshot schema validation.
- `scripts/policy_coverage_score.py --input <snapshot> --json` — coverage, maturity, and gap scores plus findings and recommendations.

## Markdown reports

- `scripts/generate_governance_control_report.py --input <snapshot>` writes a stable Markdown narrative derived from the same scores as JSON output.

## CI

The OSS developer experience workflow copies machine-readable outputs under `.oss-ci-out/` for upload as workflow artefacts (see workflow file for exact filenames).

## Related

- [`policy-coverage.md`](policy-coverage.md)
- [`../../examples/policy-intelligence/README.md`](../../examples/policy-intelligence/README.md)
