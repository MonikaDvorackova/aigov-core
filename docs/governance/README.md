# Phase 3 governance metadata (M1)

This directory contains **read-only, machine-readable governance metadata**.

**Important:** Phase 3 M1 adds **metadata and validation only**.

- No runtime enforcement is added.
- No evidence ledger writes are performed.
- No `compliance-summary` behavior is changed.
- No API endpoints are added.

## Files

- `controls.v1.yaml`: Governance control catalog (control IDs + evidence requirements).
- `aiact_requirements.v1.yaml`: Small subset of EU AI Act requirement IDs used for mapping examples.
- `aiact_mappings.v1.yaml`: Requirement-to-control mappings.
- `reason_codes.v1.yaml`: Reason code registry mapped to controls.
- `rbac_permissions.v1.yaml`: RBAC permission registry (metadata only).
- `rbac_roles.v1.yaml`: RBAC role catalog referencing permission IDs (metadata only).

## How to add a control

1. Edit `controls.v1.yaml`.
2. Add an entry under `controls` with:
   - `control_id` (unique, stable)
   - `name`, `description`
   - `risk_class_applicability` (allowed: `MINIMAL`, `LIMITED`, `HIGH`, `PROHIBITED`)
   - `tags` (non-empty list)
   - `evidence_requirements` (non-empty list)
3. Optional fields:
   - `deprecated: true|false`
   - `supersedes: [CTRL....]` (list of control IDs)

## How to add an AI Act requirement

1. Edit `aiact_requirements.v1.yaml`.
2. Add an entry under `requirements` with:
   - `requirement_id` (unique)
   - `article_ref`, `title`, `description`
   - `risk_class_applicability` (allowed values only)
3. Optional fields:
   - `deprecated`, `supersedes`

## How to add a mapping

1. Edit `aiact_mappings.v1.yaml`.
2. Add an entry under `mappings` with:
   - `requirement_id` (must exist in `aiact_requirements.v1.yaml`)
   - `control_id` (must exist in `controls.v1.yaml`)
   - `mapping_strength` (allowed: `REQUIRED`, `RECOMMENDED`, `CONTEXTUAL`)
   - `applicability_risk_classes` (allowed values only)
   - `rationale`

## How to add a reason code

1. Edit `reason_codes.v1.yaml`.
2. Add an entry under `reason_codes` with:
   - `reason_code` (unique)
   - `control_id` (must exist in `controls.v1.yaml`)
   - `severity` (allowed: `INFO`, `WARN`, `BLOCKING`)
   - `description`

## Validation

Validation is implemented as a **pure read-only** Python validator in `python/aigov_py/governance_catalog.py`
and exercised by `python/tests/test_governance_catalog_validation.py`.

