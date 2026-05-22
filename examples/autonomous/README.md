# Autonomous and multi-agent governance examples

Illustrative payloads and shell drivers for the **advisory** autonomous governance bundle under [`../../autonomous/autonomous-governance-manifest.json`](../../autonomous/autonomous-governance-manifest.json) and operator docs under [`../../docs/autonomous/`](../../docs/autonomous/).

These artefacts do **not** change GovAI compliance verdict semantics or Rust runtime enforcement.

## Commands

- `bash examples/autonomous/run-autonomous-governance-check.sh` — validates the `autonomous/` JSON bundle, documentation paths, example drivers, and Makefile wiring; prints deterministic JSON with `--json` on the script.
- `bash examples/autonomous/run-multi-agent-governance-check.sh` — same as above plus multi-agent coordination sample validation and a `docs/index.md` wiring check.

Aggregate Makefile targets (each ends with `make gate` for audit report heading hygiene):

- `make autonomous-governance-check`
- `make multi-agent-governance-check`

## Files

| File | Purpose |
| --- | --- |
| [`sample-multi-agent-coordination.json`](sample-multi-agent-coordination.json) | Example coordination graph, agents, delegation edges, and approval gateways for multi-agent reviews. |
