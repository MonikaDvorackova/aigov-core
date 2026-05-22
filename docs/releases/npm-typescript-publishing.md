# npm publishing — GovAI TypeScript SDK

Manual release guide for **`@govai/functions-sdk`** (`typescript-sdk/`). This document does **not** publish anything automatically; maintainers run commands locally or in a guarded release workflow after explicit approval.

## Registry verification (current)

| Field | Value |
| --- | --- |
| Package | `@govai/functions-sdk` |
| Published version | `0.1.0` (2026-05-18) |
| Consumer install | `npm install @govai/functions-sdk` |
| Verify | `npm view @govai/functions-sdk` |

Integrators should pin a semver range in `package.json` (for example `^0.1.0`) per `docs/releases/compatibility-policy.md`.

## Package identity

| Field | Value |
|-------|--------|
| npm package name | `@govai/functions-sdk` |
| Package directory | `typescript-sdk/` |
| Manifest | `docs/releases/npm-typescript-publishing-manifest.json` |
| Readiness validator | `make npm-typescript-publishing-check` |

## Preconditions

1. **Human approval** — a maintainer has signed off on version, changelog notes, and consumer impact (see `docs/reports/npm-typescript-publishing-readiness-audit.md`).
2. **Automated gate green** — `make npm-typescript-publishing-check` and `pytest python/tests/test_npm_typescript_publishing_check.py` pass on the release commit.
3. **npm account** — publisher is a member of the `@govai` org (or agreed scope) with permission to publish this package.
4. **2FA** — npm account uses **two-factor authentication**; org policy should require **2FA for publish** (recommended: `auth-and-writes` or stricter).
5. **No secrets in git** — tokens live only in CI secrets or local `~/.npmrc`, never committed.

## Build and test

From the repository root:

```bash
cd typescript-sdk
npm ci
npm run typecheck
npm run build
npm test
```

Or from the root workspace:

```bash
npm run build --prefix typescript-sdk
npm test --prefix typescript-sdk
```

Expected build outputs (after `npm run build`):

- `typescript-sdk/dist/index.js`
- `typescript-sdk/dist/index.d.ts`

## Dry run (no registry upload)

Validate the tarball contents without publishing:

```bash
cd typescript-sdk
npm pack --dry-run
```

Inspect the generated tarball name and file list. Confirm `dist/`, `README.md`, and `package.json` are included and that no `.env`, `.npmrc`, or credential files appear.

Optional stricter dry run (creates a local `.tgz` without uploading):

```bash
cd typescript-sdk
npm pack
tar -tzf govai-functions-sdk-*.tgz | head
rm govai-functions-sdk-*.tgz
```

## Publish dry run (registry metadata only)

npm does not offer a true “publish dry run” that hits the registry without side effects. Use this sequence instead:

1. `npm pack --dry-run` (above).
2. Bump version only on a release branch after review.
3. Publish to a **private test scope or npm provenance staging org** only if your org provides one; otherwise skip registry trials and rely on pack + CI validators.

**Do not** run `npm publish` in CI for this repository unless a dedicated, manually approved release workflow is added later.

## Required npm permissions

- **Publish**: `npm publish` for `@govai/functions-sdk` (scoped package; `publishConfig.access` is `public`).
- **Org**: maintainers need **publish** rights on the `@govai` scope or package-level collaborators.
- **CI** (if used later): restricted automation token with **minimal** publish scope, stored as a GitHub Actions secret — never committed to the repo.

## Two-factor authentication policy

- Enforce **2FA on all maintainer npm accounts** before granting publish access.
- Prefer npm org setting **“Require two-factor authentication or SSO”** for members.
- For automation, use **trusted publishing** (OIDC) or granular tokens with expiration instead of long-lived passwords.

## Provenance recommendation

When publishing from GitHub Actions in the future, enable **[npm provenance](https://docs.npmjs.com/generating-provenance-statements)** so consumers can verify the package was built from this repository. For local publishes, document the git tag and commit in the GitHub release notes.

## Versioning and compatibility

Follow `docs/releases/versioning-policy.md` and `docs/releases/compatibility-policy.md`. Bump `typescript-sdk/package.json` `version` in the same PR as release notes when cutting a release.

## Rollback and deprecation

| Situation | Action |
|-----------|--------|
| Bad version just published | **Deprecate** immediately: `npm deprecate @govai/functions-sdk@<version> "reason"` |
| Must stop all installs | Deprecate with message pointing to a fixed version; do not unpublish if consumers may already depend on the tarball |
| Security issue | Follow `docs/releases/security-release-process.md`; deprecate affected versions and publish a patch |

Unpublishing (`npm unpublish`) is discouraged for public packages after wide adoption; prefer deprecation.

## Manual approval before publishing

Checklist for the releasing maintainer:

- [ ] Release PR merged to the agreed branch with version bump and changelog.
- [ ] `make npm-typescript-publishing-check` green on the release commit.
- [ ] `npm pack --dry-run` reviewed.
- [ ] Second maintainer acknowledged breaking changes (if any).
- [ ] `npm publish --access public` run **only** from an approved environment with 2FA.
- [ ] Git tag and GitHub release created documenting the commit and npm version.

**This repository’s CI does not run `npm publish`.**
