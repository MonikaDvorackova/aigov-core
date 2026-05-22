# Threat matrix (governance and auditability)

This matrix aligns adversary capabilities with GovAI-style **technical mitigations** and explicit **residual risks**. It supports security narratives for research and enterprise due diligence. It is **not** a formal penetration-test report.

## Machine-readable sample

Canonical structured rows: `examples/security/sample-threat-matrix.json` (validated by `scripts/threat_model_check.py`).

## Categories (summary)

| Threat | GovAI-relevant mitigation (high level) |
|--------|----------------------------------------|
| Insider tampering | Append-only chain, RBAC, integrity verification |
| Evidence deletion | Replication, WORM/immutable tiers, exports |
| Provider–deployer collusion | Independent attestation, third-party monitoring |
| Key compromise | Rotation, KMS, short-lived tokens |
| Denial of evidence | Fail-closed policy, escalation, contractual audit rights |
| False inputs | Signatures where available, human review, cross-checks |
| Incomplete evidence | Required-evidence model, BLOCKED semantics |
| Unavailable provider metadata | Fallback strategies, contractual minimums |

Each row in the JSON sample includes `adversary_capability`, `mitigation`, `residual_risk`, `in_scope`, and `out_of_scope` strings suitable for manuscript tables.

## Architectural boundary

- **Core engine:** integrity of **recorded** events, deterministic projection given inputs (`docs/trust-model.md`).
- **Out of scope for software alone:** truth of natural-language claims, completeness of the real world versus the log, legal certification.

## Related

- `docs/security/threat-model-summary.md`
- `docs/trust-model.md`
- `ARCHITECTURE.md`
