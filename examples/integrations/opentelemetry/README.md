# OpenTelemetry + GovAI example

Instrument **your** HTTP client spans around GovAI calls.

## Outline

1. Initialize OTel SDK + OTLP exporter in your service.
2. Wrap `GovAIClient.request_json` (or raw `fetch`) with `tracer.start_as_current_span("govai.compliance_summary")`.
3. Attach attributes: `govai.run_id`, `http.status_code`; never attach bearer tokens.

## Docs

`docs/integrations/opentelemetry-integration.md`.
