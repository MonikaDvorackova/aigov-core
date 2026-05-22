# GovAI Glossary

This glossary defines core GovAI concepts used across documentation, issues, PRs, and RFCs.

## Auditability

The ability to reconstruct and verify why a system decision was allowed, blocked, or rejected.

## Evidence

Structured information used to justify a governance decision. Evidence may include evaluation results, approvals, artifact digests, discovery outputs, policy results, and audit events.

## Evidence bundle

A portable package of evidence artifacts and metadata used for verification, replay, or audit review.

## Evidence continuity

The property that recorded audit events can be deterministically linked to concrete exported artifacts.

## VALID

A decision verdict indicating that required evidence is present, evaluation passed, approval requirements are satisfied, and artifact continuity is intact.

## INVALID

A decision verdict indicating that evidence was present but evaluation or policy checks failed.

## BLOCKED

A fail-closed decision verdict indicating that progression is blocked because required evidence, approval, audit context, or integrity guarantees are missing.

## Fail-closed

A safety posture where missing or incomplete governance evidence blocks progression instead of being treated as success.

## Audit ledger

The storage layer for audit events and governance evidence records.

## Policy engine

The component responsible for evaluating governance rules against evidence and context.

## Governance-as-code

A model where governance requirements are represented as structured, reviewable, version-controlled configuration.

## Human approval gate

A governance control requiring explicit human approval before a decision can become valid or be promoted.

## Tenant isolation

The guarantee that one tenant cannot access or affect another tenant's audit records or governance context.

## Runtime governance

Governance enforcement that happens during system operation, not only during CI or pre-deployment checks.

## Traceability

The ability to follow the relationship between a decision, evidence, artifacts, approvals, policies, and runtime context.

## Replay

The process of reconstructing a prior decision from exported evidence to verify that the same verdict can be reproduced.

## Artifact digest

A cryptographic hash representing the content of an exported artifact.

## Compliance gate

A CI/CD or runtime control that permits or blocks progression based on GovAI verdicts.

## AI Act mapping

A structured mapping between GovAI evidence requirements and EU AI Act oriented governance controls.
