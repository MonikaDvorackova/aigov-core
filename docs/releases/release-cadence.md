# Release cadence

## Purpose

Set **default expectations** for how often GovAI cuts releases and what types of changes batch together, while allowing maintainers to accelerate for security or blocking fixes.

## Policy

- **Regular cadence (target):** maintainers aim for a **MINOR** or **PATCH** release at least **monthly** when non-trivial changes accumulated on **staging**, subject to maintainer availability — this is a guideline, not a guarantee.
- **PATCH** releases may ship **ad hoc** for documentation corrections, deterministic check fixes, and non-breaking bug fixes.
- **Security releases** ship according to [security-release-process.md](security-release-process.md), potentially off-cycle.
- **MAJOR** releases batch breaking changes with migration guides and extended soak time on **staging** when possible.

## Maintainer actions

- Review open PRs on **staging** during cadence check-ins; decide **PATCH** vs **MINOR** vs defer.
- Communicate schedule slips via maintainer channels (for example Discord or governance discussion).

## Contributor expectations

- Target **staging** for merge-ready work; avoid requesting arbitrary mid-week tags without maintainer agreement.

## Failure modes

- **Large batch merges** increase regression risk — mitigated by checklist and automated gates.
- **Starvation** of releases demotivates contributors — mitigated by lightweight **PATCH** doc releases when code is quiet.
