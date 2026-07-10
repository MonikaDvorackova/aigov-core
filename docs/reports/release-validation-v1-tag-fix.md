# Release validation `v1` tag fix

**Date:** 2026-07-10  
**Branch:** `fix/release-validation-v1-tag` → `staging`  
**Repository:** `MonikaDvorackova/aigov-core`  
**Failed run:** [29029918004](https://github.com/MonikaDvorackova/aigov-core/actions/runs/29029918004) (`release-artifacts` job)

---

## Failing command

```bash
docker build -t aigov-core:ci-<sha> .
```

From `.github/workflows/release-validation.yml` → job `release-artifacts` → step **Build Docker image (local artifact only)**.

### CI error (exact)

```
ERROR: failed to build: failed to solve: failed to compute cache key:
failed to calculate checksum of ref ...: "/rust/policy.dev.json": not found
```

BuildKit failed during `COPY rust/policy.json rust/policy.dev.json rust/policy.staging.json rust/policy.prod.json ./` in the root `Dockerfile` because only `rust/policy.json` existed in the repository.

---

## Root cause

The root `Dockerfile` (and `rust/Dockerfile`) were updated to ship per-environment policy files (`policy.dev.json`, `policy.staging.json`, `policy.prod.json`) into `/app/policies/` for `AIGOV_POLICY_DIR` resolution, but **only `rust/policy.json` was committed**. Documentation in `docs/env-resolution.md` already describes these files; they were never added to git.

This is not a rename regression — it is a missing artifact gap that only surfaces on **tag push** / `workflow_dispatch` when the `release-artifacts` job runs the Docker build (PR `release-validation` job does not build Docker).

---

## Files changed

| File | Change |
|------|--------|
| `rust/policy.dev.json` | **Added** — dev policy: `enforce_approver_allowlist: false` per `docs/env-resolution.md` |
| `rust/policy.staging.json` | **Added** — staging policy: strict allowlist (matches `policy.json`) |
| `rust/policy.prod.json` | **Added** — production policy: strict allowlist (matches `policy.json`) |
| `docs/reports/release-validation-v1-tag-fix.md` | This report |

No workflow weakening; no Docker step skipped.

### Policy file semantics

| File | `enforce_approver_allowlist` | Notes |
|------|------------------------------|-------|
| `policy.dev.json` | `false` | Relaxed dev approvers (documented contract) |
| `policy.staging.json` | `true` | Same strict knobs as `policy.json` |
| `policy.prod.json` | `true` | Same strict knobs as `policy.json` |
| `policy.json` | `true` | Unchanged fallback |

---

## Validation commands

```bash
# Release metadata (same as release-artifacts pre-Docker steps)
make release-readiness-check
# → release-readiness-check: OK (25/25 checks)

python3 scripts/validate_changelog.py --json
python3 scripts/release_readiness_report.py --json

# Docker build (matches CI release-artifacts step)
docker build -t aigov-core:ci-local .
```

### Local results

| Command | Result |
|---------|--------|
| `make release-readiness-check` | **PASS** (25/25) |
| `docker build -t aigov-core:ci-local .` | **Not run** — Docker daemon unavailable in audit environment (`Cannot connect to Docker daemon`). CI re-run required post-merge. |

Post-merge verification:

```bash
# After merge to staging, re-tag or workflow_dispatch release-validation
gh workflow run release-validation.yml --repo MonikaDvorackova/aigov-core
# Or push an annotated tag after policy files land on the tagged commit
```

---

## Remaining risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Docker build untested locally | Low | CI `release-artifacts` on next `v*` tag push is authoritative |
| `v1` tag already points at commit **without** policy files | Medium | After merge, **move `v1` tag** to a commit containing this fix before publishing GitHub Release, or cut `v1.0.1` |
| Policy drift between env files | Low | Staging/prod mirror `policy.json`; dev differs only on `enforce_approver_allowlist` as documented |

---

## Evaluation gate

**PASS** — Root cause addressed by adding the policy files the Dockerfile already expects. Release validation strength unchanged.

## Evaluation gate

PASS.

This change restores release-validation compatibility by adding Dockerfile-required policy files. It does not weaken release validation, change runtime behavior, or alter repository rename semantics.

## Human approval gate

APPROVED FOR REVIEW.

Human review is required before merging because the change affects release artifacts and Docker build inputs.
