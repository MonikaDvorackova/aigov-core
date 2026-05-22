# GovAI Private Pilot Onboarding

## What you get

- CI compliance gate for one AI system or pipeline
- deterministic **VALID / INVALID / BLOCKED** decision
- audit evidence export
- GitHub Action integration
- onboarding support during pilot

## Canonical customer onboarding (hosted)

If you already have a hosted GovAI backend + API key, start with the canonical onboarding flow:

- [customer-onboarding-10min.md](customer-onboarding-10min.md)

## What you need before starting

- Python 3.11+
- GitHub repository with CI
- `GOVAI_AUDIT_BASE_URL`
- `GOVAI_API_KEY`
- `GOVAI_RUN_ID`

## Install the CLI

```bash
python -m pip install --upgrade pip
python -m pip install "aigov-py==0.2.1"
govai --help
```

## Understand `GOVAI_RUN_ID`

- identifies one evidence run
- must be identical across:
  - evidence submission
  - `govai check`
  - export
- do NOT use `github.run_id` unless explicitly mapped
- recommended:
  - commit SHA (CI)
  - UUID (manual)

Example:

```bash
export GOVAI_RUN_ID="$(python - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
```

## Add the GitHub Action

Use the GitHub Action documented here (copy/paste workflow):

- [github-action.md](github-action.md)

Evidence submission must use the same `GOVAI_RUN_ID` before this step.

## Interpret verdicts

VALID
- evidence sufficient
- CI continues

INVALID
- evidence evaluated and failed
- CI stops

BLOCKED
- missing or incomplete evidence or approvals
- CI stops

## Export audit evidence

```bash
govai export-run --run-id "$GOVAI_RUN_ID" > govai-evidence.json
```

Use for audit or internal review. This is not legal certification.

## Minimal troubleshooting

CLI not found
- cause: not installed
- action: reinstall via pip

Missing `GOVAI_AUDIT_BASE_URL`
- cause: env not set
- action: define repository variable

Mismatched `GOVAI_RUN_ID`
- cause: different values across steps
- action: unify run-id

BLOCKED result
- cause: missing evidence or approval
- action: complete evidence or workflow

Unauthorized / API key error
- cause: missing or invalid key
- action: check secrets

## Pilot success criteria

- GovAI runs in CI
- one pipeline covered
- failures block release
- export generated
- team understands VALID / INVALID / BLOCKED

## Known limitations (pilot)

- Metering is best-effort under concurrent CI runs
- usage checks and evidence append are not atomic
- parallel jobs may temporarily exceed limits or return inconsistent 429 responses
- recommended: use one GovAI run per pipeline execution or avoid parallel evidence writes
- API key request limits are separate from evidence metering
- 429 responses may come from request caps or evidence limits
- both use the same audit endpoint but are enforced independently
