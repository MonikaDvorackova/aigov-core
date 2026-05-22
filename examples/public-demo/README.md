# Public demo package (GovAI)

**Story-first** materials for conferences, blog posts, and investor rooms where you may **not** have a live audit endpoint. For a **live** read-only probe of `/health` and `/ready`, use **[`examples/local-demo/`](../local-demo/README.md)** and **`make local-demo`**.

## What this folder is

| File | Role |
| --- | --- |
| **[demo-flow.md](demo-flow.md)** | Commands and expected outputs when a service **is** available; narrative when it is not |
| **[sample-governance-scenario.md](sample-governance-scenario.md)** | End-to-end governance story with verdict vocabulary |

## Compliance gate narrative (elevator)

**Production merges** should use the **composite GitHub Action** at the repository root: submit evidence pack, verify digest continuity against the hosted ledger, optionally require export cross-check, then assert verdict **`VALID`** via `GET /compliance-summary`. **`govai check`** is a lighter readout that does **not** bind CI artefacts to the digest chain—see **[`docs/github-action.md`](../../docs/github-action.md)**.

## Evidence pack narrative (elevator)

An **evidence pack** ties CI outputs to append-only ledger history through digests; **export JSON** captures decision fields and hashes for archival and third-party review. See **[`docs/evidence-pack.md`](../../docs/evidence-pack.md)**.

## Where to go next

- Hosted onboarding: **[`docs/customer-onboarding-10min.md`](../../docs/customer-onboarding-10min.md)**
- Pilot program docs: **[`docs/pilots/pilot-onboarding.md`](../../docs/pilots/pilot-onboarding.md)**
- Launch checklist: **[`docs/launch/launch-checklist.md`](../../docs/launch/launch-checklist.md)**
