# Sample governance scenario (fictional ML release)

**Fictional** Acme Corp releases **`expense_model_v3`**. Events are listed in **GovAI evidence vocabulary**; ordering matters in a live system. This file teaches the **story**—not your ledger contents.

## Cast

| Role | Name | Notes |
| --- | --- | --- |
| **Model owner** | Priya | Owns metrics and promotion request |
| **Risk reviewer** | Luis | Must record explicit review |
| **Human approver** | Dana | Named approval for high-risk tier |

## Events (happy path)

| Step | Event (illustrative) | Verdict snapshot |
| --- | --- | --- |
| A | `data_registered` for training snapshot | `BLOCKED` — model not trained |
| B | `model_trained` tying weights to `model_version_id` | `BLOCKED` — evaluation missing |
| C | `evaluation_reported` with passing metrics | `BLOCKED` — risk not recorded |
| D | `risk_recorded` + `risk_reviewed` | `BLOCKED` — human approval missing |
| E | `human_approved` (Dana) | `BLOCKED` — promotion prerequisites not satisfied |
| F | `model_promoted` when policy allows promotion | **`VALID`** |
| G | CI composite action verifies digest + export + **`VALID`** | CI **exit 0** |

## Non-happy branches (discussion prompts)

| Branch | What happens | Verdict |
| --- | --- | --- |
| Evaluation fails | `evaluation_passed == false` path | **`INVALID`** |
| Skip human approval | Promotion prerequisites unsatisfied | **`BLOCKED`** (may show empty `missing_evidence` but non-empty `blocked_reasons`) |
| Out-of-order evidence | Append rejected at ingest | No silent success |

## Compliance gate narrative

Acme wires **`GOVAI_RUN_ID`** to the release train UUID. On merge to `main`, GitHub Actions runs **`MonikaDvorackova/aigov-compliance-engine@v1`** (composite) with artefacts produced in the same pipeline. The action **submits** the evidence pack, **verifies** digest continuity, and **fails** unless the hosted verdict is **`VALID`**.

## Evidence pack narrative

After step F, Acme runs **`govai export-run`** (or HTTP export) and stores JSON in their GRC archive. Auditors compare **hashes** and **decision** fields to what CI asserted. The story is reproducible: same `run_id`, same policy version, same append-only history.

## Related

- [demo-flow.md](demo-flow.md)
- [README.md](README.md)
