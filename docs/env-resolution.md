# GovAI deployment environment resolution

This document is the **single contract** for how `dev`, `staging`, and `prod` are chosen. The Rust audit service and Python tooling implement the same rules.

## Precedence

Variables are read in order; the **first with a non-whitespace value** wins:

1. `AIGOV_ENVIRONMENT`
2. `AIGOV_ENV`
3. `GOVAI_ENV`

If none are set, or all are set only to whitespace → the effective value is empty before parsing.

## Accepted values (case-insensitive)

After trim, each alias normalizes to a canonical tier:

| Canonical | Aliases |
|-----------|---------|
| `dev` | `dev`, `development`, `local` |
| `staging` | `staging`, `stage` |
| `prod` | `prod`, `production` |

## Default and failure behavior

| Input | Rust (`resolve_from_env`) | Python (`resolve_aigov_environment`) |
|-------|---------------------------|----------------------------------------|
| Unset / empty / whitespace-only | `dev` | `dev` |
| Valid alias | `Dev` / `Staging` / `Prod` | `"dev"` / `"staging"` / `"prod"` |
| Non-empty, not a valid alias | **Startup error** (process exits) | **`ValueError`** |

Whitespace-only values are ignored so the next variable in the precedence list can apply (same as treating `"   "` as unset).

## Policy and policy version

- **Policy version id** (for bundle hash and `/status`): `v0.5_dev`, `v0.5_staging`, `v0.5_prod` — see `rust/src/govai_environment.rs` (`policy_version_for`).
- **Policy knobs** (`require_approval`, `block_if_missing_evidence`, `enforce_approver_allowlist`, `approver_allowlist`): loaded from `policy.<env>.json` then `policy.json` under **`AIGOV_POLICY_DIR`** if set, otherwise under the process working directory — unless **`AIGOV_POLICY_FILE`** points at a single file. See `rust/src/policy_config.rs` and the full contract in [`policy-contract.md`](policy-contract.md).
- **`AIGOV_POLICY_STRICT`**: when set to `true` / `1` / `on` / `yes`, invalid or missing policy files **abort startup even in `dev`**. Without strict mode, **only `dev`** may fall back to compiled defaults when a file is missing or invalid; **`staging`** and **`prod`** always require a valid resolvable policy file.
- **Repository defaults:** `rust/policy.dev.json` sets `enforce_approver_allowlist: false`; `rust/policy.json` sets it `true` for shared/staging/prod-style configs. Allowlist defaults are defined in code (`compliance_officer`, `risk_officer`) when the field is omitted.

## Evidence ingest

- Every **new** event appended through `POST /evidence` gets `environment` set to the server’s resolved tier.
- The client may omit `environment` or send a value that matches the server; a **mismatch** is rejected.
- **Legacy** ledger lines may omit `environment`; reads and projections still work. Once any event for a `run_id` carries `environment`, later events for that run must use the **same** tier (enforced at ingest).

## Run manifests (`console.runs` / Supabase `runs`)

- Column `environment` stores the tier used when the row was written (from `resolve_aigov_environment()` in Python ingest, aligned with the audit server tier in normal operation).
- **Migration:** existing rows without the column get `default 'dev'` when applying `rust/migrations/0006_run_environment.sql`. Backfill scripts default missing source `environment` to `dev`.

## Examples

```bash
# Local — unset vars default to dev
cargo run -p aigov_audit

# Staging
export AIGOV_ENVIRONMENT=staging
cargo run -p aigov_audit

# Production (explicit)
export AIGOV_ENVIRONMENT=prod
cargo run -p aigov_audit
```

```bash
# Python ingest (same variables)
export AIGOV_ENVIRONMENT=staging
python -m aigov_py.ingest_run <RUN_ID>
```

## Implementation map

| Concern | Location |
|---------|----------|
| Optional policy search root (`AIGOV_POLICY_DIR`) | `rust/src/policy_config.rs` |
| Parse + stamp + ledger consensus | `rust/src/govai_environment.rs` |
| HTTP ingest order | `rust/src/govai_api.rs` (`ingest`) |
| Policy file loading | `rust/src/policy_config.rs` |
| Python resolver | `python/aigov_py/env_resolution.py` |
| DB schema | `rust/migrations/0006_run_environment.sql` |

## Backward compatibility and operator-visible behavior

- **Policy JSON** without `enforce_approver_allowlist` deserialize with **`true`** (safe default). To keep relaxed dev approvers, use `rust/policy.dev.json` or set `enforce_approver_allowlist: false` explicitly.
- **`AIGOV_MODE`** (`ci` / `prod`) in Python is **operational mode** for artifacts and ingest heuristics — it is **not** the deployment tier. Tier for manifests and the audit server is **`AIGOV_ENVIRONMENT`** (and aliases) per this document.
- **Legacy ledger events** may omit `environment`; reads and projections still work. New appends always stamp the server tier.
