# Database and data-store environments

Related: [Deployment environments](deployment-environments.md) · [Branching strategy](branching-strategy.md)

## Principle

**Staging must use a different Postgres / Supabase-backed project than production.** Sharing one database between staging and production risks data corruption, PII leakage, and irreversible mistakes.

This document names **where** connection strings and keys appear; it does **not** rename variables or change application logic.

## Components in this repo

| Stack | Role |
|-------|------|
| **Supabase** (Postgres + Auth + Storage) | Dashboard auth (`NEXT_PUBLIC_SUPABASE_*`), Python helpers (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` in `python/aigov_py/supabase_db.py`). |
| **Postgres** (direct) | Rust service and API routes use **`DATABASE_URL`**. Dashboard console reads optional **`GOVAI_CONSOLE_RUNS_ENABLED`** + **`GOVAI_DATABASE_URL`** / **`DATABASE_URL`** (`dashboard/lib/console/govaiConsoleRunsRead.ts`). Python uses **`GOVAI_DATABASE_URL`** / **`DATABASE_URL`** via `python/aigov_py/psycopg_database_url.py`. |
| **SQL migrations** | Ordered files under `rust/migrations/` (e.g. `0001_govai_core.sql` … `0004_console_runs.sql`). Also referenced from `DEMO_FLOW.md` / `ENTERPRISE_LAYER.md`. |

## Where database URLs are consumed (audit)

- **Next.js dashboard**: `dashboard/lib/console/govaiConsoleRunsRead.ts` — `GOVAI_DATABASE_URL` overrides `DATABASE_URL` when console runs are enabled.
- **Supabase client (browser/server)**: `dashboard/lib/supabase/publicEnv.ts` — `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` or `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.
- **Python**: `python/aigov_py/supabase_db.py` — `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`; `python/aigov_py/psycopg_database_url.py` — normalized Postgres URL from env.

Supabase **Storage** buckets (`packs`, `audit`, `evidence`, etc. in `python/aigov_py/storage_upload.py`) are tied to the **Supabase project**—use a **staging Supabase project** for non-production deployments.

## Variables that must differ between staging and production

Use **separate Supabase projects** and/or **separate Postgres instances** so these never point at production from a staging build:

| Variable / area | Why it must differ |
|-----------------|-------------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Identifies the Supabase project (Auth, DB, Storage). |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Keys for that project. |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` (Python, server-side) | Service role must not target prod from staging jobs. |
| `DATABASE_URL` / `GOVAI_DATABASE_URL` | Direct Postgres access; staging DB only on staging. |
| `GOVAI_CONSOLE_PG_CA_CERT_PATH` | May differ per provider/region; use the cert matching the **staging** host when connecting to staging. |
| OAuth redirect / Site URL | Configured in Supabase Auth for **each** project; must list the **staging** app URL for staging. |

Optional / contextual: `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_AI_DISCOVERY_FILES_BASE`, `AIGOV_AUDIT_URL` — set per environment so links and integrations target the correct tier.

**CI note**: `.github/workflows/compliance.yml` uses a **`DATABASE_URL` secret** for some jobs when reports change. That secret should point to a **CI-appropriate** database, not necessarily production—treat it as part of pipeline configuration.

## Migration order (staging first, then production)

1. Apply the same ordered migrations to **staging** Postgres (or use Supabase migration tooling against the **staging** project).
2. Validate the application against staging.
3. Apply the **same** migration set to **production** during a planned promotion (often right after or as part of `staging` → `main`).

**Do not** run experimental or destructive changes against production first. There is no automated migration deploy in this repo’s GitHub Actions; operators run migrations with their chosen tool (`psql`, Supabase CLI, etc.).

See also: `DEMO_FLOW.md` (clean clone / migration order for enterprise demo).

## Safety checks

- **No accidental production DB from staging**: enforced by using different connection strings and different Supabase projects in Vercel **Preview** vs **Production** env settings—not by code branches alone.
- **No schema drift surprises**: keep migration files in git as the source of truth; apply in order.

## Risks and gaps

- If **one** `DATABASE_URL` is copied from production into a Preview environment by mistake, staging will hit production data—**review env vars in the host UI** before first deploy.
- **JWT / Auth**: Users in staging and production are different Supabase projects; do not expect account parity unless you sync test users deliberately.
