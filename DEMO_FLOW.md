# Demo flow (v0.1)

Exact commands and **representative** expected outputs. UUIDs, accuracy, and hashes change each run.

> **Disclaimer:** This is a **research prototype**. Outputs describe what the current code prints or returns; they are **not** legal or compliance guarantees.

## Prerequisites

1. **`DATABASE_URL`** — Postgres connection string (required for `make audit` / `audit_bg`). For a **clean clone / reproducible** enterprise demo, apply the SQL migrations **in order** to that same database (`rust/migrations/0001_govai_core.sql`, `0002_add_compliance_context_fields.sql`, `0003_compliance_workflow.sql`) so `teams`, `team_members`, and **`compliance_workflow`** exist. Without this, `/api/*` handlers that touch Postgres return DB errors. Deeper semantics (teams, RBAC): [ENTERPRISE_LAYER.md](ENTERPRISE_LAYER.md).
2. **Python venv** — `cd python && . .venv/bin/activate` with `pip install -e .` (see [README.md](README.md)).
3. For **`make demo_new`** / **`make db_ingest`**: **`SUPABASE_URL`** and **`SUPABASE_SERVICE_ROLE_KEY`**, and the `supabase` Python package if not already installed.
4. **Auth and team scope for `/api/*`** (enterprise workflow, assessments, `GET /api/me`) — required for the steps in **§2b**:
   - Set **`SUPABASE_URL`** in the Rust process environment (JWKS fetch). Optionally **`SUPABASE_JWT_AUD`** for audience validation (`rust/src/auth.rs`). Without a valid issuer/JWKS config, **`/api/*`** returns **`500`** or auth errors — same env must be used across **`make audit_bg`**, DB, and curl so a **clean clone** reproduces the same behavior.
   - **Every** `/api/*` request must include **`Authorization: Bearer <JWT>`** (Supabase session or compatible token).
   - **Team header (reproducibility):** **`x-govai-team-id: <team-uuid>`** is optional but **recommended** for a deterministic demo: pick **`teams.id`** from your seeded `team_members` rows, or from **`GET /api/me`** → **`teams[].id`**. That way queue rows line up with the membership you expect. If omitted, the server uses a default team or bootstraps one (`resolve_team_id` in `rust/src/govai_api.rs`), which can differ across DBs/users.
   - **Errors:** invalid UUID in the header → **`400`** `{"error":"INVALID_TEAM_ID"}`; user not in team → **`403`** `{"error":"NOT_TEAM_MEMBER"}`; insufficient product permission → **`403`** `{"error":"FORBIDDEN","reason":"INSUFFICIENT_ROLE","required_permission":"…"}`.

## Golden run reference path

One canonical **`run_id`** with symlinked pointers to evidence, report, audit JSON, and packs lives under **[docs/demo/golden-run/README.md](docs/demo/golden-run/README.md)**. Compliance-summary JSON is not duplicated there (ledger-dependent API); see **[docs/demo/golden-run/COMPLIANCE_SUMMARY.md](docs/demo/golden-run/COMPLIANCE_SUMMARY.md)**.

## 1. Start the evidence service

```bash
make audit_bg
```

**Expected (stdout):** `starting aigov_audit in background on http://127.0.0.1:8088`, then `ready on http://127.0.0.1:8088` — or `aigov_audit already running on http://127.0.0.1:8088` if the service was already up.

The Rust process prints `govai listening on http://…` to **its** stdout (captured in `.aigov_audit.log` when using `audit_bg`).

```bash
make status
```

**Expected:** `{"ok":true,"policy_version":"v0.4_human_approval"}`

```bash
make verify
```

**Expected:** JSON including `"ok":true` and `"policy_version":"v0.4_human_approval"` when the hash chain is intact; otherwise `"ok":false` with an `error` string.

> `GET /status` is a lightweight liveness check and **includes** `policy_version`. `GET /verify` additionally validates the full append-only chain in `rust/audit_log.jsonl`.

## 2. Training run (stops at human approval)

```bash
make run
```

**Expected (stdout):**

- `done run_id=<uuid> accuracy=<float> passed=<true|false>`
- Blank line, then `pending_human_approval`
- Printed `curl` examples and `make bundle RUN_ID=<uuid>`

