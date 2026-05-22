# Authentication

## Purpose

Document authentication expectations for GovAI HTTP APIs and local tooling: bearer tokens, optional project headers, and separation from Stripe or dashboard sessions.

## Integration overview

Hosted and self-hosted audit APIs expect `Authorization: Bearer <GOVAI_API_KEY>`. Project scoping may use `X-GovAI-Project` as metadata; authoritative tenancy remains operator-configured. Developer integrations validators and manifests never embed secrets—they only reference env var **names** and doc paths.

## Implementation steps

1. Issue API keys per environment; rotate on compromise.
2. Store keys in CI secrets (GitHub Actions, GitLab variables, etc.).
3. For local scripts, use `.env` (uncommitted) per `docs/project/local_development.md`.
4. Avoid logging headers or token material.

## Validation

- `make security-trust` for broader trust documentation presence
- `python3 scripts/developer_integrations_check.py --json`
- Review `docs/integrations/developer-integrations-manifest.json` `authentication_model` summary

## Failure modes

- **Key reuse across prod and staging** — increases blast radius. Mitigation: separate keys and URLs per environment.
- **Assuming X-GovAI-Project enforces RBAC** — semantics vary by deployment. Mitigation: read operator docs for your tenant model.
