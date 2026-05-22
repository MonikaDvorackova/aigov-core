# Secrets management

Secrets for GovAI include **API keys** to the audit service, **database credentials**, optional **Stripe** or payment keys for hosted billing, and any **signing** material used in your deployment. This page lists **patterns** that reduce accidental leakage.

## Configuration surfaces

- **Environment variables** — preferred for containers and CI. Use your platform’s secret store (Kubernetes Secrets, AWS SSM, Doppler, Vault, etc.) rather than baking values into images.
- **`.env` files** — local development only; never commit. The repository ships **`.env.example`** without live credentials.
- **`GOVAI_API_KEYS_JSON` (or equivalent)** — maps keys to tenants in multi-tenant setups. Treat the JSON as **highly confidential**; rotation requires coordinated client updates.

## CI systems

- Prefer **OIDC** or scoped short-lived tokens where your VCS provider supports them.
- Do not echo secrets in logs. Mask variables in workflow definitions when printing debug output.
- The published **GitHub Action** and local scripts expect secrets as inputs; review [../../docs/github-action.md](../../docs/github-action.md) for the minimal required parameters.

## Rotation

Plan **API key rotation** with overlap windows, client redeployments, and ledger continuity checks. Document who approves rotation and how incidents are declared (see [incident-response.md](incident-response.md)).

## Verification

- Run **`make security-trust`** locally as part of onboarding checks (documentation presence; see repository `Makefile`).
- Combine with your own secret scanning (git-secrets, Gitleaks, GitHub secret scanning) on every merge.

## Related reading

- [secure-deployment-checklist.md](secure-deployment-checklist.md)
- [../../SECURITY.md](../../SECURITY.md)
