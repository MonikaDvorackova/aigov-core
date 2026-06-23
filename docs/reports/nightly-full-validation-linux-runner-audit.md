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
