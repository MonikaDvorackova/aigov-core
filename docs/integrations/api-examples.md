# API examples

## Purpose

Provide HTTP-oriented examples complementary to `api/govai-http-v1.openapi.yaml`, focusing on evidence posting, compliance summary reads, and health checks—without duplicating OpenAPI field-by-field.

## Integration overview

GovAI v1 centres on `POST /evidence` and `GET /compliance-summary`. Language SDKs wrap these; raw `curl` examples live in customer quickstarts. Developer-integrations manifests reference this page as the bridge between REST semantics and automation argv patterns.

## Implementation steps

1. Read `docs/customer-quickstart.md` and OpenAPI for canonical request shapes.
2. Set bearer `Authorization` and optional `X-GovAI-Project` per operator policy.
3. Map HTTP failures to retry policy (idempotent GETs only).
4. Record `run_id` from responses for later export and audit correlation.

## Validation

- `make local-demo-curl` for read-only probes when a service is running
- `python3 scripts/validate_standard_conformance.py` for interchange JSON separate from HTTP
- `make developer-integrations-manifest` to ensure this doc stays indexed

## Failure modes

- **Treating OpenAPI as legal proof** — schemas describe interfaces, not regulatory outcomes. Mitigation: align claims with `docs/trust/trust-model.md`.
- **Missing /ready gating** — posting evidence before DB readiness causes confusing errors. Mitigation: poll `GET /ready` first in scripts.
