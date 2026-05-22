# GovAI Pilot Evaluation Package

## Purpose

This document defines the materials needed for prospective pilot users, enterprise evaluators, and technical decision makers to evaluate GovAI.

The goal is to make GovAI easier to assess as a decision-level AI governance platform without requiring evaluators to inspect the full codebase first.

## Target Audience

The pilot evaluation package is intended for:

- AI engineering teams
- MLOps teams
- Security teams
- Compliance teams
- Risk and audit teams
- Enterprise architecture teams
- Research partners
- Early commercial pilot customers

## Evaluation Goals

A pilot evaluator should be able to determine:

1. What problem GovAI solves
2. How GovAI differs from ordinary CI
3. How decision-level auditability works
4. How evidence bundles are verified
5. How fail-closed enforcement works
6. How tenant isolation is handled
7. How GovAI can fit into existing AI deployment workflows
8. What operational assumptions are required

## Required Pilot Materials

## 1. One Page Technical Overview

The overview should explain:

- The auditability gap
- Decision-level governance
- Evidence bundles
- Human approvals
- Compliance verdicts
- Audit ledger
- Hosted and local deployment options

## 2. Local Demo Instructions

The pilot package should link to the Docker Compose local demo.

The demo should show:

- Service startup
- Evidence submission
- Verification
- Compliance summary
- VALID, INVALID, and BLOCKED outcomes where possible

## 3. GitHub Actions Integration Example

The package should include or link to a working GitHub Actions example.

The example should show:

- Evidence artifact generation
- Evidence pack submission
- Digest continuity verification
- Compliance gate result

## 4. Security and Trust Documentation

The package should link to:

- Threat model
- Compatibility policy
- Security policy
- Tenant isolation documentation
- Audit replay documentation where available

## 5. Evaluation Checklist

Pilot evaluators should review:

- Whether GovAI fits their AI deployment workflow
- Whether evidence collection is feasible
- Whether approval requirements match internal process
- Whether audit outputs satisfy governance needs
- Whether deployment requirements are acceptable
- Whether integration effort is justified

## 6. Success Criteria

A pilot is successful when:

- GovAI runs in the evaluator environment
- At least one workflow produces a VALID verdict
- At least one intentionally incomplete workflow is BLOCKED
- Audit evidence can be inspected after execution
- The evaluator understands the governance boundary
- Operational gaps are identified clearly

## 7. Common Pilot Questions

## What does GovAI enforce?

GovAI enforces decision-level governance invariants such as evidence completeness, evaluation status, approval status, artifact continuity, and tenant isolation.

## Is GovAI a model benchmark?

No. GovAI does not replace model evaluation. It verifies whether a deployment or governance decision is supported by auditable evidence.

## What happens when evidence is missing?

GovAI fails closed. Missing evidence, missing approval, or incomplete audit context should produce BLOCKED rather than VALID.

## Does GovAI require hosted infrastructure?

No. GovAI should support local and hosted evaluation paths, depending on deployment needs.

## How is tenant isolation handled?

Tenant isolation is derived from server-owned API key mapping. Request headers are not trusted as ledger isolation boundaries.

## Pilot Deliverables

A pilot should produce:

- Integration notes
- Evidence examples
- Compliance verdict examples
- Identified workflow gaps
- Security and operational questions
- Decision on next adoption step

## Summary

The pilot evaluation package should make GovAI easy to evaluate as a governance infrastructure component. It should reduce friction for enterprise users while preserving a precise technical framing around decision-level auditability.
