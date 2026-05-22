# Tutorial: Debugging a failed gate

```docs
preset: troubleshoot-gate
```

## Audience

Engineers responding to a red **`govai check`** or failing GitHub Action.

## Steps

1. **Fetch the compliance summary** (replace host and id):

   ```bash
   curl -fsS -H "Authorization: Bearer $GOVAI_API_KEY" \
     "$GOVAI_AUDIT_BASE_URL/compliance-summary?run_id=$RUN_ID" | jq .
   ```

2. Read **`missing_evidence`** and **`blocked_reasons`** arrays in the JSON payload.
3. Cross-reference with the **auditability** scenario vocabulary in [`../../benchmarks/auditability-failures/README.md`](../../benchmarks/auditability-failures/README.md).
4. If the failure is documentation drift, run:

   ```bash
   make docs-links-strict
   make gate
   ```

## Expected outputs

- A structured JSON object explaining **why** the verdict is not **`VALID`**.
- Local gates print human-readable failures (for example missing markdown headings).

## Common failures

| JSON hint | Meaning |
| --- | --- |
| `missing_evidence` non-empty | Required event types absent |
| `blocked_reasons` mentions approvals | Approval or promotion prerequisites not met |
| digest errors (when surfaced) | Chain or artefact mismatch |

## Screenshot slot

- jq-formatted summary with secrets redacted.

## Teaching narrative

Treat the compliance summary as the **single source of truth** for gating; avoid guessing from CI logs alone.
