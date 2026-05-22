from __future__ import annotations

import copy
import json
from pathlib import Path

from aigov_py.standards.delegation_graph import (
    digest_delegation_graph_document,
    validate_delegation_graph_document,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _example() -> dict:
    p = _repo_root() / "examples" / "standards" / "delegation_graph.valid.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_delegation_graph_example_valid() -> None:
    res = validate_delegation_graph_document(_example())
    assert res.ok
    assert res.digest is not None


def test_delegation_graph_cycle_detected() -> None:
    doc = _example()
    doc["edges"] = [
        {
            "delegation_id": "e1",
            "from_node_id": "n_human",
            "to_node_id": "n_agent",
            "capability_id": "cap.read_docs",
            "scope": "a",
        },
        {
            "delegation_id": "e2",
            "from_node_id": "n_agent",
            "to_node_id": "n_human",
            "capability_id": "cap.read_docs",
            "scope": "b",
        },
    ]
    res = validate_delegation_graph_document(doc)
    assert not res.ok
    assert any(i.code == "graph_cycle" for i in res.issues)


def test_delegation_graph_unknown_node_on_edge() -> None:
    doc = _example()
    doc["edges"][0]["to_node_id"] = "n_missing"
    res = validate_delegation_graph_document(doc)
    assert not res.ok


def test_delegation_graph_parent_unresolved() -> None:
    doc = _example()
    doc["edges"][0]["parent_delegation_id"] = "no_such"
    res = validate_delegation_graph_document(doc)
    assert not res.ok


def test_delegation_graph_digest_changes_when_graph_id_changes() -> None:
    from aigov_py.standards.delegation_graph import delegation_graph_document_from_dict

    d1, _ = delegation_graph_document_from_dict(_example())
    assert d1 is not None
    x = copy.deepcopy(_example())
    x["graph_id"] = "graph.other"
    d2, _ = delegation_graph_document_from_dict(x)
    assert d2 is not None
    assert digest_delegation_graph_document(d1) != digest_delegation_graph_document(d2)


def test_delegation_graph_raw_content_rejected() -> None:
    doc = _example()
    doc["nodes"][0]["content"] = "x"
    res = validate_delegation_graph_document(doc)
    assert not res.ok
