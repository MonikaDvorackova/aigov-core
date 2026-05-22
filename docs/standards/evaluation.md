# Phase 5 standards evaluation harness

The module `python/aigov_py/standards/evaluation.py` evaluates the **fixed example corpus** under `examples/standards/*.valid.json`.

## Output

`evaluate_standards_corpus()` returns a Python dict; `evaluation_json()` returns **deterministic** canonical JSON with:

- `total_documents`, `valid_documents`, `invalid_documents`
- `validators` (Python function names, stable ordering)
- `digest_stability` (each validator run twice on the same data)
- `issue_count` (sum of issue list lengths)
- `verdict` — `VALID` only when every document validates and digest stability holds
- `documents` — per-file detail rows

## Usage (tests / tooling)

From repository root with an editable install:

```python
from pathlib import Path
from aigov_py.standards.evaluation import evaluation_json

print(evaluation_json(repo_root=Path(".").resolve()))
```

Pytest: `python/tests/test_phase5_standards_evaluation.py`.

## Non-goals

- Not a benchmark suite for latency or throughput.
- Not a substitute for hosted CI artefact gates.
