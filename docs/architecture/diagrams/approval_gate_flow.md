# GovAI Human Approval Gate Flow

This document describes how human approval gates participate in GovAI decisions.

## Flow

1. A governance action requires approval.

2. Evidence is collected.

3. Approval requirement is evaluated.

4. Approval record is checked.

5. Decision is allowed only if required approval exists.

## Text diagram

Governance action
  ->
Evidence collection
  ->
Approval requirement check
  ->
Approval record lookup
  ->
Decision verdict

## Approval behavior

Approval present and valid:
The approval gate can pass.

Approval missing:
The decision is BLOCKED.

Approval invalid:
The decision is INVALID or BLOCKED depending on the failure mode.

## Design principle

Missing human approval must not silently pass.
