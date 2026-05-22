# Golden demo run (manifest)

Canonical **`run_id`** for documentation and offline review:

`68460594-91c0-4e63-8722-bd4f2f54abe5`

This is the only checked-in run that already had **both** a full evidence bundle and a gate-complete report; audit index and packs were generated with existing `make bundle` / `make evidence_pack` targets (no new tooling).

## Artifact paths (repo root)

| Role | Path |
|------|------|
| Evidence bundle (machine) | `docs/evidence/68460594-91c0-4e63-8722-bd4f2f54abe5.json` |
| Audit report (human) | `docs/reports/68460594-91c0-4e63-8722-bd4f2f54abe5.md` |
| Audit index (JSON, hashes + paths) | `docs/audit/<run_id>.json` |
| Pack (zip) | `docs/packs/<run_id>.zip` |
| Pack (expanded dir) | `docs/packs/68460594-91c0-4e63-8722-bd4f2f54abe5/` |

## Symlinks in this directory

Same files as stable relative links (no file duplication):

- `evidence-bundle.json` → `../../evidence/68460594-91c0-4e63-8722-bd4f2f54abe5.json`
- `report.md` → `../../reports/68460594-91c0-4e63-8722-bd4f2f54abe5.md`
- `audit.json` → generated audit index at `docs/audit/<run_id>.json`
- `pack.zip` → generated evidence pack at `docs/packs/<run_id>.zip`
- `pack-expanded` → `../../packs/68460594-91c0-4e63-8722-bd4f2f54abe5/`

## Compliance summary (JSON)

The **`GET /compliance-summary?run_id=…`** response (`aigov.compliance_summary.v2`) is defined in [`docs/strong-core-contract-note.md`](../../strong-core-contract-note.md). A separate JSON snapshot is **not** vendored here: the live endpoint reads **`rust/audit_log.jsonl`**, which may not include historical demo runs checked in only as files. For bundle-based review, start from the evidence JSON above.

See [`COMPLIANCE_SUMMARY.md`](./COMPLIANCE_SUMMARY.md).

## Regenerate packs (optional)

From repo root, with Python venv active per [`README.md`](../../../README.md):

```bash
make bundle RUN_ID=68460594-91c0-4e63-8722-bd4f2f54abe5
make evidence_pack RUN_ID=68460594-91c0-4e63-8722-bd4f2f54abe5
```
