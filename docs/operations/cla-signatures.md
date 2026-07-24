# CLA signature storage (`cla-signatures`)

## Purpose

The `cla-signatures` branch stores **only** Contributor License Agreement signature
records written by CLA Assistant Lite (`contributor-assistant/github-action`).

It is not used for application development, releases, or general documentation.

## Expected layout

| Path | Who creates it |
|------|----------------|
| `README.md` | Maintainers (branch bootstrap) |
| `signatures/README.md` | Maintainers (branch bootstrap) |
| `signatures/version1/cla.json` | **CLA Assistant only** on first signature — do not create manually |

## Who may write

- `github-actions[bot]` via `.github/workflows/cla.yml` (`GITHUB_TOKEN`)
- Repository maintainers for recovery only

Do **not** grant broad write bypass on protected `main` or `staging` for CLA storage.

## Workflow configuration

In `.github/workflows/cla.yml`:

```yaml
branch: cla-signatures
path-to-signatures: signatures/version1/cla.json
```

The pinned action documents that the signature branch **must not be protected**.

## Recovery if a signature write fails

1. Confirm `cla-signatures` is not covered by rulesets that require PRs or status checks.
2. Confirm the workflow `branch:` input is still `cla-signatures`.
3. Comment `recheck` on the pull request (exact phrase) or push a synchronize event.
4. Read the failed Actions job log for rule-violation details.
5. If `cla.json` was manually created incorrectly, remove it and let the action recreate it.

## Contributor-facing docs

See [`docs/community/cla.md`](../community/cla.md).
