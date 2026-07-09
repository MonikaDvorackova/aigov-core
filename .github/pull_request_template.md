## Summary

Describe what this PR changes.

## Target branch check

- [ ] This PR targets **`staging`** for normal feature, documentation, or contributor work.
- [ ] This PR targets **`main`** only if it is a maintainer promotion PR from `staging`.

AIGov Core branch workflow:

```text
feature branch → staging → main
```

Contributor PRs should normally look like:

```text
your-feature-branch → staging
```

Do not open contributor PRs directly into `main`.

## Core invariants (when touching runtime or evidence)

If this PR changes `rust/`, evidence ingest, compliance summary, export, verify, or API key handling, confirm:

- [ ] Append-only ledger semantics preserved (no silent overwrites; duplicate `event_id` still rejected).
- [ ] Tenant isolation unchanged (`GOVAI_API_KEYS` + `GOVAI_API_KEYS_JSON`; no implicit `"default"` tenant for unknown keys).
- [ ] `GET /ready` remains non-mutating.
- [ ] `GET /compliance-summary` remains ledger-authoritative (no side-channel verdict overrides).
- [ ] Audit export remains reproducible for the same ledger contents.

## Checklist

- [ ] I used a dedicated feature branch, not `main`.
- [ ] Documentation was updated if behavior or integrator contracts changed.
- [ ] Relevant checks were run:
  - `make gate`
  - `make core-runtime-examples-check` (if examples or runtime docs changed)
  - `make reference-integrations-check` (if reference integration examples changed)
  - `cd rust && cargo test --locked` (if Rust changed)
- [ ] For core or governance changes, an audit report exists under `docs/reports/*.md` when required (see [`docs/community/maintainer-guide.md`](../docs/community/maintainer-guide.md)).
- [ ] Governance RFC followed when required ([`docs/community/rfc-process.md`](../docs/community/rfc-process.md)).

## Scope check

- [ ] This PR does **not** add hosted SaaS, Stripe/billing, pricing, dashboard ACL, or commercial onboarding to AIGov Core.

## Related issue

Closes #
