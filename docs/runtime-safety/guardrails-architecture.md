# Guardrails architecture

Guardrails sit **before and around** model and tool execution. In GovAI-aligned deployments they typically include:

1. **Input controls** — schema validation, injection heuristics, and size or rate limits.
2. **Tool policy** — allowlists, argument validators, and separation between read-only and mutating tools.
3. **Output controls** — content filters and policy-linked post-checks that never replace the audit verdict but reduce blast radius upstream.

## Telemetry fields

The Phase 21 snapshot captures **counts and latency** only (see the manifest signal IDs). Operators map these fields from their own logging and safety stacks.

## Design principles

- **Fail closed** where policy requires it; surface `BLOCKED` or upstream rejection before silent degradation.
- **Observable guardrails** — every deny path should log a stable reason code for later audit correlation.
- **Latency budget** — guardrail chains should stay within an explicit P95 budget so safety does not starve availability.

## Non-goals

This document does not prescribe a specific vendor stack or model family. It does not alter GovAI verdict semantics.
