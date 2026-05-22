# Experimental design

This page is the **narrative preregistration anchor** for studies that cite the machine-readable [`../../research/experimental-design.json`](../../research/experimental-design.json).

## Study types that fit GovAI artefacts

- **Conformance / regression** — does a pinned revision pass deterministic validators and benchmark harnesses?
- **Method comparison** — compare governance pipelines **with explicit ethical review** when human subjects or production traffic are involved.

## Hypotheses and measures

Pre-specify:

- **Primary hypotheses** — map each to a measurable outcome (for example deterministic benchmark pass rate at a pinned commit).
- **Secondary hypotheses** — optional; label them clearly to avoid fishing.
- **Stopping rules** — when to abandon or revise the protocol (for example if infrastructure changes invalidate pins).

## Analysis boundaries

Document what you will **not** claim (for example, no automatic legal compliance, no equivalence between local harness results and hosted ledger history unless demonstrated).

## Cross-links

- Threats to validity: [threats-to-validity.md](threats-to-validity.md)
- Benchmark methodology: [benchmark-methodology.md](benchmark-methodology.md)
