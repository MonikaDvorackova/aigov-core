# GovAI Documentation Website Plan

## Purpose

This document defined early options for a standalone documentation website. **Current decision:** the **production reader surface** is the **`dashboard/`** Next.js application on **govbase.dev**, exposing **`/docs`** and **`/help`** with content loaded from the canonical **`docs/`** Markdown tree (the same files contributors edit in GitHub).

Historical alternatives (Mintlify scaffold under `docs-site/`, Vite app under `docs-web/`) are **removed from this repository** to avoid duplicate sources of truth.

## Production shape (now)

- **Content:** `docs/**/*.md` (strict link checking via existing scripts).
- **Rendering:** `dashboard/app/docs`, `dashboard/app/help`, `react-markdown` + `remark-gfm`.
- **Registry:** `dashboard/lib/publicSite/publicDocsRegistry.ts` maps slugs → repo-relative Markdown paths.
- **Search:** client-side filter over registry titles, descriptions, slugs, and optional `searchText` tokens (no third-party search host).
- **Analytics:** optional `window.__GOVBASE_PUBLIC_ANALYTICS__` hook + conversion helpers (`dashboard/lib/publicSite/conversionTracking.ts`); default is a no-op.

## Documentation goals (unchanged)

The documentation experience should still help users:

- Understand the GovAI governance model
- Run local and hosted flows quickly
- Integrate GovAI into CI/CD pipelines
- Understand evidence bundles and digest continuity
- Understand the audit server and readiness model
- Evaluate tenant isolation guarantees
- Contribute safely to the project
- Understand the roadmap and compatibility policy

## Versioning strategy

Documentation continues to track the repository default branch; versioned doc sets remain a **future** enhancement when a stable public release line warrants it.

## Related

- Audit / completion record: [`../reports/dashboard-docs-help-routes.md`](../reports/dashboard-docs-help-routes.md)
- Local preview: [`local_development.md`](local_development.md) (`cd dashboard && npm run dev`)
