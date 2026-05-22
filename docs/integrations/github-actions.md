# GitHub Actions integration

## Purpose

Describe how teams wire GovAI checks into GitHub Actions using repository `Makefile` targets and stdlib validators so CI fails closed on documentation gates and integration manifests without embedding secrets in workflow YAML.

## Integration overview

The OSS workflow (`.github/workflows/oss-developer-experience.yml`) runs broader enterprise checks and emits JSON or Markdown artifacts under `.oss-ci-out/`. Developer integrations checks add **developer-integrations.json**, manifest validation, automation pack validation, and **automation-pack-summary.md** for traceability. Feature branches merge to **staging** before **main**; workflows should not bypass `make gate`.

## Implementation steps

1. Checkout the repository with sufficient depth when diagnostics compare against `origin/staging`.
2. Add a step that runs `make developer-integrations-platform-check` or individual targets (`developer-integrations`, `developer-integrations-manifest`, `automation-pack`, `automation-pack-summary`, `gate`) as needed.
3. Upload `.oss-ci-out/` or equivalent paths as CI artifacts for reviewers.
4. Keep API keys in GitHub **secrets**; never echo bearer tokens in logs.

## Validation

- `make developer-integrations` and `python3 scripts/developer_integrations_check.py --json`
- `examples/integrations/sample-github-action.yml` for a minimal pattern
- `make developer-integrations-platform-check` before opening a PR that touches integrations

## Failure modes

- **Missing workflow wiring** — diagnostics fail if expected developer-integrations artifact filenames are absent from the OSS workflow file. Mitigation: copy substrings from `scripts/developer_integrations_check.py` expectations.
- **False green without gate** — skipping `make gate` allows broken audit report headings. Mitigation: always chain `gate` in aggregate targets.
