# GovAI Audit Replay Architecture (diagram)

Formal replay semantics: [../governance-semantics.md](../governance-semantics.md#reconstructibility-and-audit-replay). Evidence lifecycle: [../evidence-lifecycle.md](../evidence-lifecycle.md).

This document describes how audit replay works conceptually.

## Goal

Audit replay allows a previously exported evidence bundle to be verified outside the original CI or runtime environment.

## Flow

1. Evidence bundle is exported.

2. Export includes audit events, artifact digests, verdict metadata, and manifest data.

3. Replay command loads the evidence bundle.

4. Digest continuity is verified.

5. Policy and evidence state are reconstructed.

6. The original verdict is reproduced.

7. Any mismatch is reported as a replay failure.

## Text diagram

Evidence bundle
  ->
Replay CLI
  ->
Manifest loading
  ->
Digest continuity verification
  ->
Evidence reconstruction
  ->
Policy/verdict reconstruction
  ->
Replay result

## Replay result

Replay succeeds when:
- required artifacts exist
- digests match
- evidence state is complete
- verdict reproduction is deterministic

Replay fails when:
- evidence is missing
- artifacts are missing
- digests mismatch
- policy state cannot be reconstructed
- verdict differs from recorded state
