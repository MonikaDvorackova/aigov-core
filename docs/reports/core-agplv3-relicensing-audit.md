# AIGov Core AGPL-3.0-only Relicensing Audit

## Summary

This change relicenses the current version of AIGov Core under the GNU Affero General Public License version 3 only (`AGPL-3.0-only`).

The canonical AGPL v3 license text replaces the previous Apache-2.0 license text. Package metadata, citation metadata, release-readiness validation, and the AIGov Core Cursor plugin manifest are aligned with the new license.

Historical versions remain governed by the license terms under which they were previously distributed. The relicensing does not revoke rights already granted under Apache-2.0.

AIGov Platform remains separate proprietary software and is not relicensed by this change.

## Evaluation gate

The change is accepted only if all of the following checks pass:

- `LICENSE` matches the canonical GNU AGPL v3 text.
- Rust, Python, npm, citation, and plugin metadata use `AGPL-3.0-only`.
- No active package metadata declares Apache-2.0, `LicenseRef-Proprietary`, or `UNLICENSED`.
- `python3 scripts/release_readiness_report.py` completes with score 100.
- JSON manifests parse successfully.
- `cargo metadata --no-deps` succeeds.
- repository secret scanning succeeds without requiring a commercial Gitleaks Action license.

This change does not modify AIGov Core runtime enforcement, ledger semantics, policy evaluation, API behavior, or stored evidence formats.

## Human approval gate

The change requires review and approval through the protected branch workflow.

The feature branch targets `staging`. It must not be pushed or merged directly into `main`. Promotion from `staging` to `main` remains subject to the repository's existing protected release process.

The reviewer must confirm:

- the intended `AGPL-3.0-only` licensing model;
- the boundary between AIGov Core and proprietary AIGov Platform;
- the recorded CLA coverage for retained external source-code contributions;
- preservation of historical licensing rights; and
- successful required CI checks.

## Risk assessment

The principal risks are:

- incorrectly implying that historical Apache-2.0 grants have been revoked;
- accidentally applying AGPL licensing to proprietary AIGov Platform code;
- inconsistent license identifiers across package metadata;
- retaining copyrightable contributions without sufficient relicensing rights;
- breaking CI by relying on the licensed Gitleaks GitHub Action for an organization repository; and
- bypassing the protected `staging` to `main` promotion process.

These risks are mitigated by the `NOTICE` file, explicit Core and Platform separation, aligned SPDX metadata, recorded CLA review, removal of uncovered contributions, CLI-based Gitleaks scanning, and protected branch review.

## Rollback plan

Before merge, rollback consists of closing the pull request or reverting commits on the feature branch.

After merge into `staging`, rollback consists of a signed revert of the relicensing commits through a new pull request targeting `staging`.

If already promoted to `main`, rollback must use the protected release workflow. Any rollback affects only later repository versions and cannot revoke license rights already granted to recipients under AGPL-3.0-only or earlier licenses.
