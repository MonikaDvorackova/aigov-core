# Actions cost optimization audit

## Scope

This report documents the GitHub Actions cost optimization changes for govai-core.

## Changes

The update removes redundant push triggers from expensive workflows and keeps pull request and manual execution paths.

Affected workflows:

- compliance.yml
- python-govai.yml
- security-scan.yml
- oss-developer-experience.yml
- supply-chain-audit.yml
- nightly-full-validation.yml

## Rationale

The previous workflow configuration consumed GitHub-hosted runner minutes on repeated pushes to integration branches. This was unnecessary because the same validation already runs on pull requests and can be started manually when needed.

Nightly full validation remains scheduled daily, but now runs on a self-hosted runner.

## Risk assessment

The change reduces duplicated CI execution without removing pull request validation.

Security and supply-chain workflows remain available on pull requests, manual dispatch, and weekly scheduled runs.

Release validation remains unchanged for version tags.

## Verification

Workflow trigger configuration was checked with grep across .github/workflows.

Whitespace validation was checked with:

git diff --check

## Evaluation gate

The change preserves validation coverage while reducing redundant GitHub-hosted runner usage.

## Human approval gate

This change should be reviewed before merge to staging.
