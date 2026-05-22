# Control maturity

Control maturity describes how far documented controls have progressed along a simple **0–4 ordinal** per control record in a snapshot. The portfolio **control_maturity_score** (0–100) is derived deterministically from the average normalized maturity across controls.

## Levels (ordinal)

- **0** — Not started or unknown.
- **1** — Informal practice; partial documentation.
- **2** — Defined process; partial evidence.
- **3** — Consistently applied; evidence routinely collected.
- **4** — Measured and improved; periodic independent review where applicable.

## Evidence attachment

Each control may set `evidence_attached` to indicate whether audit or policy evidence is linked. Missing attachments surface as findings without implying a hosted verdict.

## Related

- [`governance-gap-analysis.md`](governance-gap-analysis.md)
- [`risk-weighted-controls.md`](risk-weighted-controls.md)
