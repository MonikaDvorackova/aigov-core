## Summary

Describe what this PR changes.

## Target branch check

- [ ] This PR targets `staging` for normal feature, documentation, or contributor work.
- [ ] This PR targets `main` only if it is a maintainer promotion PR from `staging`.

GovAI branch workflow:

```text
feature branch -> staging -> main
```

Contributor PRs should normally look like:

```text
your-feature-branch -> staging
```

Do not open contributor PRs from `main`.

## Checklist

- [ ] I used a dedicated feature branch, not `main`.
- [ ] Documentation was updated if behavior changed.
- [ ] Relevant tests or checks were run (for OSS ecosystem docs: `make oss-ecosystem-check` when applicable).
- [ ] For core changes, an audit report exists under `docs/reports/*.md` (see [`docs/community/maintainer-guide.md`](../docs/community/maintainer-guide.md)).
- [ ] Governance RFC followed when required ([`docs/community/rfc-process.md`](../docs/community/rfc-process.md)).

## Related issue

Closes #
