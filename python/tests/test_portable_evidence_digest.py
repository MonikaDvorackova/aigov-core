from __future__ import annotations

import json
from pathlib import Path

from aigov_py.portable_evidence_digest import portable_evidence_digest_v1


def test_portable_digest_matches_rust_fixture() -> None:
    p = Path(__file__).resolve().parent / "fixtures" / "portable_digest_fixture.json"
    bundle = json.loads(p.read_text(encoding="utf-8"))
    rid = str(bundle["run_id"])
    events = bundle["events"]
    assert isinstance(events, list)
    got = portable_evidence_digest_v1(rid, events)
    assert got == "145e4b69901eef4de368e101859e962ab313376287cab2e0b66e52b0ef5a7976"
