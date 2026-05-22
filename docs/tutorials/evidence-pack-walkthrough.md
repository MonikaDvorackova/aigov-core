# Tutorial: Evidence pack walkthrough

## Audience

Security reviewers and platform engineers validating **governance evidence packs** offline or alongside hosted exports.

## Steps

1. Read the canonical shapes under **`docs/evidence-pack.md`** (repository root **`docs/`** tree).
2. Open the sample valid pack [`../../examples/standards/governance_evidence_pack.valid.json`](../../examples/standards/governance_evidence_pack.valid.json), or generate a minimal pack per **`docs/evidence-pack.md`**.
3. Run offline validators packaged with GovAI standards tooling (see **`README.md`** standards section).

```bash
cd python && source .venv/bin/activate
python -m aigov_py.standards.cli validate-evidence-pack ../examples/standards/governance_evidence_pack.valid.json
cd ..
```

## Expected outputs

- Validator exits **0** for well-formed packs.
- Human-readable errors for schema violations (field paths depend on the validator version).

## Common failures

- **Digest mismatch** — regenerated files not saved before digest computation.
- **Missing required sections** — policy version or capability references omitted.

## Screenshot slot

- Side-by-side view of JSON pack and validator success output (redact customer identifiers).

## Demo video checklist

- [ ] Show file path and command line only (no secrets).
- [ ] Explain what digest continuity means in one sentence.
- [ ] Link viewers to **`GET /api/export/:run_id`** for hosted audit alignment.

## Teaching narrative

Evidence packs are **portable artefacts**; hosted audit services add **ledger-backed** guarantees. Both play roles in enterprise reviews.
