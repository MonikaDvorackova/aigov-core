# Academic artifacts and reproducibility (Phase 5)

This note ties **citation metadata**, **reproducibility**, and **evaluation artefacts** to the Phase 5 *Research and Ecosystem Dominance* roadmap (`docs/governance/phase5_research_and_ecosystem.md`).

## Citation

Use the repository **`CITATION.cff`** at the root for software citation metadata (title, authors, version fields, repository URL). Update the `version` and `date-released` fields when cutting releases used in publications.

## Reproducibility statement

- **Deterministic validators:** `python/aigov_py/standards/` uses canonical JSON and stable issue ordering.
- **Fixed corpus:** `examples/standards/*.valid.json` is the reference set for regression and the evaluation harness (`docs/standards/evaluation.md`).
- **Evaluation JSON:** `evaluation_json()` from `aigov_py.standards.evaluation` is stable for a given repository commit.

## Artifact readiness checklist

- [ ] Record exact **`aigov-py`** version (`python/pyproject.toml`).
- [ ] Pin Python version used for experiments.
- [ ] Archive **`examples/standards/`** and validator outputs (`evaluation_json()`).
- [ ] Document whether runs used **hosted** audit APIs or **offline** standards only.
- [ ] Avoid storing secrets or raw prompts in supplementary material (aligns with standards raw-field rejection).

## Relationship to Phase 5 roadmap

Phase 5 emphasizes **interoperable artefacts** and **ecosystem alignment**. Academic packages should cite the **software** (`CITATION.cff`) and the **standards specifications** under `docs/standards/*.md`, and clearly separate **offline structural validation** from **hosted audit guarantees**.
