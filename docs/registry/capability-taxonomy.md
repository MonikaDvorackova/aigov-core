# Capability taxonomy

The machine-readable taxonomy lives in [`registry/capability-taxonomy.json`](../../registry/capability-taxonomy.json). Each `id` is a **stable string** used by [`registry/policy-pack-catalog.json`](../../registry/policy-pack-catalog.json) and submission templates.

## Categories (Phase 15)

| `id` | Typical evidence themes |
| --- | --- |
| `risk_management` | Risk registers, mitigations, approvals tied to residual risk acceptance. |
| `human_oversight` | Human-in-the-loop plans, escalation paths, role definitions for consequential decisions. |
| `traceability` | Decision records, lineage, digest-backed exports suitable for audit replay. |
| `robustness` | Security testing summaries, abuse-case handling, resilience of serving pipelines. |
| `post_market_monitoring` | Production monitoring, incident response, drift detection, and change management. |

## How to use the taxonomy

- **Policy pack authors** — pick the smallest set of capabilities that honestly describes the pack; reviewers will challenge overstated breadth.
- **Private registries** — may extend with additional `id` values **only** if they also extend the JSON catalog with definitions and keep `schema_version` compatibility notes.
- **Verification** — `scripts/registry_check.py` ensures every `capability_ids` entry on a pack resolves to a defined category.

Capabilities classify **documentation and interchange**; they are **not** a substitute for product verdict enums (`VALID`, `INVALID`, `BLOCKED`).