Copy **`RUN_ID`** for the next steps.

## 2b. Enterprise compliance workflow (API queue)

This is **app-layer state** in Postgres (`compliance_workflow`). It does **not** append to `audit_log.jsonl` and does **not** replace **`make approve`** / **`make promote`** (those post evidence via `POST /evidence`). Use it to mirror an internal review queue. Deeper semantics: [ENTERPRISE_LAYER.md](ENTERPRISE_LAYER.md).

**Base URL (align with Makefile):** use the same origin as **`make status`** — Makefile defines **`AUDIT_URL`** (default **`http://127.0.0.1:8088`**). The Python pipeline uses **`AIGOV_AUDIT_URL`** for the same service; when mixing **`make run`** and these curls, keep host/port identical (e.g. `export AUDIT_URL="${AIGOV_AUDIT_URL:-http://127.0.0.1:8088}"`).

| Step | Method | Path | Body (JSON) |
|------|--------|------|-------------|
| Register in queue | `POST` | `/api/compliance-workflow` | `{"run_id":"<RUN_ID>"}` |
| Review decision | `POST` | `/api/compliance-workflow/<RUN_ID>/review` | `{"decision":"approve"}` or `"reject"` |
| Promotion decision | `POST` | `/api/compliance-workflow/<RUN_ID>/promotion` | `{"decision":"allow"}` or `"block"` |

**Permissions (product RBAC, `rust/src/rbac.rs`):** list and single-row **`GET`** need **`review_queue_view`**; **register** and **review** need **`decision_submit`**; **promotion** needs **`promotion_action`**. On denial: **`403`** with `{"error":"FORBIDDEN","reason":"INSUFFICIENT_ROLE","required_permission":"…"}`. **Demo pitfall:** the **`reviewer`** DB role has `decision_submit` but **not** `promotion_action`; use **`compliance_officer`**, **`risk_officer`**, **`admin`**, or **`owner`** (or switch user/JWT) for the promotion step, or expect **`403`** on **`POST …/promotion`**.

**States** (see migration): `pending_review` → `approved` or `rejected` after review; from `approved`, promotion moves to `promotion_allowed` or `promotion_blocked`. Wrong transition: **`409`** `{"error":"INVALID_STATE","message":"…"}` — e.g. review when not pending: `"expected pending_review for review decision"`; promotion when not approved: `"expected approved for promotion decision"`. Bad decision strings: **`400`** `{"error":"INVALID_DECISION","expected":["approve","reject"]}` or `["allow","block"]`. Empty **`run_id`** on register: **`400`** `{"error":"RUN_ID_REQUIRED"}`.

**Representative success shape** (`POST` register / review / promotion return the same `workflow` object type):

```json
{
  "ok": true,
  "workflow": {
    "id": "<uuid>",
    "team_id": "<uuid>",
    "run_id": "<RUN_ID>",
    "state": "pending_review",
    "created_at": "<rfc3339>",
    "updated_at": "<rfc3339>",
    "created_by": "<user-uuid>",
    "updated_by": null
  }
}
```

(`updated_by` is set after transitions; states and UUIDs vary.)

With the audit service up:

```bash
export AUDIT_URL="${AUDIT_URL:-${AIGOV_AUDIT_URL:-http://127.0.0.1:8088}}"
export TOKEN="<supabase-jwt>"
export TEAM_ID="<team-uuid>"   # optional; use GET /api/me → teams[].id for reproducibility
export RUN_ID="<uuid-from-step-2>"
```

Discover teams and effective permissions (optional):

```bash
curl -sS "$AUDIT_URL/api/me" \
  -H "Authorization: Bearer $TOKEN"
```

**Representative output:** JSON with **`user_id`** and **`teams`** (each team: **`id`**, **`name`**, **`role`**, **`effective_role`**, **`permissions`** with boolean flags such as **`decision_submit`**, **`promotion_action`**).

**1) Register run in queue** (`pending_review` on first insert; idempotent if already present):

```bash
curl -sS -X POST "$AUDIT_URL/api/compliance-workflow" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "x-govai-team-id: $TEAM_ID" \
  -d "{\"run_id\":\"$RUN_ID\"}"
```

