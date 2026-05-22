# AI Act conformity automation examples

Stdlib-only drivers for the EU AI Act conformity automation bundle under [`conformity/`](../../conformity/) (no network). Run from the repository root or use the script below (it resolves the repo root automatically).

| Script | Purpose |
| --- | --- |
| [`run-conformity-workflow-check.sh`](run-conformity-workflow-check.sh) | Aggregated workflow diagnostics JSON (`conformity_workflow_check.py --json`). |

## Sample snapshot

- [`sample-conformity-assessment-snapshot.json`](sample-conformity-assessment-snapshot.json) — referenced by `scripts/conformity_workflow_check.py` to ensure paths resolve to committed workflow artefacts.

## Makefile

```bash
make conformity-workflow-check
make regulatory-workflow-check
```

Canonical operator documentation lives under [`docs/conformity/`](../../docs/conformity/). Underlying EU AI Act obligations are indexed by [`docs/regulatory/ai-act-obligations.json`](../../docs/regulatory/ai-act-obligations.json).
