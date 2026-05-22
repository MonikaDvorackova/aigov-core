# Evidence quality gates

Phase 19 gates are **documentation and CI artefact** gates: they ensure manifests, samples, validators, Makefile targets, and OSS workflow JSON outputs stay aligned. The aggregate Makefile target is **`make evidence-quality-check`**, which chains individual targets and ends with **`make gate`** for report heading hygiene under `docs/reports/`.

## Local commands

- `python3 scripts/evidence_quality_check.py --json` — repository wiring diagnostics.
- `python3 scripts/validate_evidence_quality_manifest.py --json` — manifest validation.
- `python3 scripts/validate_dataset_provenance_snapshot.py --json` — snapshot schema validation.

## CI artefacts

The OSS developer experience workflow writes JSON and Markdown artefacts (for example `evidence-quality.json` and `dataset-governance-report.md`) into `.oss-ci-out/` for upload as build artefacts.