**Expected:** `{"ok":true,"workflow":{…}}` with **`id`**, **`team_id`**, **`run_id`**, **`state`**, **`created_at`**, **`updated_at`**, **`created_by`**, **`updated_by`**. On the **first** registration for that `(team_id, run_id)`, **`state`** is **`pending_review`**. A duplicate `POST` returns **200** with the **existing** row (state may already be **`approved`**, **`rejected`**, **`promotion_*`**, etc.—the server does not reset it).

**2) Review decision** (only from `pending_review`):

```bash
curl -sS -X POST "$AUDIT_URL/api/compliance-workflow/$RUN_ID/review" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "x-govai-team-id: $TEAM_ID" \
  -d '{"decision":"approve"}'
```

Use **`"decision":"reject"`** to end in `rejected`. **`400`** with `INVALID_DECISION` and `"expected":["approve","reject"]` if the value is wrong.

**Expected on success:** `{"ok":true,"workflow":{…}}` with `"state":"approved"` or `"state":"rejected"`.

**3) Promotion decision** (only from `approved`):

```bash
curl -sS -X POST "$AUDIT_URL/api/compliance-workflow/$RUN_ID/promotion" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "x-govai-team-id: $TEAM_ID" \
  -d '{"decision":"allow"}'
```

Use **`"decision":"block"`** for `promotion_blocked`. **`400`** with `INVALID_DECISION` and `"expected":["allow","block"]` if the value is wrong.

**Expected on success:** `{"ok":true,"workflow":{…}}` with `"state":"promotion_allowed"` or `"state":"promotion_blocked"`.

**List / inspect (optional):**

```bash
curl -sS "$AUDIT_URL/api/compliance-workflow?state=pending_review" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-govai-team-id: $TEAM_ID"
```

**Expected:** `{"ok":true,"items":[…]}` (each element matches the **`workflow`** object shape above).

```bash
curl -sS "$AUDIT_URL/api/compliance-workflow/$RUN_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-govai-team-id: $TEAM_ID"
```

**Expected:** `{"ok":true,"workflow":{…}}` or **`404`** `{"error":"NOT_FOUND"}`.

### Final enterprise demo sequence (end-to-end)

1. **`make audit_bg`** — service listening (e.g. `http://127.0.0.1:8088`); **`make status`** should return `{"ok":true,"policy_version":"…"}`.
2. **Clean-repo prerequisites:** **`DATABASE_URL`** set for the Rust process; migrations **`0001`**–**`0003`** applied to that database; **`SUPABASE_URL`** (JWKS) in the same environment as the server; a valid **`Authorization: Bearer`** JWT for a user present in **`team_members`** when using **`x-govai-team-id`**.
3. **`make run`** — copy **`RUN_ID`** from stdout.
4. Export **`AUDIT_URL`** (same default as Makefile; match **`AIGOV_AUDIT_URL`** if you use the Python train path), **`TOKEN`**, and **`TEAM_ID`** — use **`GET /api/me`** to copy **`teams[].id`** when you need a stable team scope.
5. **Register in queue:** **`POST /api/compliance-workflow`** with `{"run_id":"$RUN_ID"}` → **`200`**, body `{"ok":true,"workflow":{…}}`; on first registration **`workflow.state`** is **`pending_review`** (a duplicate `POST` returns the current row unchanged).
6. **Review decision:** **`POST /api/compliance-workflow/$RUN_ID/review`** with `{"decision":"approve"}` or `{"decision":"reject"}` → workflow state **`approved`** or **`rejected`** (stop here if rejected).
7. **Promotion decision:** **`POST /api/compliance-workflow/$RUN_ID/promotion`** with `{"decision":"allow"}` or `{"decision":"block"}` (requires **`promotion_action`**; see RBAC note above) → **`promotion_allowed`** or **`promotion_blocked`**.
8. Optionally **`GET /api/compliance-workflow?state=…`** and **`GET /api/compliance-workflow/$RUN_ID`** to inspect the queue.

**Ledger parity:** the workflow API does **not** write **`audit_log.jsonl`**. For real **`human_approved`** / **`model_promoted`** evidence events, still run **`make approve`** and **`make promote`** (§3–4) in addition to or after the API steps above.

## 3. Human approval

```bash
RUN_ID=<uuid-from-step-2> make approve
```

