# Deployment environments

Related: [Branching strategy](branching-strategy.md) · [Database environments](database-environments.md)

This repository is **infrastructure- and docs-first**: application behavior is unchanged; deployment wiring is mostly **Vercel (or similar) + environment variables** configured outside git.

## Environment model

| Environment | Typical use | Git ref | Deployment intent |
|-------------|-------------|---------|-------------------|
| **Local** | Developer machine | any branch | `next dev` / local services; `.env.local` (not committed). |
| **Staging** | Integration & QA | `staging` | **Non-production** URL; preview/staging config and DB (see database doc). |
| **Production** | Live users | `main` | **Production** URL; production config and DB only. |

## What this repo contains

- **GitHub Actions**: `.github/workflows/compliance.yml` — CI (gate, tests, evidence) on PRs/pushes to `staging` and `main`. It is **not** a deployment pipeline to Vercel or elsewhere.
- **Next.js app**: `dashboard/` (likely the deploy root for hosting).
- **No `vercel.json` in-repo** at time of writing; Vercel behavior is configured in the **Vercel project dashboard** unless you add a config file later.

## Vercel (recommended layout)

Configure in the **Vercel project** (exact UI names may vary):

1. **Connect the GitHub repo** and set **Root Directory** to `dashboard` if the Vercel project root is the monorepo root.
2. **Production branch**: **`main`** — deployments from `main` are **production**.
3. **Preview deployments**: enabled for other branches (including **`staging`**). The `staging` branch should get a **stable preview URL** for that branch (Vercel creates per-branch preview URLs; pinning QA to `staging` avoids relying on every feature preview).

### Branch → environment mapping

| Git branch | Vercel target | Notes |
|------------|---------------|--------|
| `main` | **Production** | Customer-facing domain; production env vars. |
| `staging` | **Preview** (treat as staging) | Use **Preview**-scoped or **branch-specific** env vars so this deployment never uses production secrets. |
| `feature/*` | **Preview** | Ephemeral previews; not a substitute for the shared staging integration branch unless you explicitly adopt that workflow. |

### Manual settings checklist (Vercel)

- [ ] Production branch = `main`.
- [ ] **Production** environment variables: production Supabase URL/keys, production `DATABASE_URL` / `GOVAI_*` if used, production `NEXT_PUBLIC_*` where they must match prod URLs.
- [ ] **Preview** (or branch `staging`) variables: **separate** staging Supabase project or keys, **staging** database URL, staging OAuth callback URLs registered in IdP/Supabase.
- [ ] Optional: protection rules so **production** deploys only from `main` (Vercel default when production branch is set).

**Do not** point staging deployments at production Supabase or production Postgres. See [Database environments](database-environments.md).

### Secrets and env vars (manual)

Add real values only in Vercel (or your host); **do not commit secrets**.

| Kind | Production | Staging / Preview |
|------|------------|-------------------|
| Supabase | Production project URL + anon/publishable key | **Different** project or credentials |
| Postgres / console | `DATABASE_URL` / `GOVAI_DATABASE_URL` for prod DB | **Different** connection string for staging DB |
| OAuth / redirects | Supabase Auth **Site URL** and redirect allowlist for prod domain | Staging/preview URLs added to the **staging** Supabase project |
| Third-party API keys | Live keys | Test/staging keys where vendors provide them |

A concrete variable inventory (names only) is in [Database environments](database-environments.md) and in code via `process.env` / `os.environ`.

## GitHub Actions deployment

There is **no** workflow in this repo that deploys to Vercel or production. If you add one later:

- Run deploy jobs only on `push` to `staging` (staging target) and `push` to `main` (production target).
- Use separate secrets, e.g. `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, and **two** tokens or projects if you split staging vs production.

## Git: `staging` branch

If `staging` does not exist locally or on the remote:

```bash
git fetch origin main
git switch -c staging origin/main    # skip if branch already exists
git push -u origin staging
```

**No automatic merges** are performed by these docs; open PRs in GitHub as usual.

## Safety (preserved by design)

- **No direct feature → production** in Vercel when production branch is `main` only.
- **CI** blocks PRs into `main` unless the head branch is `staging` (see workflow).
- **No production DB from staging** requires **distinct env vars** on the staging deployment; misconfiguration is an ops mistake—use separate Supabase projects and DBs and verify URLs before first staging deploy.

## Risks and gaps

- **OAuth**: Each Supabase project has its own redirect URL list; staging and production must each list their own app URLs.
- **Monorepo**: Wrong **Root Directory** in Vercel builds the wrong folder or fails the build.
- **Preview URL churn**: Feature branch previews may rotate; use the **`staging`** branch URL as the stable non-prod entry for QA when possible.
