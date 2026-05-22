# Example: AI Act–oriented compliance workflow (policy + evidence)

The EU **AI Act** introduces obligations that organizations interpret with counsel. GovAI provides **technical infrastructure** for **traceable decisions** and **policy-driven evidence requirements** — it does **not** provide legal advice or certification.

## What this example covers

- How teams often **map** Act-style obligations to **evidence types** and **approval steps**.
- How **policy modules** attach static `required_evidence` sets (`docs/customer-policy-modules.md`).
- How the **verdict** remains **`GET /compliance-summary`** (VALID / INVALID / BLOCKED).

## Workflow (illustrative)

1. **Classify** the system (e.g., high-risk category in your internal model) with legal/compliance input — **outside** GovAI.
2. **Select or author** a policy module that lists required evidence: datasets, evaluations, risk records, human review, promotion events.
3. **Open a `run_id`** for a release candidate; run **discovery** if you use discovery signals (`docs/discovery-v2.md`).
4. **Append evidence** in order accepted by policy; observe **BLOCKED** until prerequisites exist.
5. **Obtain human approval** events as required by policy; ensure **evaluation_passed** semantics are understood (`README` decision states).
6. **Promote** only when the server accepts promotion and verdict becomes **VALID**.
7. **Export** audit JSON for record retention.

## INVALID vs BLOCKED

- **INVALID** — evaluation or other gates **failed** explicitly.
- **BLOCKED** — not eligible for promotion (missing evidence and/or approval/promotion prerequisites).

This distinction matters for **regulatory narrative**: show the **server’s** structured reasons, not a spreadsheet tab.

## Portable artefacts

For interchange without a hosted verdict, use **governance evidence packs** and validators (`docs/standards/interchange-specification.md`). Bind them to a ledger when you need **append-only** history.

## Reference folder

**`examples/reference/ai-act-compliance/README.md`** — condensed checklist and doc map.

## Related

- `docs/policies/` · `docs/customer-policy-modules.md` · `docs/evidence-pack.md`
