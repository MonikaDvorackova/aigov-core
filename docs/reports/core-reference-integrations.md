# Core Reference Integrations

## Summary

Adds four reference integration examples and documentation showing how AI applications record ledger-authoritative evidence through AIGov Core (`aigov_audit`): OpenAI-style mocked inference, FastAPI middleware hooks, tool-call reconstruction, and human approval lifecycle. Includes `make reference-integrations-check` and CI wiring. No runtime semantics, billing, or platform route changes.

## Evaluation gate

Reference integrations preserve **evaluation** evidence (`evaluation_reported` and evaluation outcomes in audit export) as **ledger-authoritative** evidence. Evaluation results contribute to **deterministic compliance summary** verdicts together with discovery, risk review, and promotion state—not as side-channel scores.

## Human approval gate

Reference integrations preserve **human approval** evidence (`human_approved`) as **ledger-authoritative** evidence. Approval records contribute to **deterministic compliance summary** verdicts and appear in audit export human-approval fields before promotion gates can clear.

## Integration coverage

| Integration | Path | Evidence focus |
|-------------|------|----------------|
| OpenAI-style runtime audit | `examples/openai-runtime-audit/` | Mocked model input/output, policy evaluation, evaluation gate, export + verify |
| FastAPI middleware | `examples/fastapi-runtime-middleware/` | Request / decision lifecycle hooks via middleware |
| Tool-call audit | `examples/tool-call-audit/` | `tool_call`, `tool_output`, decision linkage in export |
| Human approval | `examples/human-approval-runtime/` | Pre/post `human_approved` compliance summary comparison |

Shared helpers: `examples/reference-runtime-common/`. Operator guide: `docs/reference-integrations.md`.

## Verification

```bash
make reference-integrations-check
make gate
make core-runtime-examples-check
cd rust && cargo build --locked --bin aigov_audit && cargo test --locked
```

Examples use `GOVAI_EXAMPLE_EXECUTE=1` for live runtime calls; CI validates structure and contracts offline only.
