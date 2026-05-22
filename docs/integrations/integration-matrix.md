# Integration matrix

## Purpose

Provide a **single glanceable table** of developer integration surfaces, their maturity in this repository, and where to read next—reducing duplicate questions from field teams and partners.

## Integration overview

| Surface | Role | Primary docs | Example entrypoint | Validation / gate |
|--------|------|--------------|--------------------|---------------------|
| TypeScript client | In-repo `@govai/client` (`typescript-sdk/`, not on npm) | `docs/integrations/typescript-sdk.md` | `typescript-sdk/README.md` | `make typescript-client-check`; `make public-sdk-packages-check` |
| Python SDK / CLI | First-party HTTP + CLI | `docs/integrations/python-sdk.md`, `docs/cli-reference.md` | `examples/integrations/python-sdk/README.md` | `govai check`, unit tests |
| OpenAI apps | Sidecar evidence from LLM apps | `docs/integrations/openai-integration.md` | `examples/integrations/openai/README.md` | CI + `govai check` |
| LangChain | Agent/tool evidence hooks | `docs/integrations/langchain-integration.md` | `examples/integrations/langchain/README.md` | Policy-specific tests |
| MLflow | Experiment ↔ `run_id` bridge | `docs/integrations/mlflow-integration.md` | `examples/integrations/mlflow/README.md` | Promotion job gate |
| OpenTelemetry | Trace correlation | `docs/integrations/opentelemetry-integration.md` | `examples/integrations/opentelemetry/README.md` | Observability smoke |
| Webhooks / connectors | Vendor → evidence mapping | `docs/integrations/webhooks-and-connectors.md` | `examples/adoption/github-actions-ci-gate/` | Signature + idempotency tests |
| CI/CD (GitHub Actions) | Artefact-bound composite action | `docs/github-action.md` | `examples/ci/govai-check.yml` | `verify-evidence-pack` |

**Maturity legend:** TypeScript and Python clients ship in-repo; public npm publication follows `docs/integrations/sdk-roadmap.md` when release engineering signs off.

## Implementation steps

1. **Pick a row** that matches your stack; read the linked doc end-to-end.
2. **Copy the nearest example** README into your monorepo as a starting template—not as production config.
3. **Wire gates** — always know whether you need hosted verdict checks, interchange validation, or both (`docs/standards/conformance.md`).
4. **Record decisions** — update your internal ADR with which `run_id` scheme and digest artefacts you selected.
5. **Revisit quarterly** — SDK and action pins drift; align with `CHANGELOG.md` and release manifest.

## Validation

- `python3 scripts/developer_integrations_check.py`
- `make sdk-ecosystem-check` before tagging releases that claim new integration support.

## Failure modes

- **Matrix treated as law** — the table summarizes guidance, not contractual SLAs. Mitigation: refer to operator agreements for hosted commitments.
- **Skipping digest columns** — teams mark CI as done using only `compliance-summary`. Mitigation: for production promotion, use artefact-bound flows where required.
- **Stale links** — docs move between phases. Mitigation: `make docs-links-strict` in CI.
