"""Tests for lineage graph CLI helpers."""

from __future__ import annotations

from unittest.mock import patch

from aigov_py.lineage_graph import format_lineage_summary, lineage_graph_from_export


def test_format_lineage_summary() -> None:
    doc = {
        "summary": {"run_id": "r1", "root_run_id": "r1", "lineage_integrity_status": "ok"},
        "graph": {
            "delegation_types": ["agent_delegated"],
            "governance_gates": ["evaluation"],
            "lineage_validation": {"errors": [], "delegation_cycle_detected": False},
        },
    }
    text = format_lineage_summary(doc)
    assert "r1" in text
    assert "lineage_integrity=ok" in text


def test_lineage_graph_mermaid_mode() -> None:
    with patch(
        "aigov_py.lineage_graph._find_lineage_binary",
        return_value="/bin/lineage_graph_once",
    ), patch(
        "aigov_py.lineage_graph.subprocess.run",
        return_value=type("R", (), {"returncode": 0, "stdout": "flowchart TD\n", "stderr": ""})(),
    ):
        out = lineage_graph_from_export("export.json", mermaid=True)
    assert "flowchart" in out
