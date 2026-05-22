## Policies (customer-replaceable modules)

GovAI’s core engine evaluates runs against a **flat set of `required_evidence` codes** and produces deterministic verdicts (`VALID`, `BLOCKED`, `INVALID`) via `GET /compliance-summary`.

GovAI does **not** enforce legal frameworks directly.

Instead, legal/regulatory/internal frameworks are modeled as a **product-layer policy module** that maps “what your policy requires” → “which evidence codes must exist for a run”.

### What this folder is

- **Policy modules**: static YAML files that compile into a flat `required_evidence` set.
- **Examples**: reference mappings for common starting points.

### What this folder is not

- Not executable logic.
- Not a rules engine.
- Not a place to implement conditionals based on runtime data.

### Examples included

- `ai-act-high-risk.example.yaml`: example mapping for an “AI Act high-risk” framing (illustrative only).
- `internal-genai-policy.example.yaml`: example mapping for an internal GenAI policy.

### Why “AI Act” is just one policy

The EU AI Act can be one policy module among many:

- internal policy (security/approval gates)
- sector policy (health/finance)
- customer contract policy (procurement requirements)

GovAI remains policy-agnostic: it enforces **evidence completeness and deterministic decision semantics**, not legal interpretation.

---

## CLI usage (compile-only)

Compile a policy module YAML into a flat `required_evidence` set:

```bash
govai policy compile --path docs/policies/ai-act-high-risk.example.yaml
```

Machine-readable JSON:

```bash
govai policy compile --path docs/policies/ai-act-high-risk.example.yaml --json
```

---

## Policy replacement workflow (customer-side)

1) Copy an example module (start small):

- `docs/policies/internal-genai-policy.example.yaml`

2) Set policy identity fields:

- `policy.id`
- `policy.name`
- `policy.version`

3) Update `requirements[*]`:

- each requirement has a stable `code`
- each requirement lists `required_evidence` codes (existing GovAI evidence codes)

4) Compile and inspect the required evidence:

```bash
govai policy compile --path /path/to/your-policy.yaml
```

5) Compare versions by diffing compiled output:

```bash
govai policy compile --path /path/to/policy-v1.yaml > /tmp/policy-v1.txt
govai policy compile --path /path/to/policy-v2.yaml > /tmp/policy-v2.txt
diff -u /tmp/policy-v1.txt /tmp/policy-v2.txt
```

Note: this repository currently provides **compile-only** tooling. Backend enforcement configuration is separate.

