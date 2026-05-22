# Release security checklist (security program v0)

`SEC_PROGRAM_RELEASE`

- [ ] Confirm dependency updates reviewed (Rust `cargo deny` / advisory tooling if configured in your org).
- [ ] Run `make gate` and bounded stabilization checks before tagging.
- [ ] Verify migration ordering for Postgres in staging before production.
- [ ] Validate signing keys and `GOVAI_API_KEYS` / `GOVAI_API_KEYS_JSON` consistency in staging/prod.
- [ ] Document any operator-visible behavior change in `CHANGELOG.md` or release notes.

This checklist does **not** assert penetration testing was executed.
