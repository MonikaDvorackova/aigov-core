# LangChain integration guide

## Purpose

Describe how **LangChain** (Python or TypeScript) applications can record agent steps, tool calls, and retrievals as **GovAI evidence** and gate releases—aligned with the documentation-only patterns already referenced from customer examples.

## Integration overview

LangChain runs as **orchestration** in your process; GovAI remains an **audit service**:

- Use **callbacks** or **middleware** (depending on LangChain version) to translate chain events into GovAI evidence events.
- Keep **secrets and prompts** out of evidence when policy requires minimization.
- Correlate LangChain `run_id` / `session_id` with GovAI `run_id` via a single explicit mapping layer you control.

See also `examples/customer-repos/README.md` for documentation-only LangChain-style patterns shipped earlier in the repo.

## Implementation steps

1. **Define the evidence contract** — list required events (for example `tool_start`, `tool_end`, `human_approval`) in your policy module; validate interchange offline if you use registry artefacts (`docs/standards/conformance.md`).
2. **Implement a callback** — on each tool invocation, POST a compact JSON event to `POST /evidence` with stable ordering if your policy cares about sequence.
3. **Surface failures** — if a tool throws, still emit an error event so the ledger reflects reality before `govai check`.
4. **CI** — run LangChain integration tests in parallel with `govai check` on a fixed `run_id` fixture for golden-path tests.
5. **Upgrade safety** — pin LangChain majors; re-run conformance checks when callback APIs change.

## Validation

- Repository layout: `python3 scripts/developer_integrations_check.py`.
- Golden tests in your app: assert evidence POST responses are `2xx` and summary becomes `VALID` for happy path fixtures.
- Optional: validate portable JSON artefacts with `scripts/validate_standard_conformance.py` where applicable.

## Failure modes

- **Missing tool failure events** — chain aborts without evidence → `BLOCKED` surprises. Mitigation: `try/finally` in callback hooks.
- **Unbounded payloads** — serializing full documents into evidence. Mitigation: digest or reference storage URIs allowed by policy.
- **Async races** — overlapping async tool calls produce ambiguous ordering. Mitigation: include monotonic sequence numbers in events if policy requires total order.
