# Post-market monitoring workflow

The [`post-market-monitoring-workflow.json`](../../conformity/post-market-monitoring-workflow.json) artefact describes the categories of monitoring providers establish after a high-risk AI system is placed on the market (Article 72).

## Monitoring categories

| Category | Examples |
| --- | --- |
| Performance drift | Accuracy windows, false positive rate, calibration error. |
| Operational stability | Availability, p95 latency, saturation. |
| Safety signals | Guardrail invocations, overrides, kill-switch activations. |
| User feedback | Complaint volume and categorization. |

Each category links to existing observability or runtime-safety material in this repository so operators can wire metrics into the same dashboards they already maintain.

## Cadence

`review_cadence` requires at least monthly review, immediate review after incidents, and an annual summary. Operators usually align this with their existing service review schedule.

## Escalation routes

Three escalation routes are documented: internal engineering, internal governance, and authority notification. The third route invokes the [incident reporting workflow](incident-reporting-workflow.md) when criteria are met.

## Boundaries

Thresholds, on-call coverage, and exact metric definitions remain **operator-defined**. GovAI does not enforce regulator-specific thresholds automatically.
