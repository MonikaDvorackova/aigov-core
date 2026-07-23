# Linux self-hosted runner readiness (Phase 1)

Status as of this document: **BLOCKED — Linux runner not registered**.

## Current verified state

GitHub API (`GET /repos/{owner}/{repo}/actions/runners`) for both
`MonikaDvorackova/aigov-compliance-engine` and `MonikaDvorackova/aigov-core`
returns a single runner:

| Field | Value |
|-------|--------|
| Name | `Monika-MacBook-Air` |
| Status | online |
| OS | macOS |
| Labels | `self-hosted`, `macOS`, `X64` |
| Suitable for nightly | **No** |

GitHub Actions **service containers** (including `postgres:`) require Linux.
Nightly workflows must **not** use this Mac runner and must **not** fall back
to `ubuntu-latest` after migration (would consume private hosted minutes).

## Required production runner (before Phase 3 nightly)

Provision a **Linux** self-hosted runner (recommended: Linux VM on the Mac, or
a dedicated Linux host). Register it to both repositories (or an org runner
group) with **all** of these labels:

```text
self-hosted
linux
x64
aigov-nightly
```

Optional isolation labels (if two VMs or concurrent capacity exists):

```text
aigov-core
aigov-engine
```

Do **not** put `aigov-nightly` on the Mac runner.

## Readiness checklist (must all pass)

- [ ] Runner appears online in both repos with the labels above
- [ ] Runner service starts automatically after host reboot
- [ ] Host does not sleep during the planned nightly window (Europe/Prague)
- [ ] Docker Engine available **or** local PostgreSQL 16 install documented
- [ ] Proof: `docker compose` (or equivalent) can start Postgres and accept TCP connections
- [ ] Rust stable toolchain (`cargo`, `rustc`) installed
- [ ] Python 3.11 + `venv` / `pip` installed
- [ ] Node 20 available if release/nightly Node steps remain
- [ ] Sufficient free disk (recommend ≥40 GiB free on the runner volume)
- [ ] Dedicated work directories per repo; jobs cannot clobber each other’s trees
- [ ] No production secrets, personal SSH keys, or cloud admin creds in the runner environment beyond what nightly needs
- [ ] Runner GitHub token / registration uses minimum access
- [ ] Workflows using `aigov-nightly` are limited to `schedule` and `workflow_dispatch` (never fork `pull_request`)
- [ ] Manual `workflow_dispatch` of a dry-run job on `aigov-nightly` succeeds

## Failure mode after nightly retarget (Phase 3)

If no runner matches `aigov-nightly`, the job must **queue or fail visibly**.
There must be **no** `ubuntu-latest` fallback.

## Phase gate

| Phase | Allowed when |
|-------|----------------|
| 1 (this doc + push YAML fixes) | Always |
| 2 CLA | Independent of runner |
| 3 Nightly retarget | **Only after checklist is complete** |
| 4+ PR slim / hardening | After nightly proven on Linux |

## Related

- Architecture: Cursor canvas `cicd-architecture-spec`
- Prior Mac/`services:` failure: `docs/reports/nightly-full-validation-linux-runner-audit.md` (Core) / Engine equivalent notes
