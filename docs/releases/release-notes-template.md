# Release notes template

## Purpose

Standardise **operator- and integrator-readable** release notes so every GovAI release communicates impact, upgrade steps, and governance-relevant behaviour consistently.

## Policy

- Every **tagged** release ships notes that include: **Summary**, **Upgrade notes**, **Compatibility**, **Security** (or explicit “none”), **Contributors** (optional), and **Artefacts** (SBOM links, CLI wheel locations) when applicable.
- Notes must align with **CHANGELOG.md** for the same version; discrepancies are treated as **release blockers**.
- Breaking changes require **migration** steps and link to [compatibility-policy.md](compatibility-policy.md) / [deprecation-policy.md](deprecation-policy.md) as appropriate.

## Maintainer actions

- Copy the skeleton below into GitHub Releases (or your channel) and replace placeholders.

```markdown
## GovAI vX.Y.Z

### Summary
- …

### Upgrade notes
- …

### Compatibility
- Semver: MAJOR|MINOR|PATCH per docs/releases/versioning-policy.md
- …

### Security
- CVE / advisory references, or: “No security-relevant changes in this release.”

### Contributors
- Thanks @…

### Verification
- make release-readiness-check
- …
```

## Contributor expectations

- Add **CHANGELOG** bullets under **Unreleased** when your change is user-visible; maintainers fold them into the template at release time.

## Failure modes

- **Marketing-only notes** without verification commands erode trust — mitigated by the **Verification** section.
- **Undocumented breaking HTTP or CLI** — mitigated by semver policy and reviewer checklist.
