# Standards examples (interoperability)

Valid JSON files in this directory are used by:

- **`python/aigov_py/standards/evaluation.py`** — corpus regression (digest stability).
- **`scripts/validate_standard_conformance.py`** — registry-backed conformance (`make governance-standards-check`).

## Phase 9 registry interchange (copy/paste starters)

| File | `schema_version` |
| --- | --- |
| `evidence-pack.valid.json` | `govai.standards.governance_evidence_pack.v1` |
| `policy-module.valid.json` | `govai.standards.governance_policy_module.v1` |
| `decision-trace.valid.json` | `govai.standards.governance_decision_trace.v1` |

```bash
python3 scripts/validate_standard_conformance.py --json examples/standards/evidence-pack.valid.json
```

See `docs/standards/interchange-specification.md` for field rules. Invalid shapes are covered in `python/tests/test_standards_conformance.py` (not shipped as `.valid.json` files).

## Phase 5 golden files

`capability_policy.valid.json`, `delegation_graph.valid.json`, `trace_verification_plan.valid.json`, and `governance_evidence_pack.valid.json` continue to exercise the original CLI validators (`python -m aigov_py.standards.cli …`).
