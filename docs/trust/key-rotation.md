# Key rotation

Long-lived signing keys increase blast radius if compromised. This document aligns operator practice with the machine-readable policy stub `trust/key-rotation-policy.json`.

## Principles

- **Overlap windows** — new keys should verify incoming artefacts while old keys remain valid for historical verification during an explicit overlap period (`overlap_acceptance_days` in the JSON stub).
- **Maximum active age** — `max_active_signing_key_days` is a planning knob; enforce it with your HSM or cloud KMS policies.
- **Emergency rotation** — document break-glass steps (who approves, how tenants are notified, how ledgers and signed exports are re-verified).

## GovAI interaction

Key rotation for **API keys** (`GOVAI_API_KEY`) is independent of artefact signing keys. Both should be tracked in your CMDB: one gates **ingest**, the other gates **offline integrity** of exports.

## Validation

`python3 scripts/trust_chain_check.py` confirms the rotation policy JSON references this file and matches the active signing profile identifier.
