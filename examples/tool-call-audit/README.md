# Tool-call audit reference

Records agent **tool_call**, **tool_output**, and a final **ai_decision_completed** event that references tool evidence IDs. Then reads export to show reconstructible tool use.

## Run

```bash
export GOVAI_EXAMPLE_EXECUTE=1
python3 examples/tool-call-audit/run_tool_call_audit.py
```

Routes: `POST /evidence`, `GET /compliance-summary/{run_id}`, `GET /api/export/{run_id}`, `GET /verify/{run_id}`.

## Expected verdict

Usually **BLOCKED** until full governance lifecycle evidence exists. Tool events still appear in the audit export hash chain.
