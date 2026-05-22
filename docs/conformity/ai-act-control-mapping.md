# AI Act control mapping

The [`ai-act-control-mapping.json`](../../conformity/ai-act-control-mapping.json) artefact provides an **indicative** mapping from EU AI Act obligations to GovAI repository controls. The mapping is consumed by regulatory, engineering, and audit teams to locate the supporting artefacts associated with each obligation.

## How it works

- Each control entry references an `obligation_id` that **must exist** in [`../regulatory/ai-act-obligations.json`](../regulatory/ai-act-obligations.json). The validator (`scripts/conformity_workflow_check.py`) rejects unknown obligation identifiers.
- Each control has a stable `control_id`, a short `control_summary`, and a list of `supporting_artefacts` (workflow JSON, narrative docs, or scripts).
- Controls are typed as `process`, `evidence`, or `documentation` to signal what the supporting artefacts actually deliver.

## Reviewing the mapping

When reviewing a control:

1. Confirm the linked obligation reflects the binding legal text in the *Official Journal* and implementing acts.
2. Walk the `supporting_artefacts` and confirm they reflect the operator's current implementation.
3. If a control is no longer reflective of practice, update the JSON entry and the matching narrative document together.

## Caveats

The artefact's `mapping_caveats` field restates that:

- mappings are orientation aids, not certifications;
- some obligations produce records (for example signed declarations) that GovAI does not generate;
- legal compliance remains with providers and deployers.
