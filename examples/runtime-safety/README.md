# Runtime safety examples (stdlib, no network)

These scripts mirror CI behaviour for **Phase 21** runtime safety diagnostics.

| Script | Purpose |
| --- | --- |
| [run-runtime-safety-check.sh](run-runtime-safety-check.sh) | Runs `runtime_safety_check.py` with JSON to stdout |
| [run-runtime-safety-score.sh](run-runtime-safety-score.sh) | Runs `runtime_safety_score.py` with JSON to stdout |
| [run-runtime-safety-report.sh](run-runtime-safety-report.sh) | Writes deterministic Markdown to stdout |

## Sample snapshot

- [`sample-runtime-safety-snapshot.json`](sample-runtime-safety-snapshot.json) — validated by `scripts/validate_runtime_safety_snapshot.py`.

## Try it

```bash
bash examples/runtime-safety/run-runtime-safety-check.sh
bash examples/runtime-safety/run-runtime-safety-score.sh
bash examples/runtime-safety/run-runtime-safety-report.sh | head
```

Aggregated validation from the repo root:

```bash
make runtime-safety-check
```
