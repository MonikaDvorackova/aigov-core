# Developer integrations

Guides for adopting GovAI from **Python**, **TypeScript**, popular **AI/ML stacks**, **observability**, and **CI/CD**. Behaviour remains defined by `api/govai-http-v1.openapi.yaml` and operator configuration; these pages are patterns, not legal claims.

## Start here

- **[Integration matrix](integration-matrix.md)** — pick your stack row, then read the linked guide.
- **[Python SDK](python-sdk.md)** — `GovAIClient`, `govai` CLI, timeouts, exit codes.
- **[TypeScript client](typescript-sdk.md)** — In-repo `@govai/client` (`typescript-sdk/`, `private: true`, not on npm): audit HTTP + Functions 2.0 read APIs.
- **[Public SDK packages audit](../reports/public-sdk-packages-audit.md)** — Packaging and naming alignment across Python, TypeScript, and Rust components.
- **[Developer integrations manifest](developer-integrations-manifest.json)** — machine-readable index (`make developer-integrations-manifest`).

## Automation and CI

- [GitHub Actions](github-actions.md) — workflow wiring and CI artifacts.
- [CLI workflows](cli-workflows.md) — `govai` and Makefile usage from shells.
- [Automation packs](automation-packs.md) — JSON contract for commands and artifacts.
- [Local tooling](local-tooling.md) — stdlib validators and aggregate `make developer-integrations-platform-check`.

## IDE and protocols

- [MCP integration](mcp-integration.md) — local MCP bridge patterns.
- [Cursor plugin](cursor-plugin.md) — `.cursor-plugin/` bundle and checks.

## Security and operations

- [Authentication](authentication.md) — bearer tokens and headers.
- [API examples](api-examples.md) — HTTP-oriented patterns (see OpenAPI for canonical fields).
- [Troubleshooting](troubleshooting.md) — common failures in integration checks.

## AI and ML platforms

- [OpenAI integration](openai-integration.md)
- [LangChain integration](langchain-integration.md)
- [MLflow integration](mlflow-integration.md)

## Platform engineering

- [OpenTelemetry integration](opentelemetry-integration.md)
- [Webhooks and connectors](webhooks-and-connectors.md)

## Roadmap

- [SDK ecosystem roadmap](sdk-roadmap.md)
