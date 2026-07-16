# Threat model (foundation)

This document frames security assumptions for self-hosted AIGov Core. It does **not** claim formal certification or complete mitigation of all AI governance risks.

## Trust boundaries

```
[Agent / CI] --API key--> [aigov_audit runtime] --> [append-only ledger volume]
                              |
                              v
                        [Postgres (optional)]
                              |
                              v
                        [Operators / auditors] --exports--> [archive + verify]
```

**Inside trust boundary (operator responsibility):**

- Runtime process, ledger volume, policy directory, API keys, signing keys, network policy to port 8088.

**Outside trust boundary:**

- Upstream LLM providers, agent frameworks, and any system that fabricates evidence before ingest.

## Tampering threats

| Threat | Impact | Mitigations (today) |
|--------|--------|---------------------|
| Modify ledger files on disk | False history | Filesystem permissions, immutable snapshots, WORM storage (operator) |
| MITM on HTTP API | Inject/spoof evidence | TLS termination at ingress, private networking |
| Replace policy bundle | Change verdict rules | Mount integrity checks, signed policy (future), change control |

Core detects hash chain breaks via `/verify` and export integrity checks; it does not encrypt ledger at rest by default.

## Replay manipulation

Attackers may present forged **export JSON** without a matching ledger.

- Use `govai verify-audit-export` when signatures are enabled.
- Compare live `GET /api/export` to archived copies after restore.
- Deterministic replay validates internal consistency; it does not prove ingest authenticity without ledger + API auth logs.

## Missing evidence attacks

Agents can omit steps (e.g. skip `human_approved`) while still returning plausible text.

- Verdict projection marks runs **BLOCKED** or **INVALID** when required events are absent.
- Operators must require ingest of all governance lifecycle events, not rely on model self-reporting.

## Forged approvals

Submitting `human_approved` via API without organizational process is possible if API keys leak.

- Protect `GOVAI_API_KEYS` / JSON map in secrets managers.
- Rotate keys on departure; scope keys per tenant.
- Correlate approvals with external ticketing (operator process, not Core-enforced yet).

## Compromised signing keys

Attacker can sign false exports that verify cryptographically.

- Key rotation, hardware/security module storage (operator).
- Short-lived signing keys and dual-key verification windows.
- Monitor for exports signed after key retirement.

## Runtime isolation assumptions

- Container runs as non-root UID 1000.
- Single replica default — no distributed locking between writers.
- No built-in seccomp/AppArmor profiles in stock manifests (harden per cluster policy).

## Operator assumptions

Operators are expected to:

- Control who can reach the audit API and mount ledger volumes.
- Perform backups and restore drills.
- Maintain policy bundles and environment separation (`AIGOV_ENVIRONMENT`).
- Investigate INVALID/BLOCKED verdicts using exports and replay tooling.

## Lineage and delegation threats

| Threat | Impact | Mitigations (today) |
|--------|--------|---------------------|
| Forged delegation | False narrative of who delegated to whom | Signed exports; `agent_delegated` with `agent_id`; graph validation on replay |
| Orphaned lineage | Child run without parent evidence | `lineage-graph` orphan detection; warnings on export |
| Hidden sub-agents | Undisclosed workers bypassing approval | Require `parent_run_id` / `root_run_id`; cross-run export review |
| Replay desynchronization | Export verdict differs from replayed projection | `govai replay-audit-export`; hash chain verify |
| Lineage tampering | Edited `parent_run_id` without ledger change | Append-only ledger; chain integrity; signed export digests |
| Cyclic governance flows | Circular delegation obscures accountability | `lineage_validation` cycle detection; invalid graph status |

Core does **not** prove that `agent_id` maps to a real organizational principal without operator identity integrations.

## Explicit non-guarantees

- Protection against malicious insiders with root on the ledger host.
- Automated fraud detection on evidence payload content.
- Legal admissibility or regulatory certification by deploying Core alone.
- Strong tenant isolation beyond API key → tenant mapping (no per-tenant crypto boundaries).

See [runtime-operations.md](./runtime-operations.md) for operational guarantees and gaps.
