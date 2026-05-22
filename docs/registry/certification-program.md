# Certification program (documentation-oriented)

GovAI uses **three certification levels** for registry and marketplace metadata. These levels communicate **review depth and packaging expectations**; they are **not** statutory certifications.

## Levels (machine-readable)

Canonical definitions: [`registry/certification-levels.json`](../../registry/certification-levels.json).

| `id` | Meaning |
| --- | --- |
| `community` | Public contribution path; basic validation; suitable for examples and teaching. |
| `verified` | Maintainer-reviewed; compatibility notes against interchange versions; reproducible validator commands documented. |
| `enterprise` | Extended review, stronger provenance expectations, and documented operator runbooks for adoption at scale. |

## What certification does **not** do

- It does **not** change Rust runtime enforcement or database migrations.
- It does **not** alter `GET /compliance-summary` verdict semantics.
- It does **not** guarantee legal compliance in any jurisdiction.

## Promotion path (conceptual)

1. Start as **community** after passing structural validators and editorial review.
2. Move to **verified** after extended checklist completion (see [review-process.md](review-process.md)).
3. Reserve **enterprise** for packs with signed releases, documented support channels, and explicit compatibility statements.

Human owners approve transitions; automation only **checks metadata shape**, not business trust.
