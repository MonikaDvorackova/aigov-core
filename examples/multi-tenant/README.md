# Multi-tenant governance examples

Stdlib-only drivers for the enterprise **multi-tenant governance** bundle under [`multi-tenant/`](../../multi-tenant/) (no network). Run from the repository root or use the script below (it resolves the repo root automatically).

| Script | Purpose |
| --- | --- |
| [`run-multi-tenant-check.sh`](run-multi-tenant-check.sh) | Aggregated diagnostics JSON (`multi_tenant_check.py --json`). |

## Sample snapshot

- [`sample-tenant-governance-snapshot.json`](sample-tenant-governance-snapshot.json) — referenced by `scripts/multi_tenant_check.py` to ensure paths resolve to committed artefacts.

## Makefile

```bash
make multi-tenant-check
make tenant-isolation-check
```

Canonical operator documentation lives under [`docs/multi-tenant/`](../../docs/multi-tenant/).
