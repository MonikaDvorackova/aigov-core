# Runtime Packaging And Operations

## Summary

Adds official container packaging (`Dockerfile`, `.dockerignore`), operator stacks under `deployments/` (Docker Compose, Kubernetes manifests, Helm chart), operational documentation (`docs/runtime-operations.md`, `docs/backup-and-recovery.md`, `docs/threat-model.md`), and `make runtime-packaging-check` wired into `govai-ci.yml`. The image runs `aigov_audit` as a non-root user on port 8088 with configurable ledger, database, API keys, and policy paths. No commercial platform UI, entitlement services, or hosted control-plane flows.

## Evaluation gate

**Replayed governance state remains ledger-authoritative after deployment and restore.** Operators must persist `GOVAI_LEDGER_DIR`; compliance summary and exports project from ledger bytes. After backup/restore, `GET /api/export/:run_id` and `govai replay-audit-export` must agree with pre-incident exports for the same run. Evaluation outcomes (`evaluation_reported`) are not re-derived from external metrics post-restore—only from restored ledger + policy.

## Human approval gate

**Approval evidence remains append-only operational evidence across deployments and restores.** `human_approved` events live in the ledger; restores must not rewrite or omit them. Export archives and signed bundles preserve approval fields for offline verification; a restore drill should show the same approval-gated verdict progression (e.g. BLOCKED → VALID) when ledger data is intact.

## Deployment guarantees

**Guaranteed (documented, not HA):**

- Single-writer ledger semantics with persistent volume guidance.
- Configurable env for bind address, policy dir, API keys, Postgres URL.
- Liveness `/health` and readiness `/ready` for orchestrators.
- Non-root container execution (UID 1000).

**Not guaranteed:**

- Multi-replica active-active ledger on one volume.
- Automated backup/restore or cross-region replication.
- Built-in observability or commercial control plane.

## Verification

```bash
make runtime-packaging-check
make reconstructible-demo-check
make reference-integrations-check
make core-runtime-examples-check
make gate
cd rust && cargo build --locked --bin aigov_audit && cargo test --locked
cd ..
```

Optional local image smoke:

```bash
docker build -t aigov-core:local .
docker run --rm -p 8088:8088 -v govai-ledger:/var/lib/govai/ledger aigov-core:local
curl -sS http://127.0.0.1:8088/health
```
