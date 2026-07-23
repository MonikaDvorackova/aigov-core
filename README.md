# CLA signatures branch (`cla-signatures`)

**Purpose:** Store Contributor License Agreement signature records for **aigov-core** only.

**Not for:** application development, releases, or general documentation.

**Writer:** `github-actions[bot]` via the CLA Assistant Lite workflow (`.github/workflows/cla.yml` on `main`/`staging`), using `GITHUB_TOKEN`. Maintainers may repair this branch if a signature write fails.

**Expected file (created by the action on first signature — do not create manually):**

`signatures/version1/cla.json`

**Recovery if a signature write fails:**

1. Confirm this branch is **not** covered by repository rulesets that require PRs or status checks.
2. Confirm the CLA workflow `branch:` input is `cla-signatures`.
3. Re-run by commenting `recheck` on the pull request, or push an empty commit to retrigger `pull_request_target`.
4. Inspect the failed Actions run log for rule-violation messages.
5. Do **not** grant broad write bypass on `main`/`staging` to fix signature storage.
