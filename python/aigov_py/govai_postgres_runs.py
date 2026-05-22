from __future__ import annotations

from typing import Any, Dict

from aigov_py.psycopg_database_url import resolve_psycopg_database_url


def upsert_run_row_postgres(row: Dict[str, Any]) -> None:
    """Upsert a single run manifest row into ``console.runs`` (GovAI Postgres)."""
    try:
        import psycopg
    except ImportError as e:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Install psycopg for postgres run persistence (e.g. pip install 'aigov-py[runs-postgres]')"
        ) from e

    sql = """
    insert into console.runs (
      id, created_at, mode, status, policy_version, bundle_sha256,
      evidence_sha256, report_sha256, evidence_source, closed_at, environment
    ) values (
      %(id)s, %(created_at)s::timestamptz, %(mode)s, %(status)s, %(policy_version)s,
      %(bundle_sha256)s, %(evidence_sha256)s, %(report_sha256)s, %(evidence_source)s,
      %(closed_at)s::timestamptz, coalesce(%(environment)s, 'dev')
    )
    on conflict (id) do update set
      created_at = excluded.created_at,
      mode = excluded.mode,
      status = excluded.status,
      policy_version = excluded.policy_version,
      bundle_sha256 = excluded.bundle_sha256,
      evidence_sha256 = excluded.evidence_sha256,
      report_sha256 = excluded.report_sha256,
      evidence_source = excluded.evidence_source,
      closed_at = excluded.closed_at,
      environment = excluded.environment
    """

    with psycopg.connect(resolve_psycopg_database_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, row)
