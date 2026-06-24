# Nightly full validation Linux runner audit

## Summary

This report documents the nightly full validation runner correction.

## Root cause

The nightly full validation workflow used a self hosted runner while also defining a PostgreSQL service container.

GitHub Actions service containers require Linux runner support. When the workflow ran on a non Linux self hosted runner, it failed with:

Container operations are only supported on Linux runners

## Change

The workflow .github/workflows/nightly-full-validation.yml was changed to use ubuntu-latest instead of self-hosted.

## Validation

The workflow configuration was reviewed locally.

The nightly full validation workflow now uses ubuntu-latest, which supports the PostgreSQL service container used by the job.

## Risk

Low. This is a CI runner configuration change only. It does not modify runtime code, APIs, schemas, or package behavior.

## Expected result

The nightly full validation workflow should run on a Linux runner and should no longer fail because of unsupported container operations.

## Evaluation gate

The change was evaluated against the failing nightly validation behavior. The root cause was that the workflow used a generic self-hosted runner while also defining a PostgreSQL service container. GitHub Actions service containers require a Linux runner. Moving the job to ubuntu-latest preserves PostgreSQL-backed validation while making the runner compatible with service containers.

Validation performed:
- nightly-full-validation keeps services.postgres configured
- DATABASE_URL remains pointed at 127.0.0.1:5432
- full Rust tests, full Python tests, enterprise readiness, and Slack notification steps remain present
- the workflow no longer targets a generic self-hosted runner

## Human approval gate

This workflow change is intended for maintainer review before promotion from staging to main. Human approval is required because it changes CI execution infrastructure for the nightly full validation workflow.
