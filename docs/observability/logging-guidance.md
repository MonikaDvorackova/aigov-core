# Logging Guidance

Runtime observability logs should be structured, minimal, and correlated with GovAI audit traces.

## Required Correlation

Every runtime log event should include `run_id`, `tenant_id`, `policy_id`, and `audit_trace_id`. These identifiers let operators move from a dashboard panel to evidence exports without inspecting sensitive payloads.

## Recommended Fields

Use `event_name`, `event_version`, `event_time`, `severity`, `source`, `component`, `diagnostic_code`, `incident_class`, `latency_ms`, `verdict`, and `recommended_action` when relevant.

## Redaction Rules

Do not log prompts, completions, embeddings, API keys, bearer tokens, database URLs, email addresses, or raw customer payloads. Prefer opaque IDs and short diagnostic codes.

## Retention

Retention should follow the deployment operator's policy. Local examples in this repository are fixtures and should not be treated as production retention guidance.

## Local Validation

Run:

```bash
python3 scripts/observability_check.py
```

Use `--json` for deterministic machine-readable output.
