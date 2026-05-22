# GovAI Policy Engine Flow

This document describes the conceptual flow of policy evaluation in GovAI.

## Flow

1. Governance evidence is collected.

2. Runtime or CI context is attached.

3. Policy requirements are loaded.

4. Evidence is evaluated against policy requirements.

5. Approval requirements are checked.

6. Artifact continuity is checked.

7. A final governance verdict is produced.

## Text diagram

Evidence
  ->
Context
  ->
Policy loading
  ->
Policy evaluation
  ->
Approval check
  ->
Artifact continuity check
  ->
Governance verdict

## Policy outcomes

Policy pass:
The policy requirements are satisfied.

Policy fail:
Evidence exists, but the policy requirements are not satisfied.

Policy blocked:
Required evidence or context is missing.

## Design principle

Policy evaluation should be deterministic, explainable, and auditable.
