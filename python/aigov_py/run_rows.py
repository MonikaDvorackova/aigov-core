from __future__ import annotations

import os
from typing import Any, Dict, Tuple


def _persist_targets() -> Tuple[bool, bool]:
    """
    Returns (write_postgres, write_supabase).

    ``AIGOV_RUN_PERSISTENCE``:
      - ``supabase`` (default): existing Supabase ``runs`` table
      - ``postgres``: ``console.runs`` on GovAI Postgres only
      - ``both``: dual-write for cutover / backfill validation
    """
    raw = (os.environ.get("AIGOV_RUN_PERSISTENCE") or "supabase").strip().lower()
    if raw in ("both", "dual"):
        return True, True
    if raw in ("postgres", "govai", "pg"):
        return True, False
    if raw in ("supabase", "sb", ""):
        return False, True
    raise ValueError(
        f"Unknown AIGOV_RUN_PERSISTENCE={raw!r}; expected supabase, postgres, or both"
    )


def upsert_run_row(row: Dict[str, Any]) -> None:
    """Backend-agnostic run row upsert (phase 1: switch via ``AIGOV_RUN_PERSISTENCE``)."""
    to_pg, to_sb = _persist_targets()
    if to_pg:
        from aigov_py.govai_postgres_runs import upsert_run_row_postgres

        upsert_run_row_postgres(row)
    if to_sb:
        from aigov_py.supabase_db import upsert_run_row_via_supabase

        upsert_run_row_via_supabase(row)
