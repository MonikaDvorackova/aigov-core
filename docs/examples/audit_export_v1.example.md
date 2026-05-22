# Audit export example (v1) — why `BLOCKED` can have `missing_evidence: []`

The file [`audit_export_v1.example.json`](audit_export_v1.example.json) is intentionally a **credible “promotion is gated”** scenario:

- `decision.verdict: "BLOCKED"` can mean **“not eligible for promotion yet”** even when all required evidence is present.
- In that case, `evidence_requirements.missing_evidence` may be `[]`, and the blocking condition is explained in `decision.blocked_reasons` (for example awaiting human approval or promotion prerequisites).

This is important for first-time users: **a `BLOCKED` CI failure does not necessarily mean “upload more evidence”** — it can also mean “complete the approval/promotion gate for this run”.

