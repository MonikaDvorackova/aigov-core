# Risk management lifecycle

[`risk-management-workflow.json`](../../conformity/risk-management-workflow.json) documents the iterative risk management lifecycle expected for high-risk AI systems under Article 9. The lifecycle is operator-owned; this bundle structures the stages and review cadence.

## Stages

| Stage | Purpose |
| --- | --- |
| Identify | Enumerate foreseeable harms and reasonably foreseeable misuse. |
| Analyze | Estimate severity, likelihood, and affected groups. |
| Treat | Select mitigations and record residual risk. |
| Evaluate | Compare residual risk against acceptance criteria. |
| Monitor | Track post-deployment signals and refresh the register. |

Each stage lists `activities` and `outputs`; the `evaluate` stage records `human_approvals` so risk acceptance is auditable.

## Risk tier taxonomy

The taxonomy (`high`, `medium`, `low`) is a documentation aid for operators. GovAI does **not** assign tiers automatically; the criteria are intended to support consistent classification decisions across releases.

## Cadence and triggers

`review_cadence` requires at least one review per release. Substantial modification, serious incidents, and regulatory change all act as triggers for re-running stages. Coordination with the post-market monitoring workflow is captured in `evidence_links`.

## Boundaries

Risk acceptance remains a **human, accountable decision**. The bundle does not change runtime decisions or override deployer responsibilities.
