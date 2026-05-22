# Conformance validation

Conformance checks prove that a JSON document matches the **registered** interchange revision for its `schema_version` field, using **deterministic Python validators** (canonical digests, digest manifest rules, and—where applicable—authoritative gate recomputation). This is **orthogonal** to hosted audit readiness: passing conformance does **not** assert ledger state, billing, or tenant isolation.

## Outputs

The helper `aigov_py.standards.validator.validate_conformance` returns a structured report. When using `scripts/validate_standard_conformance.py --json`, stdout is **one JSON object** with sorted keys:

| Field | Meaning |
| --- | --- |
| `ok` | `true` only when there are zero validation failures. |
| `artifact_type` | Registry id (for example `governance_evidence_pack`). |
| `version` | Exact `schema_version` string from the document. |
| `checks` | Small ordered list of named checks (registry lookup, deterministic rules). |
| `failures` | List of `{code, message, path}` issues. |
| `warnings` | Reserved for non-fatal diagnostics (usually empty). |
| `digest` | Canonical digest token when validation succeeded (`sha256:…`). |

Human-readable mode (omit `--json`) prints the same information as short lines on stderr/stdout suitable for logs.

## Commands

From the repository root:

```bash
python3 scripts/validate_standard_conformance.py --json examples/standards/evidence-pack.valid.json
python3 scripts/validate_standard_conformance.py --json examples/standards/policy-module.valid.json
python3 scripts/validate_standard_conformance.py --json examples/standards/decision-trace.valid.json
```

Optional enforcement of a specific registry type (must match inference):

```bash
python3 scripts/validate_standard_conformance.py --json --artifact-type governance_evidence_pack examples/standards/evidence-pack.valid.json
```

## Make targets

- `make standards-conformance` — runs `pytest` on `python/tests/test_standards_conformance.py`.
- `make governance-standards-check` — validates the three shipped interchange examples with `--json` (exit non-zero on failure).

## JSON Schema files

Under `schemas/`, each interchange revision ships a **JSON Schema** description for external tooling. The **authoritative** rules remain the Python validators (they express digest algebra and cross-field constraints that are awkward to encode purely in schema). External implementers should treat schema + Python behaviour together; when they disagree, follow the Python validator and open an issue.

## Corpus evaluation

`python/aigov_py/standards/evaluation.py` continues to walk `examples/standards/*.valid.json` and assert digest stability across double validation. Phase 9 adds the new example filenames to that corpus.
