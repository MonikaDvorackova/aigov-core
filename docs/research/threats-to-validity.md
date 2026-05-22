# Threats to validity

Research using GovAI repositories should acknowledge **construct**, **internal**, and **external** validity limits.

## Construct validity

Benchmarks and interchange validators check **structured shapes and documented expectations**. They do not, by themselves, prove that an organisation’s **operational** controls match those artefacts.

## Internal validity

CI and local environments evolve. Without pinned commits and recorded tool versions, repeated executions may diverge for reasons unrelated to GovAI logic (for example dependency updates).

## External validity

Self-hosted and hosted deployments differ in topology, identity, billing, and policy modules. Findings from the OSS reference layout may not transfer without adaptation and operator-specific evidence.

## Mitigations

- Use [`reproducibility.md`](reproducibility.md) checklists and the JSON checklist in [`../../research/reproducibility-checklist.json`](../../research/reproducibility-checklist.json).
- Pair local harness results with **explicit** claims scopes in papers and datasheets.
- Machine-readable threat index: [`../../research/threats-to-validity.json`](../../research/threats-to-validity.json)
