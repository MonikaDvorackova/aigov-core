# Engineering lines of code (LOC)

Raw line counts over the whole repository (for example ``git ls-files | xargs wc -l``) mix **product source**, **tests**, **documentation**, **CI and package configuration**, **generated bundles**, **experiment outputs**, and **fixtures**. That total is easy to misread for engineering sizing, architecture reviews, or trend tracking.

AIGov Core documents the **categorised LOC report** contract here. The full `scripts/engineering_loc.py` reporter ships in the proprietary platform repository; this open-core repo validates the documentation contract with `scripts/test_engineering_loc_smoke.py`.

## Why raw LOC is misleading

- **Generated or vendored trees** (`dist/`, `.next/`, `node_modules/`, `target/`, …) can dominate totals even when they are not hand-maintained source.
- **Large JSON or logs** (experiment replays, evidence bundles, demo artefacts) add thousands of lines that are not application logic.
- **Markdown documentation and audit reports** are valuable but are not executable product code.
- **Lockfiles and CI YAML** are real engineering effort to maintain but are not the same kind of metric as Rust/Python/TypeScript implementation.

## What “engineering LOC” means here

The script prints three subtotals (all derived from the category table):

- **Backend/core engineering LOC** = **core_source**
- **Frontend/dashboard LOC** = **dashboard**
- **Product engineering LOC** = **core_source + dashboard**

- **core_source** includes, among others: `rust/` production `.rs` and SQL migrations, `python/aigov_py/` and `python/govai/` application modules, `ai_discovery/` TypeScript, `api/` OpenAPI, `docs/schemas/`, and `examples/` sample code. Test paths, the top-level `experiments/` tree, and `python/aigov_py/experiments/` are **not** in this bucket.
- **dashboard** is the Next.js application under `dashboard/`, excluding dashboard-local config files (for example `package.json`, `eslint.config.mjs`, `next.config.ts`) which are counted under **config_ci**.

Excluded from engineering LOC (but still reported in their own rows): **tests**, **experiments**, **docs**, **config_ci**, **generated_build**, **data_fixtures_assets**, and **other**.

## Command

From the repository root:

In the platform repository:

```bash
python3 scripts/engineering_loc.py
make engineering_loc
```

In AIGov Core, CI runs the documentation smoke check:

```bash
make engineering_loc
```

## Smoke check

```bash
python3 scripts/test_engineering_loc_smoke.py
```

This verifies a successful run inside the repo and a clear failure outside a Git repository.
