# GovAI CI/CD Compliance Flow

This diagram describes how GovAI participates in CI/CD enforcement.

## Flow

1. A pull request or deployment workflow starts.

2. CI runs project tests and produces governance-relevant artifacts.

3. GovAI collects evidence from:
- test results
- discovery outputs
- evaluation results
- approval records
- artifact digests
- promotion metadata

4. Evidence is submitted to the audit service.

5. The audit service records events in the audit ledger.

6. The compliance gate verifies:
- evidence completeness
- evaluation status
- approval requirements
- digest continuity
- policy requirements

7. GovAI returns a verdict:
- VALID
- INVALID
- BLOCKED

8. CI proceeds only when the verdict is VALID.

## Text diagram

Pull request or deployment
  ->
CI workflow
  ->
Tests and evidence generation
  ->
Evidence pack export
  ->
GovAI audit service
  ->
Audit ledger
  ->
Compliance verification
  ->
VALID / INVALID / BLOCKED
  ->
Allow or block promotion

## Fail-closed rule

If evidence is missing, approvals are missing, or artifact continuity cannot be verified, the compliance gate must return BLOCKED.
