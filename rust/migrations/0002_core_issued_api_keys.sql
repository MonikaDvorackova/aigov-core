-- Core: hash-only storage for operator-issued API keys (ledger tenant mapping).

create table if not exists public.govai_issued_api_keys (
    id uuid primary key,
    ledger_tenant_id text not null,
    team_id uuid not null,
    key_hash text not null,
    key_prefix text not null,
    label text not null default '',
    created_by uuid not null,
    created_at timestamptz not null default now(),
    revoked_at timestamptz,
    revealed_at timestamptz
);

create unique index if not exists govai_issued_api_keys_key_hash_active_idx
    on public.govai_issued_api_keys (key_hash)
    where revoked_at is null;

create index if not exists govai_issued_api_keys_team_id_idx
    on public.govai_issued_api_keys (team_id);
