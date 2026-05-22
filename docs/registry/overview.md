# GovAI standards registry and policy pack ecosystem (overview)

GovAI ships a **documentation-first registry layer** so operators, partners, and contributors can discover **interchange standards**, **curated policy packs**, **benchmark metadata**, **certification levels**, and a **capability taxonomy** without implying new runtime enforcement.

## What lives where

| Surface | Role |
| --- | --- |
| [`registry/README.md`](../../registry/README.md) | Human-readable index for JSON catalogs under [`registry/`](../../registry/). |
| [`registry/standards-catalog.json`](../../registry/standards-catalog.json) | Maps interchange artefacts to JSON Schemas and docs paths. |
| [`registry/policy-pack-catalog.json`](../../registry/policy-pack-catalog.json) | Annotates example packs with certification level and capability tags. |
| [`registry/benchmark-catalog.json`](../../registry/benchmark-catalog.json) | Points to local stdlib benchmark runners. |
| [`registry/certification-levels.json`](../../registry/certification-levels.json) | Defines **community**, **verified**, and **enterprise** documentation levels. |
| [`registry/capability-taxonomy.json`](../../registry/capability-taxonomy.json) | Stable capability identifiers (risk management, human oversight, traceability, robustness, post-market monitoring). |
| [`marketplace/manifest.json`](../../marketplace/manifest.json) | Curated machine-readable list of in-repo example policy pack directories. |

Validation entry point: `python3 scripts/registry_check.py` (see [`../../Makefile`](../../Makefile) targets `registry-check` and `customer-analytics-check`).

## Public vs private registries

- **Public registry** — open documentation, JSON catalogs, and example packs in this repository. Suitable for teaching, CI fixtures, and partner alignment on interchange versions.
- **Private registry** — an operator-maintained catalog (often behind SSO) that reuses the same shapes but lists **internal** policy packs, evidence templates, and signing keys. See [private-registries.md](private-registries.md).

Neither registry type changes **hosted verdict semantics**; they help humans and tooling agree on **what to validate** and **where artefacts live**.

## Trust posture (short)

The registry describes **process and file layout expectations**. **Signing and provenance** are layered concepts: see [trust-and-signing.md](trust-and-signing.md). GovAI still treats the **audit service and ledger** as authoritative for deployment decisions when configured.

## Submissions and review

Contributors propose packs and registry entries through the community workflow: [submission-guidelines.md](submission-guidelines.md) and [review-process.md](review-process.md). Maintainers use [registry-maintainer-guide.md](../community/registry-maintainer-guide.md).

## Non-claims

- Registry metadata **does not** certify legal compliance with the EU AI Act, HIPAA, PCI-DSS, or any sectoral regime.
- Validators prove **structural** conformance and **catalog consistency**; they do **not** replace human judgement for high-risk deployments.
