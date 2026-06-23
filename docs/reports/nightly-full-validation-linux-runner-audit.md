# Nightly full validation Linux runner audit

## Summary

Documents the runner correction for nightly full validation.

## Root cause

The workflow used a self hosted runner while also defining a PostgreSQL service container. Service containers require Linux runner support. On a non Linux self hosted runner, the job failed with this error:

Container operations are only supported on Linux runners

## Change

Changed .github/workflows/nightly-full-validation.yml to run on ubuntu-latest instead of self-hosted.

## Validation

Verified that nightly-full-validation.yml now uses runs-on: ubuntu-latest.

## Risk

Low. This changes only the workflow execution environment and does not modify runtime code, APIs, schemas, or package behavior.

## Expected result

The nightly full validation workflow should run on a Linux runner and support the PostgreSQL service container.
