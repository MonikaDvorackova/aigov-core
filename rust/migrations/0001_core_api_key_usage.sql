-- Core: per-API-key operational usage counters (not billing).

create table if not exists public.govai_api_key_usage (
    key_hash text primary key,
    request_count bigint not null default 0,
    evidence_ingest_count bigint not null default 0,
    compliance_summary_read_count bigint not null default 0,
    updated_at timestamptz not null default now()
);

create index if not exists govai_api_key_usage_updated_at_idx
    on public.govai_api_key_usage (updated_at desc);
