# SDK ecosystem roadmap

## Purpose

Set expectations for **what ships when** across Python, TypeScript, composite CI actions, and observability—without committing to dates in this file; maintain dates in release notes and the release manifest instead.

## Integration overview

Near-term priorities (documentation and examples in-repo):

1. **Python** — continue to treat `python/govai/client.py` and `govai` CLI as the supported developer surface; expand examples, not breaking semantics without a major version.
2. **TypeScript** — maintain the in-repo **`@govai/client`** package under `typescript-sdk/` (audit HTTP + Functions 2.0 read APIs, `private: true`). A future public **`@govai/functions-sdk`** npm release is handled on a dedicated publishing branch with separate gates — not from normal integration branches.
3. **CI** — keep the composite GitHub Action as the primary distribution for digest-bound checks; document version pins aggressively.
4. **Observability** — add more copy-paste OTel snippets as community contributions mature.
5. **Partner SDKs** — follow `docs/partners/README.md` for co-marketed wrappers; they remain **downstream** of the OpenAPI contract.

## Implementation steps (maintainers)

1. **Track issues** — label integration tasks `area:sdk` / `area:docs` in your tracker (public or internal).
2. **Contract-first** — any SDK change starts from `api/govai-http-v1.openapi.yaml` and changelog entries.
3. **Release coupling** — when adding npm packages, wire them into `make release-readiness-check` and SBOM processes already described under `docs/releases/`.
4. **Deprecation** — announce CLI flag removals in two releases per `docs/releases/versioning-policy.md`.
5. **Community examples** — accept README-only contributions under `examples/integrations/` after `developer_integrations_check` passes.

## Validation

- Before merging roadmap-adjacent PRs: `python3 scripts/developer_integrations_check.py` and `make docs-links-strict`.
- Before marketing claims: align wording with `docs/reports/repo-debt-audit-and-cleanup.md` human gate.

## Failure modes

- **Over-promising dates** — roadmap lines interpreted as contractual delivery. Mitigation: keep timelines in release manifest / external comms, not hardcoded here.
- **Fork drift** — downstream SDKs diverge from OpenAPI. Mitigation: conformance tests against pinned OpenAPI git SHA.
- **Security shortcuts** — rushing npm publish without provenance and OIDC trust. Mitigation: follow existing release engineering docs.
