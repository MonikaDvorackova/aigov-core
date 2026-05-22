# Performance results (machine-generated)

Authoritative numeric outputs live under **`benchmark-runs/latest/`** after running:

```bash
make empirical-evaluation-run
```

Key files:

| File | Contents |
|------|-----------|
| `event-ingestion-benchmarks.json` | Throughput and latency statistics per payload size and count |
| `hash-chain-benchmarks.json` | Verification seconds, µs/event, events/sec |
| `export-benchmarks.json` | Export and gzip timings, sizes, compression ratio |
| `multi-tenant-benchmarks.json` | Aggregate wall time vs tenant count |
| `failure-benchmarks.json` | Detection timings for invalid states |
| `empirical-evaluation-summary.json` | Orchestrator metadata |

This Markdown file is **not** auto-synced; cite the JSON artefacts in manuscripts for reproducibility.

## Related

- `docs/research/empirical-evaluation.md`
