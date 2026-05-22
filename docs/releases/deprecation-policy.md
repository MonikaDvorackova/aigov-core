# Deprecation policy

## Purpose

Ensure deprecated capabilities **sunset predictably** with documented timelines, logging or headers where applicable, and semver alignment so operators are not surprised by removals.

## Policy

- A **deprecated** feature remains available for at least **one MINOR** release cycle after deprecation announcement unless security policy requires faster removal ([security-release-process.md](security-release-process.md)).
- Deprecations are announced in: **CHANGELOG.md** under **Unreleased**, **release notes**, and **documentation** near the affected command, env var, or field.
- **Removal** happens only in **MAJOR** or, for explicitly experimental surfaces, **MINOR** with clear notes per [compatibility-policy.md](compatibility-policy.md).

## Maintainer actions

- When deprecating, add **Deprecation** subsection to **Unreleased** with removal target (version window, not a vague “later”).
- Update examples and runbooks to prefer non-deprecated paths in the same or follow-up PR when feasible.

## Contributor expectations

- Prefer **additive** changes over breaking removals.
- If removal is necessary, open an RFC for governance-visible behaviour and link it from the PR.

## Failure modes

- **Silent removal** breaks automation — mitigated by semver, CHANGELOG, and release notes discipline.
- **Indefinite deprecation** confuses users — mitigated by explicit removal targets in docs.
