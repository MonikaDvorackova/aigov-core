# Backup and recovery

Operator guidance for GovAI Core persistence: append-only ledger, Postgres, and signed exports.

## Append-only ledger backup

**Scope:** everything under `GOVAI_LEDGER_DIR`.

**Recommended approaches:**

1. **Volume snapshots** — preferred for RPO/RTO on cloud block storage. Quiesce writes (stop pod or scale to 0) for strict point-in-time consistency.
2. **Filesystem copy** — `rsync -a` or `tar` while stopped; do not copy partial files mid-write.
3. **Frequency** — align with compliance RPO; hourly snapshots plus daily off-site copy is a common starting point.

**Verify backups** by restoring to an isolated host and running:

```bash
curl -sS http://127.0.0.1:8088/ready
govai replay-audit-export --export path/to/export.json
```

## Postgres backup

When `DATABASE_URL` is configured:

- Use native logical backup (`pg_dump`) or managed automated backups.
- Store backups encrypted at rest; restrict access to DBAs and break-glass roles.
- After restore, set `GOVAI_AUTO_MIGRATE=true` for one startup if migration versions changed.

Postgres loss with intact ledger: historical evidence remains in ledger files; relational auxiliary state may need rebuild from exports.

## Export archival

Periodic `GET /api/export/:run_id` (or automation via `govai` CLI) to object storage:

- Include `schema_version`, `evidence_events`, `evidence_hashes`, and `decision`.
- Name objects with run id and export hash prefix for deduplication.
- Retain per regulatory schedule independently of ledger retention.

## Signed export archival

When using signed bundles ([signed-evidence-bundles.md](./signed-evidence-bundles.md)):

- Archive `.json` export + detached signature (or embedded signature field per your pipeline).
- Store public verification keys in a separate trust store.
- On restore drills, run `govai verify-audit-export` before replay.

## Replay verification after restore

1. Restore ledger (+ Postgres if used).
2. Start `aigov_audit`; confirm `/health` and `/ready`.
3. Pick a canonical run id with a pre-incident export file.
4. Fetch live export: `GET /api/export/{run_id}` — compare hash chain to archived export.
5. Run deterministic replay CLI; expect match on verdict and event ordering.

Mismatch indicates incomplete restore, corruption, or policy drift — stop promotion until resolved.

## Corruption handling

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `/ready` fails | DB down or ledger permissions | Fix mount permissions (UID 1000), check `DATABASE_URL` |
| `/verify/:run_id` invalid | Truncated ledger segment | Restore from last good snapshot; do not hand-edit ledger files |
| Export hash mismatch | Partial copy or mixed volumes | Re-restore from older snapshot; compare `bundle-hash` |
| Replay CLI fails integrity | Tampered export archive | Use signed export verification; investigate key compromise |

**Do not** silently truncate ledger files to “fix” errors — that destroys audit evidence.

## Recovery objectives (operator-defined)

GovAI Core does not enforce RPO/RTO. Operators should document:

- Maximum acceptable ledger age at restore.
- Whether exports alone satisfy regulatory read models.
- Escalation when signing keys or API keys are compromised (see [threat-model.md](./threat-model.md)).
