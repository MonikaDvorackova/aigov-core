---
name: map-ai-act-controls
description: Map product features to repository governance artefacts and EU AI Act themes (operational, non-legal).
---

# Skill: Map a feature to EU AI Act–oriented governance controls

Use this skill when designing or reviewing AI features so that **technical controls** align with **documented governance** (not legal advice).

## 1. Describe the feature

Capture:

- Actors (human, automated agent, external API).
- Data categories (training, inference logs, user content).
- Risk surface (safety, fundamental rights, misuse).

## 2. Map to GovAI artefacts (repository-native)

| EU AI Act theme (high level) | GovAI / repo artefact |
|------------------------------|------------------------|
| Risk management & logging | Evidence events, audit log, `docs/evidence/` bundles |
| Human oversight | Human approval events in pipeline; `## Human approval gate` in reports |
| Technical documentation | `docs/reports/*.md`, architecture docs |
| Data governance | Policy modules under `python/aigov_py/`, evidence requirements |
| Traceability / record keeping | Run id continuity, digest manifests, `verify-evidence-pack` |

## 3. Concrete workflow

1. Identify which **policy** and **evidence** types your feature triggers (`python/aigov_py/policy_loader.py` patterns, discovery scan output).
2. Specify required **events** and **approvals** for a valid `VALID` verdict in your deployment mode (consult **`docs/technical-documentation.md`** and **`docs/golden-path.md`** if present).
3. Add a **`docs/reports/*.md`** section under `## Risk assessment` tying feature risks to mitigations and residual risk.
4. Run offline validators where applicable (`govai standards validate-*` via `python -m aigov_py.standards.cli`).

## 4. Non-goals

- This skill does **not** provide legal classification as high-risk AI; engage qualified counsel for regulatory classification.
- Do not change **verdict semantics** or hosted gate contracts in this mapping exercise without a dedicated change plan and audit report.
