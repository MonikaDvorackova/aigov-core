# GovAI Threat Model

## Purpose and Scope

This document defines the formal threat model and trust assumptions for GovAI.

GovAI is a decision-level AI governance platform that enforces fail-closed compliance semantics over machine learning and AI deployment workflows. The purpose of this document is to explicitly identify protected assets, trust boundaries, threat scenarios, and mitigations.

## Security Objectives

GovAI is designed to provide the following security properties:

1. Integrity of audit evidence
2. Integrity of compliance verdicts
3. Integrity of human approvals
4. Tenant isolation
5. Traceability of decision artifacts
6. Durability of audit records
7. Resistance to evidence forgery and replay attacks

## Protected Assets

The following assets are security-critical:

- Audit ledger
- Evidence bundles
- Portable digests
- Approval records
- API keys
- Tenant identifiers
- Compliance verdicts
- Billing records
- Runtime governance events

## Trust Boundaries

GovAI includes the following trust boundaries:

1. Client to API boundary
2. API server to PostgreSQL boundary
3. API server to ledger storage boundary
4. CI/CD system to hosted compliance gate boundary
5. Human approver to approval subsystem boundary
6. Tenant isolation boundary

## Threat Actors

Potential threat actors include:

- External attackers
- Malicious tenants
- Compromised CI runners
- Insider operators
- Unauthorized approvers
- Accidental misconfiguration

## Security Assumptions

GovAI assumes:

- Cryptographic hash functions remain collision resistant
- API keys are protected by operators
- PostgreSQL enforces durability guarantees
- Ledger storage is durable and access-controlled
- CI artifacts are not modified after generation
- Human approvers are properly authenticated

## Threat Scenarios

### Evidence Forgery

An attacker submits fabricated evidence to obtain a false VALID verdict.

### Replay Attacks

Previously valid evidence is replayed for unrelated workflows.

### Approval Bypass

Required human approvals are omitted or forged.

### Tenant Isolation Violation

One tenant attempts to read or modify another tenant's audit records.

### Ledger Tampering

Audit records are altered or deleted after creation.

### Digest Mismatch

Recorded evidence does not match the referenced artifacts.

### API Key Compromise

An attacker obtains valid credentials and submits unauthorized events.

### Denial of Service

The service is overwhelmed or made unavailable.

## Mitigations

GovAI mitigates these threats through:

- SHA-256 digest continuity
- Artifact-bound evidence verification
- Fail-closed VALID / INVALID / BLOCKED semantics
- Server-owned tenant mapping from API keys
- Immutable append-only audit ledger
- Mandatory human approval gates
- Readiness checks for database and ledger
- Durable storage requirements
- Audit replay and verification tools

## Residual Risks

Residual risks include:

- Operator credential compromise
- Infrastructure outages
- Insider abuse with authorized credentials
- Misconfigured deployments
- Future cryptographic weaknesses

## Operational Recommendations

Operators should:

- Protect API keys using secret managers
- Enable durable storage and backups
- Restrict access to ledger and database systems
- Monitor readiness and audit endpoints
- Rotate credentials regularly
- Review approval workflows

## Future Hardening

Planned security enhancements include:

- Cryptographic signing of evidence bundles
- Hardware-backed key management
- Rate limiting and abuse detection
- Tamper-evident ledger anchoring
- Formal security assessments

## Summary

GovAI is designed to preserve the integrity, traceability, and isolation of decision-level governance evidence. Security is enforced through fail-closed semantics, cryptographic artifact binding, immutable audit records, and strict tenant separation.
