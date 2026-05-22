# npm release checklist — `@govai/functions-sdk`

## Published release (0.1.0)

| Field | Value |
| --- | --- |
| Package | `@govai/functions-sdk` |
| Version | `0.1.0` |
| Install | `npm install @govai/functions-sdk` |
| Verify registry | `npm view @govai/functions-sdk` |

**Status (2026-05-18):** `0.1.0` is **live** on the public npm registry. Use this document for **subsequent** semver releases.

## Preconditions (every release)

- [ ] `make npm-typescript-publishing-check` passes
- [ ] `make typescript-client-check` passes
- [ ] `make public-sdk-packages-check` passes
- [ ] Human approval for version bump and consumer impact
- [ ] `@govai` npm org access and 2FA for publish

## Release steps

1. Bump version in `typescript-sdk/package.json` (semver).
2. Update changelog / release notes for integrators.
3. From `typescript-sdk/`: `npm ci && npm run typecheck && npm run build && npm test`
4. `npm publish --access public` (dry-run first: `npm publish --dry-run`)
5. Verify: `npm view @govai/functions-sdk version`
6. Update product docs if the default install pin changes.

## Post-publish

- Tag git release aligned with package version.
- Smoke test: `npm install @govai/functions-sdk@<version>` in a clean directory.

## Do not

- Mix this package with legacy private in-repo `@govai/client` naming in consumer docs.
- Claim a new version is on npm before `npm view` shows it.
