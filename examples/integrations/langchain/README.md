# LangChain + GovAI example

Use LangChain callbacks (or middleware) to translate agent/tool events into GovAI evidence posts.

## Outline

1. Allocate a `run_id` per agent session.
2. On each tool call completion, POST an evidence event with tool name, latency, and outcome.
3. On human approval steps, POST explicit approval events if your policy requires them.

## Related docs

- `docs/integrations/langchain-integration.md`
- `examples/customer-repos/README.md` (documentation-only patterns)
