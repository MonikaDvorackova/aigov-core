# Runtime operations

AIGov Core ships as a self-hosted **ledger HTTP runtime** (`aigov_audit`). This document describes deployment models, persistence, backups, upgrades, and what operators can rely on today.

## Deployment models

| Model | Path | Use when |
|-------|------|----------|
| Docker image | Root `Dockerfile` | Single host, CI smoke, minimal footprint |
| Docker Compose | `deployments/docker-compose/` | Dev/staging operator stack with Postgres |
| Kubernetes (plain) | `deployments/kubernetes/` | Cluster operators who manage manifests directly |
| Helm | `deployments/helm/aigov-core/` | Parameterized installs with persistence and secrets |

All models run the same binary entrypoint: `aigov_audit` on port **8088** (configurable via `AIGOV_BIND`).

## Environment variables

| Variable | Purpose |
|----------|---------|
| `AIGOV_BIND` | Listen address (default in image: `0.0.0.0:8088`) |
| `AIGOV_ENVIRONMENT` | Policy profile selector (`dev`, `staging`, `prod`) |
| `AIGOV_POLICY_DIR` | Directory containing `policy.json` bundles |
| `GOVAI_LEDGER_DIR` | Append-only ledger files (must be persistent in production) |
| `DATABASE_URL` | Postgres for SQL migrations / optional relational state |
| `GOVAI_API_KEYS` | Comma-separated API keys (when auth enabled) |
| `GOVAI_API_KEYS_JSON` | JSON map key → tenant id |
| `GOVAI_AUTO_MIGRATE` | Run SQL migrations on startup (`true`/`false`) |

Signed export signing keys are documented in [signed-evidence-bundles.md](./signed-evidence-bundles.md); store them in secrets managers, not ConfigMaps.

## Persistence requirements

**Ledger (required for authoritative governance state):** mount a volume at `GOVAI_LEDGER_DIR`. The runtime assumes a single writer to this directory. Do not attach the same ReadWriteOnce volume to multiple pods without external coordination (not provided).

**Postgres (optional but typical):** used for schema migrations and relational features. Back up independently of the ledger. Loss of Postgres without ledger backup may block migrations but does not rewrite append-only ledger history if ledger files survive.

## Ledger storage guidance

- Use durable block storage (EBS, PD, managed disk), not ephemeral container layers.
- Filesystem: ext4/xfs with regular fsck; avoid NFS for write-heavy append paths unless your ops team accepts latency/fsync semantics.
- Permissions: image runs as UID/GID **1000** (`govai`); mount paths must be writable by that user.
- Retention: define operator retention for ledger segments and exports; Core does not implement automatic tiered archival yet.

## Backup strategy

See [backup-and-recovery.md](./backup-and-recovery.md). At minimum:

1. Snapshot or copy `GOVAI_LEDGER_DIR` on a schedule (crash-consistent snapshot acceptable if the volume is quiesced or the runtime is stopped for strict consistency).
2. `pg_dump` or managed backup for Postgres when `DATABASE_URL` is in use.
3. Archive signed audit exports to object storage with separate integrity verification.

## Restore semantics

1. Restore ledger volume to the same path (`GOVAI_LEDGER_DIR`).
2. Restore Postgres if used; run with `GOVAI_AUTO_MIGRATE=true` once if schema version drifted.
3. Start runtime; verify `GET /ready` and `GET /health`.
4. Run deterministic replay verification on a known export (see [deterministic-replay.md](./deterministic-replay.md)).

Replaying governance state from exports validates projection; **ledger bytes remain authoritative** for live ingest.

## Replay guarantees

When ledger files are intact:

- Evidence event order and hash chain integrity are preserved.
- Compliance summary and export projection remain deterministic for a given run id.
- `govai replay-audit-export` / `replay_audit_export_once` can validate export bundles offline.

When ledger files are missing but signed exports exist:

- Offline verification and replay of **export payloads** still work.
- Live ingest for historical run ids cannot be reconstructed without ledger data.

## Signing key management

- Generate Ed25519 signing material per environment; never reuse dev keys in production.
- Rotate by dual-publishing exports during a window; verifiers must trust both public keys until cutover completes.
- Compromise response: revoke API keys, rotate signing keys, re-export critical runs from restored ledger.

## Policy bundle management

- Ship default bundles in the image under `/app/policies`.
- Override by mounting a ConfigMap/volume to `AIGOV_POLICY_DIR` for environment-specific policy.
- Treat policy changes as **forward-only** operational events; document which policy version applied to each deployment.

## Rolling upgrades

1. Scale to one replica (default).
2. Snapshot ledger volume.
3. Replace image tag; roll pod with `readinessProbe` on `/ready`.
4. Smoke-test `POST /evidence` on a test run id in a non-production tenant first when possible.

**Not supported yet:** blue/green with shared multi-writer ledger, automatic leader election, or cross-region active-active ledger replication.

## What IS guaranteed (today)

- Append-only ledger semantics for ingested evidence (no in-place rewrite API).
- Deterministic verdict projection from ledger + policy for a given run.
- Health (`/health`) and readiness (`/ready`) endpoints for orchestrators.
- Offline export verification and replay tooling documented in-repo.

## What is NOT guaranteed yet

- Multi-replica HA with a single shared ledger volume.
- Automatic backup, replication, or corruption repair.
- Built-in metrics/tracing stack (bring your own observability).
- Commercial platform control-plane UX or entitlement services (out of scope for Core).
