# GovAI Release Checklist

This checklist helps validate release readiness for GovAI.

## CI and validation

- [ ] Python tests pass
- [ ] Rust tests pass
- [ ] cargo check passes
- [ ] GitHub Actions pass
- [ ] Evidence verification flows pass
- [ ] Runtime enforcement tests pass
- [ ] No unexpected snapshot or schema diffs

## Governance validation

- [ ] VALID semantics verified
- [ ] INVALID semantics verified
- [ ] BLOCKED semantics verified
- [ ] Fail-closed behavior verified
- [ ] Human approval flows verified
- [ ] Evidence continuity verified
- [ ] Tenant isolation checks verified

## Security review

- [ ] No secrets committed
- [ ] API key handling reviewed
- [ ] Security-sensitive changes reviewed
- [ ] Cryptographic verification flows validated
- [ ] Replay protections reviewed

## Documentation

- [ ] README updated if needed
- [ ] New configuration documented
- [ ] New APIs documented
- [ ] Migration notes added if needed
- [ ] Examples updated if needed

## Operational checks

- [ ] /health semantics unchanged
- [ ] /ready semantics validated
- [ ] Database migrations validated
- [ ] Ledger persistence validated
- [ ] Deployment guidance updated if needed

## OSS and community

- [ ] Relevant issues linked
- [ ] RFC linked if applicable
- [ ] Changelog or release notes prepared
- [ ] Contributor-facing breaking changes documented

## Final review

- [ ] Release candidate reviewed
- [ ] No known critical regressions
- [ ] Release approved
