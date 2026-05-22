# Adoption kit: standards conformance (offline)

**Purpose:** Run a **single-command**, **offline** validation of a **governance evidence pack** JSON file using the same `scripts/validate_standard_conformance.py` entry point used in CI. Suitable for **pre-commit** or **local** checks when authoring interchange documents.

## Prerequisites

- Python 3.10+ on your PATH.
- Repository root available (script resolves paths relative to the monorepo).

## Quickstart

From repository root:

```bash
bash examples/adoption/standards-conformance-kit/run-conformance.sh
```

Equivalent manual invocation:

```bash
python3 scripts/validate_standard_conformance.py \
  examples/adoption/standards-conformance-kit/sample-valid-artifact.json
```

## Expected output

- Exit code **0**.
- `standards-conformance-kit: OK` when using `run-conformance.sh`.
- JSON diagnostics on stdout when you omit output redirection.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `No such file` | Run from repo root; do not move `scripts/` relative to `examples/`. |
| Validator errors after edit | `sample-valid-artifact.json` is **byte-aligned** with `examples/standards/evidence-pack.valid.json` so `pack_digest` stays valid; fork from that file if you need a new pack id. |
| Need stricter CI parity | Run `make governance-standards-check` to validate all canonical interchange examples. |

## Scope limitations

- Validates **structure + digest** for interchange; **does not** prove **append-only ledger** history or **hosted** `GET /compliance-summary` outcomes.
- **Does not** change **evidence digest** behaviour inside the Rust service — this kit calls the **Python** validator only.

## Related

- `docs/standards/conformance.md` · `make governance-standards-check` · `docs/adoption/reference-implementations.md`
