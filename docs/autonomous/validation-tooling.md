# Validation tooling

## Script

[`../../scripts/autonomous_governance_check.py`](../../scripts/autonomous_governance_check.py) (stdlib only):

- Validates the `autonomous/` JSON bundle, manifest cross-references, required documentation paths, example drivers, and Makefile targets.
- With `--multi-agent`, additionally validates [`../../examples/autonomous/sample-multi-agent-coordination.json`](../../examples/autonomous/sample-multi-agent-coordination.json) and ensures [`../index.md`](../index.md) links autonomous documentation for discoverability.

Emit deterministic JSON:

```bash
python3 scripts/autonomous_governance_check.py --json
python3 scripts/autonomous_governance_check.py --multi-agent --json
```

## Makefile

- `make autonomous-governance-check` — runs the script then `make gate`.
- `make multi-agent-governance-check` — runs the script in multi-agent mode then `make gate`.

## CI note

Repository CI continues to enforce existing gates (`make gate`, strict doc links, and so on). This tooling adds **documentation and artefact hygiene** checks only.
