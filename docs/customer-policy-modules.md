## Customer policy modules (bring your own policy)

GovAI’s core engine is **policy-agnostic**: it does not “implement the AI Act” or any other legal framework.

Instead, GovAI enforces **evidence completeness** and produces deterministic `VALID` / `BLOCKED` / `INVALID` outcomes based on:

- the run’s append-only evidence log, and
- the configured policy requirements expressed as **required evidence codes**

This page describes a **product-layer** convention: a customer-replaceable policy module that maps your chosen policy → a flat `required_evidence` set.

See:

- `docs/policies/policy-module-format.md`
- `docs/policies/*.example.yaml`

---

## Replace “AI Act” with your internal policy

1) Create your own policy module YAML (or copy an example):

- start from `docs/policies/internal-genai-policy.example.yaml`
- edit `policy.id`, `policy.name`, `policy.version`
- edit the `requirements[*]` list to match your internal controls

2) Ensure `required_evidence` only uses **existing GovAI requirement/evidence codes**.

Examples of evidence codes already used in this repo include:

- discovery-driven requirements: `ai_discovery_completed`, `model_registered`, `usage_policy_defined`
- lifecycle / release controls: `evaluation_reported`, `risk_reviewed`, `human_approved`, `model_promoted`

Important: policy modules are **static mappings**. No conditionals, no discovery branching, no runtime computation.

---

## Compile a policy module (inspect required evidence)

Compile a policy module YAML into the flat deterministic `required_evidence` set:

```bash
govai policy compile --path docs/policies/ai-act-high-risk.example.yaml
```

Default output is **newline-separated evidence codes**, sorted.

To get machine-readable output:

```bash
govai policy compile --path docs/policies/ai-act-high-risk.example.yaml --json
```

This prints:

- `policy.id`, `policy.name`, `policy.version`
- `required_evidence[]` (sorted)

This command is **compile-only**:

- no network calls
- no backend calls
- no enforcement or upload behavior change

---

## Compare two policies

To compare two policies, compile both and diff the resulting evidence lists:

```bash
govai policy compile --path docs/policies/ai-act-high-risk.example.yaml > /tmp/policy_a.txt
govai policy compile --path docs/policies/internal-genai-policy.example.yaml > /tmp/policy_b.txt
diff -u /tmp/policy_a.txt /tmp/policy_b.txt
```

This comparison is about **required evidence codes**, not legal interpretation.

---

## Separate from backend enforcement (current limitation)

Today, policy modules are a **customer-facing product layer** that compiles into a flat evidence set.

They are intentionally separate from backend enforcement:

- The Rust audit service and its decision semantics are unchanged.
- There is **no policy upload API** in this iteration.
- There is **no runtime policy switching** via the backend in this iteration.

Current limitation: **compile-only** (local inspection). Enforcement remains whatever policy the backend is configured to use.

---

## How policy maps to required evidence

The mapping is a deterministic union:

- For each `requirements[*]`, take its `required_evidence` list.
- Union + deduplicate into a flat set.

That flat set is what GovAI uses as “required evidence” for a run (and what appears in exports and summaries).

---

## How discovery affects policy (automatic requirements)

GovAI supports a deterministic “policy binding” layer that can **augment** policy-required evidence based on deterministic discovery signals.

Conceptually:

`discovery signals` + `policy module` → `required_evidence` (flat set) → verdict

Examples (deterministic mapping):

- If `llm_used` is detected → require `evaluation_reported` and `usage_policy_defined`.
- If `user_facing` is detected → require `human_approved`.
- If `pii_possible` is detected → require `privacy_review_completed`.

Important constraints:

- Discovery does **not** replace policy modules.
- The output of binding is still a **flat deterministic set** (`required_evidence` codes).
- No runtime policy logic is introduced: it is a static mapping from signals to evidence codes.

See also:

- `docs/discovery-v2.md`
- `docs/reports/discovery-v2-and-policy-binding.md`

---

## How this affects `BLOCKED` / `VALID` outcomes

This product-layer policy module mechanism does **not** change semantics:

- `BLOCKED`: the run is not yet eligible (commonly because required evidence is missing; sometimes because approval/promotion prerequisites are not satisfied even when `missing_evidence == []`).
- `VALID`: all required evidence is present and policy rules pass.
- `INVALID`: a decisive policy rule fails (for example explicit evaluation failure), even if required evidence exists.

What changes when you switch policy modules is only the **content of the required evidence set** (and therefore what appears in `missing_evidence` when a run is incomplete).

