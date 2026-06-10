# Human approval runtime reference

Shows a high-risk governance run **without** `human_approved`, then appends human approval evidence and re-reads compliance summary and export.

## Run

```bash
export GOVAI_EXAMPLE_EXECUTE=1
python3 examples/human-approval-runtime/run_human_approval.py
```

## Expected behavior

- **Before** `human_approved`: promotion state is not satisfied; verdict is typically **BLOCKED** with approval-related reason codes.
- **After** `human_approved`: ledger projection records approval; export includes the approval event. Verdict may still be **BLOCKED** until `model_promoted` and other lifecycle gates are satisfied.

Human approval evidence is ledger-authoritative and feeds the deterministic compliance summary.
