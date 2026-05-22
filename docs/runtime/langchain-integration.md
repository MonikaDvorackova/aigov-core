# LangChain integration

LangChain is **not** imported by `aigov_py.runtime.adapters.langchain` at module load time. The adapter exposes **stdlib callables** you invoke from LangChain callbacks, tool wrappers, or runnables in **your** application.

## Tool evidence hook

[`make_tool_evidence_hook`](../../python/aigov_py/runtime/adapters/langchain.py) returns `on_tool(tool_name, input_digest)` which builds an [`EvidenceEvent`](../../python/aigov_py/runtime/models.py) and calls your `submit` callable (typically `RuntimeGovernanceClient.submit_evidence`).

Keep **payloads policy-safe**: include digests and ids, not raw user prompts, unless your operator policy explicitly allows them.

## Example

See [`../../examples/runtime-governance/langchain-example.py`](../../examples/runtime-governance/langchain-example.py). By default it **dry-runs**; set `GOVAI_EXAMPLE_EXECUTE=1` to perform a real `POST /evidence` against your audit base URL.

## Related

- [Python SDK](python-sdk.md)
- [Runtime policy patterns](runtime-policy-patterns.md)
