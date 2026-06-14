# Release engineering examples (stdlib drivers)

These scripts exercise the **changelog validator**, **release notes generator**, and **readiness report** without network access. Run from the **repository root**.

| Script | Purpose |
|--------|---------|
| [`run-changelog-validation.sh`](run-changelog-validation.sh) | `validate_changelog.py --json` |
| [`run-release-notes-generation.sh`](run-release-notes-generation.sh) | `generate_release_notes.py` sample output |
| [`run-release-readiness-report.sh`](run-release-readiness-report.sh) | `release_readiness_report.py --json` |

Makefile equivalents: **`make validate-changelog`**, **`make generate-release-notes`**, **`make release-readiness-report`**, and the aggregate **`make release-readiness-check`**.

See also **[sample-release-plan.json](sample-release-plan.json)** and the machine-readable index **[../../docs/releases/release-manifest.json](../../docs/releases/release-manifest.json)**.
