# Pilot execution example package

This directory provides a **copy-paste friendly** wrapper around Phase 9 diagnostics. It uses **stdlib Python only** and emits **deterministic JSON** on stdout for automation.

## Prerequisites

- Repository cloned
- Run commands from the **repository root**

## Scripts

```bash
bash examples/pilot-execution/run-pilot-execution-check.sh
```

Or directly:

```bash
make pilot-execution
make pilot-manifest
make go-to-market-check
```

## Sample plan

`sample-pilot-plan.json` is an illustrative JSON document for workshop exercises; it is **not** interpreted by the audit service.

## Related documentation

- `docs/pilots/enterprise-pilot-playbook.md`
- `docs/pilots/pilot-manifest.json`
- `docs/sales/proof-of-value-plan.md`