**Expected:** JSON line from the service, e.g. `{"ok":true,"record_hash":"…","policy_version":"v0.4_human_approval"}` (exact hash varies).

## 4. Promotion

Requires the joblib artifact from training: `python/artifacts/model_<RUN_ID>.joblib`.

```bash
RUN_ID=<uuid> make promote
```

**Expected:** JSON with `"ok":true` on success; policy errors return `"ok":false` with an `error` message.

## 5. Report, audit manifest, pack, CLI verify

```bash
RUN_ID=<uuid> make report_prepare
```

This runs (via Makefile): `ensure_evidence` → `report` → `export_bundle` → `verify_cli`.

**Expected:**

- `ensure_evidence`: either fetches from `GET /bundle` / `GET /bundle-hash`, or falls back to `ci_fallback` when `AIGOV_MODE` is not `prod` and fetch fails.
- `report`: writes `docs/reports/<RUN_ID>.md` (includes sections required by `make gate`: `## Evaluation gate`, `## Human approval gate`).
- `export_bundle`: prints paths to `docs/audit/<RUN_ID>.json` and `docs/packs/<RUN_ID>.zip` and `bundle_sha256=…`.
- `verify_cli` (`python -m aigov_py.verify`): prints `AIGOV VERIFICATION REPORT`, lines such as `OK   audit file present` / `OK   governance hash chain verified`, and ends with **`ARTIFACTS_OK`** or **`ARTIFACTS_INVALID`**.

### One-shot (train → gates → bundle → compliance summary JSON)

`make flow_full` runs **`run` → `approve` → `promote` → `report_prepare`**, then **`GET /compliance-summary?run_id=…`** (response printed to stdout). `make flow` is an alias.

```bash
make audit_bg
RUN_ID=$(make new_run)
export RUN_ID
make flow_full RUN_ID="$RUN_ID"
```

Requires **`DATABASE_URL`**, audit up (`check_audit`), and default **`AUDIT_URL`** unless overridden.

## 6. Makefile demo targets

### `make demo_new` (full iris path + artifacts + ingest)

```bash
make demo_new
```

**Expected:** prints `DEMO: generated RUN_ID=…`, then runs `run` → `approve` → `promote` → `report_prepare` → `db_ingest`, then `OK: demo completed RUN_ID=…` and `Dashboard: /runs/<RUN_ID>`.

**Note:** `db_ingest` fails if Supabase env vars or the `supabase` Python client are missing — use the manual path (steps 1–5) without ingest if you only want local files under `docs/`.

### `make demo RUN_ID=<uuid>` (full path with a fixed id)

Same sequence as `make demo_new`, but uses your **`RUN_ID`** (prefer a new uuid so the ledger does not collide with prior approvals for the same id). Same Supabase requirements as `db_ingest` above.

To **only** regenerate reports/packs for a run that already finished training/approval/promotion, run **`RUN_ID=<uuid> make report_prepare`** (and optionally **`make db_ingest`**).

## 7. Optional: audit pack only (`export_bundle`)

`make bundle` is an alias for `python -m aigov_py.export_bundle` (same as `make export_bundle`). It **requires** existing `docs/evidence/<RUN_ID>.json` and `docs/reports/<RUN_ID>.md` (e.g. after `report_prepare` or manual generation). It writes `docs/audit/<RUN_ID>.json` and `docs/packs/<RUN_ID>.zip`.

```bash
RUN_ID=<uuid> make bundle
```

## Dashboard

Local dev (from repo root):

```bash
cd dashboard && npm install && npm run dev
```

Set **`NEXT_PUBLIC_SUPABASE_URL`** and **`NEXT_PUBLIC_SUPABASE_ANON_KEY`** (or **`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`**, see `dashboard/lib/supabase/`) so the app can read `runs` from Supabase.

After a successful **`db_ingest`**, open **`/runs/<RUN_ID>`** (URL printed by `demo_new`).

## CI gate on reports

```bash
make gate
```

**Expected:** `gate OK; checked N reports` or `gate: no reports found; OK` if `docs/reports/` has no `*.md`.

The gate scans **every** `docs/reports/*.md`; each file must contain `## Evaluation gate` and `## Human approval gate` (regenerate with `report_prepare` or remove stale placeholders).
