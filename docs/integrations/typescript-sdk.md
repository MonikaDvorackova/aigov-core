# TypeScript SDK

## Purpose

Provide a **TypeScript client** for the GovAI audit HTTP API and Functions 2.0 read routes, aligned with `api/govai-http-v1.openapi.yaml`.

Package path: **`typescript-sdk/`** — public npm package **`@govai/functions-sdk`** (`publishConfig.access: public`).

## Integration overview

| Capability | Implementation |
|------------|----------------|
| Liveness | `GovAIClient.health()` → `GET /health` |
| Readiness | `GovAIClient.ready()` → `GET /ready` |
| Compliance verdict | `GovAIClient.getComplianceSummary(runId)` |
| Audit export | `GovAIClient.exportAudit(runId)` |
| Enterprise reads | `GovaiFunctionsV2Client` (Supabase JWT) |

Authentication for ledger routes: `apiKey` or `bearerToken` on `GovAIClient` (sets `Authorization: Bearer …`). Optional `defaultProject` sends `X-GovAI-Project` for metering metadata only.

Python reference: `python/govai/client.py` (`GovAIClient`).

## Implementation steps

1. **Install** — `@govai/functions-sdk@0.1.0` is publicly available on npm: `npm install @govai/functions-sdk` (verify with `npm view @govai/functions-sdk`). Build from `typescript-sdk/` when developing the SDK in this monorepo.
2. **Import** — `import { createGovAIClient } from "@govai/functions-sdk"`.
3. **Configure** — `baseUrl`, `apiKey` or `bearerToken`, optional `defaultProject`.
4. **Probe** — `await client.health()` and `await client.ready()` before ledger reads.
5. **Gate on verdict** — use `getComplianceSummary` and branch on `summary.ok` / `summary.verdict`.
6. **Export** — `await client.exportAudit(runId)` for machine-readable audit JSON.

## Usage

```typescript
import { createGovAIClient } from "@govai/functions-sdk";

const client = createGovAIClient({
  baseUrl: process.env.GOVAI_AUDIT_BASE_URL!,
  apiKey: process.env.GOVAI_API_KEY,
});

await client.health();
await client.ready();

const summary = await client.getComplianceSummary("my-run-id");
if (summary.ok) {
  console.log(summary.verdict);
}

const exportJson = await client.exportAudit("my-run-id");
```

See `typescript-sdk/README.md` and `examples/integrations/typescript-sdk/README.md`.

## Validation

- `make typescript-client-check` — typecheck, build, unit tests
- `make public-sdk-packages-check` — product copy and required client files
- `make npm-typescript-publishing-check` — npm metadata, docs, and publishing manifest
- `make sdk-ecosystem-check` — doc links + integrations layout

## Failure modes

- **Invalid JSON shape** — client validates core response fields and throws `GovAIHTTPError`.
- **Secrets in the browser** — proxy API keys server-side.
- **Verdict vs HTTP 200** — treat `summary.verdict` as the gate, not status code alone.
