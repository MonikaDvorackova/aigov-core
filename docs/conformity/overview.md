# Overview

The EU AI Act assigns providers and deployers concrete obligations across the lifecycle of high-risk AI systems. GovAI cannot grant conformity, but it can give regulatory, engineering, and operations teams a **shared, machine-readable structure** for the workflows that surround a conformity assessment.

This section couples narrative guides with the JSON artefacts indexed by [`../../conformity/regulatory-workflow-manifest.json`](../../conformity/regulatory-workflow-manifest.json) so dossiers, risk reviews, post-market monitoring, and incident reporting use the same vocabulary.

## Principles

1. **Provider obligations are operator-owned** — GovAI structures the workflows; legal sufficiency is decided by counsel and competent authorities.
2. **Evidence over assertions** — Where a workflow step benefits from a reproducible artefact, the bundle points at the export script that can produce it.
3. **Human approvals are explicit** — Each workflow phase names the roles expected to sign off, mirroring the role hierarchy used elsewhere in the repository.
4. **Indicative, not exhaustive** — The AI Act and its implementing acts evolve; the bundle is a working aid that complements primary sources, not a substitute for them.
5. **Read-only contracts** — Workflow JSON files do not drive runtime decisions; they document operator processes.

## Boundaries

The conformity bundle does **not**:

- modify `VALID`, `INVALID`, or `BLOCKED` semantics;
- assign legal liability or substitute for legal counsel;
- replace database migrations, storage layout, or Rust runtime enforcement;
- transmit notifications to national authorities or notified bodies.

## Related material

- Obligation index: [`../regulatory/ai-act-obligations.json`](../regulatory/ai-act-obligations.json)
- Regulator-facing export guide: [`../regulatory/regulator-export-guide.md`](../regulatory/regulator-export-guide.md)
- Existing regulatory documentation: [`../regulatory/README.md`](../regulatory/README.md)
- Runtime safety and human oversight: [`../runtime-safety/README.md`](../runtime-safety/README.md)
