# Industry implementer checklist (Phase 5 standards)

Use this checklist when adopting GovAI **portable standards** alongside (or separate from) the hosted audit service.

## Adoption steps

1. **Pin** the `aigov-py` package version that matches your validators.
2. Store standards documents as **JSON** (YAML optional where PyYAML is deployed).
3. Run **`govai standards validate-…`** (or `python -m aigov_py.standards.cli`) in CI on every change to standards files.
4. Keep **canonical digests** in your artefact registry if you rely on interchange integrity.

## Conformance expectations

- Passing validation means **structural** conformance to the published schemas — not legal approval or model safety.
- **Evidence-first:** standards complement audit evidence; they do not replace append-only ledger semantics.

## Validation commands

```bash
govai standards validate-capability-policy path/to/policy.json
govai standards validate-delegation-graph path/to/graph.json
govai standards validate-trace-verification-plan path/to/plan.json
govai standards validate-evidence-pack path/to/pack.json
```

Each command prints **exactly one** JSON object on stdout.

## Evidence handling expectations

- Governance evidence packs reference artefacts by **id** and **digest** — not raw payloads.
- Cross-check digests with your own artefact store; validators do not fetch remote content.

## Interoperability expectations

- Identifiers (`policy_id`, `capability_id`, `delegation_id`, …) should be agreed between partners; the validators enforce **shape** and **internal** consistency only.

## Certification disclaimer

GovAI standards validators are **technical conformance tools**. They are **not** a certification mark, regulatory approval, or legal opinion.
