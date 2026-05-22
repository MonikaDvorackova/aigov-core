# AI Act conformity automation and regulatory workflows

This section describes the **EU AI Act conformity automation layer**: machine-readable workflow artefacts under the repository-root `conformity/` directory, operator-facing narrative guides in this folder, and a stdlib validator at [`../../scripts/conformity_workflow_check.py`](../../scripts/conformity_workflow_check.py). It complements the obligation index in [`../regulatory/ai-act-obligations.json`](../regulatory/ai-act-obligations.json) and the existing regulatory evidence material in [`../regulatory/README.md`](../regulatory/README.md).

## Machine-readable bundle

| File | Purpose |
| --- | --- |
| [`../../conformity/regulatory-workflow-manifest.json`](../../conformity/regulatory-workflow-manifest.json) | Index of workflow artefacts, documentation paths, examples, and explicit non-goals. |
| [`../../conformity/conformity-assessment-workflow.json`](../../conformity/conformity-assessment-workflow.json) | Conformity assessment workflow (Article 43) with phases, inputs, outputs, and audit events. |
| [`../../conformity/ai-act-control-mapping.json`](../../conformity/ai-act-control-mapping.json) | Indicative mapping from AI Act obligations to GovAI repository controls. |
| [`../../conformity/technical-documentation-workflow.json`](../../conformity/technical-documentation-workflow.json) | Annex IV technical documentation workflow (sections, lifecycle, retention). |
| [`../../conformity/risk-management-workflow.json`](../../conformity/risk-management-workflow.json) | Article 9 risk management lifecycle (identify, analyze, treat, evaluate, monitor). |
| [`../../conformity/post-market-monitoring-workflow.json`](../../conformity/post-market-monitoring-workflow.json) | Article 72 post-market monitoring categories, cadence, and escalation routes. |
| [`../../conformity/incident-reporting-workflow.json`](../../conformity/incident-reporting-workflow.json) | Article 73 serious incident reporting triggers, steps, and indicative deadlines. |

## Narrative guides

| Topic | Document |
| --- | --- |
| Scope and principles | [overview.md](overview.md) |
| Conformity assessment workflow | [conformity-assessment-workflow.md](conformity-assessment-workflow.md) |
| AI Act control mapping | [ai-act-control-mapping.md](ai-act-control-mapping.md) |
| Annex IV technical documentation | [technical-documentation-workflow.md](technical-documentation-workflow.md) |
| Risk management lifecycle | [risk-management-workflow.md](risk-management-workflow.md) |
| Post-market monitoring | [post-market-monitoring-workflow.md](post-market-monitoring-workflow.md) |
| Serious incident reporting | [incident-reporting-workflow.md](incident-reporting-workflow.md) |

## Validation

From the repository root:

```bash
python3 scripts/conformity_workflow_check.py
make conformity-workflow-check
make regulatory-workflow-check
```

These checks assert workflow file presence and JSON shape, cross-reference each control with a known AI Act obligation, validate that Makefile and example wiring exist, and confirm that linked regulatory references resolve. They do **not** change compliance verdict semantics, Rust runtime enforcement, or database migrations.
