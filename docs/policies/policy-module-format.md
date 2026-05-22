## Policy module format (customer-replaceable)

GovAI is **policy-agnostic** at the product layer: a “policy module” is a **static mapping** from a named policy (for example EU AI Act, internal policy, sector policy) to the **flat `required_evidence` set** that the existing GovAI engine already understands.

This module format is intentionally narrow:

- **No runtime logic allowed** (no conditionals, no branching, no environment switching).
- **Deterministic mapping only**: YAML → flat `required_evidence` set.
- **No engine changes**: this is a *product layer* convention that compiles into the same `required_evidence` codes the core engine already uses.
- **No schema / API payload changes**: `required_evidence` remains a list of existing requirement codes.

---

## YAML structure

A policy module is one YAML document with two top-level keys:

- `policy`: metadata (required)
- `requirements`: mapping entries (required)

### Required fields

The `policy` object MUST include:

- `policy.id` (string)
- `policy.name` (string)
- `policy.version` (string)

Each entry in `requirements` MUST include:

- `code` (string): stable identifier for the requirement in this module (for human traceability)
- `description` (string): human-readable intent
- `required_evidence` (list of strings): **GovAI evidence/requirement codes** already compatible with the engine

### Example skeleton

```yaml
policy:
  id: "ai-act-high-risk"
  name: "EU AI Act — High-Risk (example mapping)"
  version: "0.1.0"

requirements:
  - code: "AIACT.HR.01"
    description: "Maintain evidence of model evaluation before promotion."
    required_evidence:
      - evaluation_reported
```

---

## Determinism and “no runtime logic”

Allowed:

- static lists
- plain strings
- YAML anchors/aliases for deduplication (still static)

Not allowed:

- conditionals (for example “if OpenAI used then require X”)
- discovery-dependent branching inside the module
- templating / code generation at runtime
- reading environment variables
- fetching remote content

If you need conditional behavior, it belongs in **your CI / change-management process**, not inside GovAI’s policy module layer.

---

## Output: flat required evidence set

The only intended output of a policy module is a **flat set**:

- Union of all `requirements[*].required_evidence`
- Deduplicated
- No ordering requirements (ordering is a presentation concern)

The GovAI engine continues to:

- compute `missing_evidence` as “required minus provided”
- keep `VALID` / `BLOCKED` / `INVALID` semantics unchanged

