# TypeScript SDK example

Uses **`@govai/functions-sdk`** (`typescript-sdk/`) against a local or hosted audit service.

## Prerequisites

- Node.js 18+
- Audit service running (`make audit` or Docker Compose)
- `GOVAI_API_KEY` for tenant-scoped routes

## Install (npm)

`@govai/functions-sdk@0.1.0` is publicly available on npm.

```bash
npm install @govai/functions-sdk
npm view @govai/functions-sdk
```

## Build from monorepo

```bash
cd typescript-sdk
npm install
npm run build
```

## Run the example

```bash
export GOVAI_AUDIT_BASE_URL=http://127.0.0.1:8088
export GOVAI_API_KEY=your-key
export GOVAI_RUN_ID=demo-run

node example.mjs
```

Consumers install from npm:

```javascript
import { createGovAIClient } from "@govai/functions-sdk";
```

This example imports from the monorepo build output for local SDK development:

```javascript
import { createGovAIClient } from "../../../typescript-sdk/dist/index.js";
```

## Validation

```bash
make typescript-client-check
make npm-typescript-publishing-check
make developer-integrations-check
```
