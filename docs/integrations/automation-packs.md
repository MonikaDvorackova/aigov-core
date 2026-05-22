# Automation packs

## Purpose

Define the **automation pack** JSON contract used by `scripts/validate_automation_pack.py` and `scripts/generate_automation_pack_summary.py`: structured commands (argv arrays) and on-disk artifacts validated for presence, not executed during validation.

## Integration overview

An automation pack lists `commands` (each with `id`, `argv`, `description`) and `artifacts` (each with `path`, `kind`, `description`). Validators ensure argv segments are non-empty strings, artifact paths exist as files under the repository root, and required top-level keys are present. CI emits **automation-pack-validation.json** and **automation-pack-summary.md**.

## Implementation steps

1. Copy `examples/integrations/sample-automation-pack.json` as a template.
2. Run `python3 scripts/validate_automation_pack.py --pack <path>` locally.
3. Generate reviewer-facing Markdown with `python3 scripts/generate_automation_pack_summary.py --pack <path>`.
4. Register the pack path in `docs/integrations/developer-integrations-manifest.json` under `automation_packs`.

## Validation

- `make automation-pack`
- `make automation-pack-summary`
- `examples/integrations/run-automation-pack-validation.sh`

## Failure modes

- **Empty argv segment** — validation fails (intentionally strict). Mitigation: trim tokens and remove blank entries.
- **Artifact path typo** — non-existent paths fail validation. Mitigation: use paths relative to repo root as stored in git.
