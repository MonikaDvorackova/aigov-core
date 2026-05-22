# Secure deployment checklist

Use this checklist when promoting GovAI from pilot to production. It complements automated gates (for example **`make enterprise-readiness-check`** in CI) with **environment-specific** controls.

## Identity and access

- [ ] API keys are **unique per tenant** where isolation is required.
- [ ] Database roles follow **least privilege** (app role vs migration role).
- [ ] Break-glass accounts are **rare**, **monitored**, and **documented**.

## Network

- [ ] Audit API is not exposed on the public internet without TLS termination and rate limits.
- [ ] Admin interfaces (DB, dashboard) are on **private** networks or IP allowlists.

## Data protection

- [ ] Encryption **in transit** (TLS) end-to-end for client → API and API → datastore.
- [ ] Encryption **at rest** enabled for Postgres/object storage per your policy.
- [ ] Backups are **encrypted** and **restored-tested** on a schedule.

## Configuration

- [ ] Secrets injected via a **secret manager**, not plaintext in repos.
- [ ] `GOVAI_*` and related env vars reviewed against [secrets-management.md](secrets-management.md).
- [ ] Auto-migration flags (`GOVAI_AUTO_MIGRATE`, etc.) understood for your environment.

## Observability

- [ ] Structured logs **omit** bearer tokens and raw keys.
- [ ] Alerts on error rate, latency, and auth failures baseline deviations.

## Supply chain

- [ ] Pin container base images and rebuild on CVE announcements.
- [ ] Verify SBOM or dependency scanning in CI for Rust and Python crates.

## Related reading

- [security-overview.md](security-overview.md)
- [../../docs/hosted-pilot-runbook.md](../../docs/hosted-pilot-runbook.md) (hosted path)
