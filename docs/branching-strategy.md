# Branching strategy

Related: [Deployment environments](deployment-environments.md) · [Database environments](database-environments.md)

## Branches

| Branch | Role |
|--------|------|
| `feature/*`, `fix/*`, `chore/*`, … | Short-lived work. Open a **pull request into `staging`**. |
| `staging` | **Integration and pre-production.** Merges from features; deploys to the **staging / preview** stack (see deployment doc). |
| `main` | **Production only.** Updated only by merging **`staging` → `main`** via PR. Deploys to **production**. |

```text
feature/*  ──PR──▶  staging  ──PR──▶  main
                     (staging)      (production)
```

## Why `staging` exists

- **Integration**: surface merge conflicts and cross-feature issues before they hit `main`.
- **Pre-production validation**: run CI, manual QA, and staging-only data against a single integration branch.
- **Deployment safety**: bind preview/staging infrastructure and secrets to this branch, not to every feature branch.

## Why `main` is production-only

`main` should always represent what is **released or release-ready**. Keeping production deploys and production databases tied to `main` avoids accidental promotion of unreviewed work.

The **`compliance`** GitHub Actions workflow enforces that **pull requests targeting `main` must have head branch `staging`**, so feature→`main` PRs fail CI until work flows through `staging`.

## Recommended PR policy

- **Into `staging`**: required for routine feature work; use small, reviewable PRs.
- **Into `main`**: only **`staging` → `main`** promotion PRs after staging is validated.
- **Do not merge automatically** in CI; humans (or an explicit merge queue) merge after review.

## Hotfixes

Treat urgent fixes like normal delivery unless you have an **documented exception**:

1. Branch from `main` or from `staging` (team choice), implement the fix.
2. Merge to **`staging` first** (PR), verify on the staging deployment.
3. Promote **`staging` → `main`** (PR).

If process latency is unacceptable, **document** an emergency path (e.g. temporary branch protection bypass, incident owner) outside this file—do not rely on ad-hoc feature→`main` merges while the workflow guard is enabled.

## CI

The **`compliance`** workflow runs on:

- **Pull requests** with base `staging` or `main`.
- **Pushes** to `staging` and `main`.

## Branch protection (recommended, not applied by repo automation)

### `main`

- Require pull request before merging.
- Require status checks to pass (mark the jobs your team trusts, e.g. `make_verify`).
- Block direct pushes; restrict who can merge.

### `staging`

- Require pull request (supports controlled integration).
- Require **basic** CI checks (e.g. same workflow with a subset marked required, if you want faster iteration than `main`).
- Allow the integration flow: feature PRs merge into `staging`, then `staging` promotes to `main`.

### Optional

- Rulesets for both branches; merge queue for `main` if you need serialized merges.
