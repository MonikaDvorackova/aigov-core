# Runtime Observability

GovAI runtime observability is an operational layer around runtime governance. It helps operators correlate runtime events, dashboards, incidents, and audit traces without changing enforcement behavior or compliance verdict semantics.

Start with the canonical observability docs:

- [Runtime telemetry contract](../observability/runtime-telemetry-contract.md)
- [Event taxonomy](../observability/event-taxonomy.md)
- [Dashboard guidance](../observability/operational-dashboards.md)
- [SLO and SLA guidance](../observability/slo-and-sla-guidance.md)
- [Incident response](../observability/incident-response.md)
- [Logging guidance](../observability/logging-guidance.md)

Machine-readable fixtures start at [`../../observability/runtime-event-schema.json`](../../observability/runtime-event-schema.json) and local examples start at [`../../examples/observability/README.md`](../../examples/observability/README.md).

Validation:

```bash
python3 scripts/observability_check.py
make observability-check
make observability-check
```
