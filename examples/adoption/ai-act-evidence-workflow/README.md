# Adoption kit: AI Act–oriented evidence workflow (interchange samples)

**Purpose:** Provide **offline**, **machine-readable** samples that mirror the **registry interchange** artefacts (`governance_evidence_pack`, `governance_policy_module`, `governance_decision_trace`) for teams mapping **EU AI Act–style** programmes to GovAI concepts. This kit is **documentation and validation practice**, not legal advice.

## Prerequisites

- Python 3.10+ available.
- This repository cloned (validators live under `scripts/`).

## Quickstart

Validate the three JSON files with the conformance CLI (no network):

```bash
python3 scripts/validate_standard_conformance.py \
  examples/adoption/ai-act-evidence-workflow/evidence-pack.example.json
python3 scripts/validate_standard_conformance.py \
  examples/adoption/ai-act-evidence-workflow/policy-module.example.json
python3 scripts/validate_standard_conformance.py \
  examples/adoption/ai-act-evidence-workflow/decision-trace.example.json
```

Or run the aggregate standards tests from the repo root:

```bash
make governance-standards-check
```

(That target validates the canonical files under `examples/standards/`; your kit files use the same shapes.)

## Expected output

- Each `validate_standard_conformance.py` invocation exits **0** and prints a JSON object with `"ok": true` when the document matches the registry validators.
- Failures list structured `failures` / `warnings` — use them to tighten your own policy modules before binding to a hosted ledger.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `ok: false` / schema errors | Compare against `examples/standards/*.valid.json` and `docs/standards/conformance.md`. |
| Digest mismatch | `evidence-pack.example.json` matches the canonical demo pack (`examples/standards/evidence-pack.valid.json`). If you change `pack_id` or artefacts, recompute `pack_digest` using validator output or copy a freshly validated pack. |
| Confusion with hosted verdict | Interchange validation is **offline**; **`GET /compliance-summary`** remains authoritative on the audit service. |

## Scope limitations

- **Not** EU AI Act certification — organizational interpretation belongs with legal/compliance.
- **Does not** change **verdict semantics**, **digest algorithms**, or **runtime enforcement** in the GovAI engine.
- Illustrative **`ai_act_refs`** strings are **labels** for narrative only unless your program formally maps them.

## Related

- `docs/examples/ai-act-compliance-workflow.md` · `examples/reference/ai-act-compliance/README.md` · `docs/standards/interchange-specification.md` · `docs/adoption/reference-implementations.md`
