from __future__ import annotations

import os
from typing import Any, Dict

from supabase import create_client


def create_supabase_client(strict: bool = True):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        if strict:
            raise RuntimeError("Supabase env variables missing")
        return None

    return create_client(url, key)


def upsert_run_row_via_supabase(row: Dict[str, Any]) -> None:
    """Write run metadata to Supabase ``runs`` (legacy path; prefer ``aigov_py.run_rows.upsert_run_row``)."""
    client = create_supabase_client(strict=True)

    # IMPORTANT: primary key column is "id"
    response = (
        client
        .table("runs")
        .upsert(row, on_conflict="id")
        .execute()
    )

    if hasattr(response, "error") and response.error:
        raise RuntimeError(f"Supabase error: {response.error}")
