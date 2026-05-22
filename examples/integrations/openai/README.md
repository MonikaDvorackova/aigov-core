# OpenAI + GovAI example

Demonstrates the **sidecar evidence** pattern: OpenAI SDK calls stay in your app; GovAI receives structured events.

## Outline

1. Call OpenAI with your preferred SDK and model.
2. Build a compact JSON evidence payload referencing `run_id`, model id, and policy-required fields (no secrets).
3. `POST /evidence` using `GovAIClient` or `curl`.
4. `govai check` before deploy.

## Docs

`docs/integrations/openai-integration.md`.
