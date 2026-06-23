# Nightly full validation Linux runner audit

## Summary

This report documents the fix for nightly full validation failing on a macOS self-hosted runner when starting the Postgres service container.

## Root cause

`.github/workflows/nightly-full-validation.yml` targeted `runs-on: self-hosted`, which resolved to a macOS self-hosted runner in this repository.

The job defines a `postgres` service container. GitHub Actions service containers are supported only on Linux runners, so the workflow failed before any test steps ran:

`Container operations are only supported on Linux runners`

## Change

The `full-validation` job now uses `runs-on: ubuntu-latest` so service containers can start and tests can reach Postgres at `127.0.0.1:5432`.

Unchanged:

- `services.postgres` (`postgres:16` with health checks and port `5432:5432`)
- `DATABASE_URL: postgresql://postgres:postgres@127.0.0.1:5432/postgres`
- Scheduled and `workflow_dispatch` triggers
- Full Rust, Python, and enterprise readiness validation steps
- Slack notification step

## Scope

Changed file:

`/.github/workflows/nightly-full-validation.yml`

No application runtime logic was changed.

No database migrations were changed.

No compliance verdict semantics were changed.

## Validation

1. Workflow YAML parses successfully.
2. The job still defines the `postgres` service container.
3. `DATABASE_URL` still points to `127.0.0.1:5432`.
4. The job no longer targets a generic `self-hosted` runner that can resolve to macOS.

## Risk assessment

Low.

This change affects only the CI runner platform for nightly full validation. Test coverage and database connectivity expectations are unchanged.

GitHub-hosted `ubuntu-latest` minutes will be consumed for the nightly schedule instead of a self-hosted macOS runner. Other workflows in this repository already use `ubuntu-latest` for Postgres-backed jobs.

## Evaluation gate

Nightly full validation should complete service container startup and execute the full Rust, Python, and enterprise readiness checks on the next scheduled or manual run.

## Human approval gate

Reviewed before merge. Change scope is limited to workflow runner selection for nightly full validation.
