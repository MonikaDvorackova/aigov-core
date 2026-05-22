# Evidence pack generator (customer-ready)

This repo ships a minimal, deterministic evidence pack generator so customers can create a valid evidence pack without reverse-engineering tests or demos.

Canonical customer onboarding (hosted): see [customer-onboarding-10min.md](customer-onboarding-10min.md).

```flow
preset: export
```

```docs
preset: export-flow
```

## Generate an evidence pack

This writes exactly two files:

- `<run_id>.json`
- `evidence_digest_manifest.json`

Run:

```bash
RUN_ID="example-id"
govai evidence-pack init --out evidence_pack --run-id "$RUN_ID"
```

Note:

- The command **fails if the output directory already exists**.
- Use `--force` to allow overwrite.

```bash
govai evidence-pack init --out evidence_pack --run-id "$RUN_ID" --force
```

## Submit it

Set your audit service connection:

```bash
export GOVAI_AUDIT_BASE_URL="http://127.0.0.1:8088"
export GOVAI_API_KEY="YOUR_API_KEY"
```

Then submit:

```bash
govai submit-evidence-pack --path evidence_pack --run-id "$RUN_ID"
```

## Verify it (production gate)

This checks digest continuity (`evidence_digest_manifest.json` vs hosted `/bundle-hash`) and then requires the run to be `VALID`.

```bash
govai verify-evidence-pack --require-export --path evidence_pack --run-id "$RUN_ID"
```

## Run `govai check`

```bash
govai check --run-id "$RUN_ID"
```

