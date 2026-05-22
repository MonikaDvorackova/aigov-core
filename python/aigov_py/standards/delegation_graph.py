from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from aigov_py.standards.common import (
    ValidationIssue,
    ValidationResult,
    canonical_digest,
    find_raw_content_fields,
)


class DelegationNodeType(str, Enum):
    HUMAN = "HUMAN"
    AGENT = "AGENT"
    SERVICE = "SERVICE"


@dataclass(frozen=True)
class DelegationNode:
    node_id: str
    node_type: DelegationNodeType
    principal_id: str | None
    agent_id: str | None


@dataclass(frozen=True)
class DelegationEdge:
    delegation_id: str
    from_node_id: str
    to_node_id: str
    capability_id: str
    scope: str
    expires_at: str | None
    parent_delegation_id: str | None


@dataclass(frozen=True)
class DelegationGraphDocument:
    schema_version: str
    graph_id: str
    tenant_scope: str
    nodes: tuple[DelegationNode, ...]
    edges: tuple[DelegationEdge, ...]


def _parse_node(raw: Any, idx: int, issues: list[ValidationIssue]) -> DelegationNode | None:
    base = f"nodes[{idx}]"
    if not isinstance(raw, Mapping):
        issues.append(
            ValidationIssue(
                code="node_invalid",
                message="each node must be an object",
                path=base,
            )
        )
        return None
    nid = raw.get("node_id")
    if not isinstance(nid, str) or not nid.strip():
        issues.append(
            ValidationIssue(
                code="node_id_required",
                message="node_id is required",
                path=f"{base}.node_id",
            )
        )
        return None
    nt_raw = raw.get("node_type")
    nt: DelegationNodeType | None = None
    if isinstance(nt_raw, str):
        try:
            nt = DelegationNodeType(nt_raw.strip())
        except ValueError:
            issues.append(
                ValidationIssue(
                    code="node_type_invalid",
                    message="node_type must be HUMAN, AGENT, or SERVICE",
                    path=f"{base}.node_type",
                )
            )
    else:
        issues.append(
            ValidationIssue(
                code="node_type_invalid",
                message="node_type must be a string",
                path=f"{base}.node_type",
            )
        )
    pid = raw.get("principal_id")
    if pid is not None and (not isinstance(pid, str) or not pid.strip()):
        issues.append(
            ValidationIssue(
                code="principal_id_invalid",
                message="principal_id must be a non-empty string when present",
                path=f"{base}.principal_id",
            )
        )
        pid = None
    aid = raw.get("agent_id")
    if aid is not None and (not isinstance(aid, str) or not aid.strip()):
        issues.append(
            ValidationIssue(
                code="agent_id_invalid",
                message="agent_id must be a non-empty string when present",
                path=f"{base}.agent_id",
            )
        )
        aid = None
    if nt is None:
        return None
    return DelegationNode(
        node_id=nid.strip(),
        node_type=nt,
        principal_id=None if pid is None else str(pid).strip(),
        agent_id=None if aid is None else str(aid).strip(),
    )


def _parse_edge(raw: Any, idx: int, issues: list[ValidationIssue]) -> DelegationEdge | None:
    base = f"edges[{idx}]"
    if not isinstance(raw, Mapping):
        issues.append(
            ValidationIssue(
                code="edge_invalid",
                message="each edge must be an object",
                path=base,
            )
        )
        return None
    did = raw.get("delegation_id")
    if not isinstance(did, str) or not did.strip():
        issues.append(
            ValidationIssue(
                code="delegation_id_required",
                message="delegation_id is required",
                path=f"{base}.delegation_id",
            )
        )
        return None
    fn = raw.get("from_node_id")
    tn = raw.get("to_node_id")
    if not isinstance(fn, str) or not fn.strip():
        issues.append(
            ValidationIssue(
                code="from_node_required",
                message="from_node_id is required",
                path=f"{base}.from_node_id",
            )
        )
    if not isinstance(tn, str) or not tn.strip():
        issues.append(
            ValidationIssue(
                code="to_node_required",
                message="to_node_id is required",
                path=f"{base}.to_node_id",
            )
        )
    cap = raw.get("capability_id")
    if not isinstance(cap, str) or not cap.strip():
        issues.append(
            ValidationIssue(
                code="capability_id_required",
                message="capability_id is required on each edge",
                path=f"{base}.capability_id",
            )
        )
    sc = raw.get("scope")
    if not isinstance(sc, str):
        issues.append(
            ValidationIssue(
                code="scope_invalid",
                message="scope must be a string",
                path=f"{base}.scope",
            )
        )
    ex = raw.get("expires_at")
    if ex is not None and (not isinstance(ex, str) or not ex.strip()):
        issues.append(
            ValidationIssue(
                code="expires_at_invalid",
                message="expires_at must be a non-empty string when present",
                path=f"{base}.expires_at",
            )
        )
        ex = None
    parent = raw.get("parent_delegation_id")
    if parent is not None and (not isinstance(parent, str) or not parent.strip()):
        issues.append(
            ValidationIssue(
                code="parent_delegation_invalid",
                message="parent_delegation_id must be a non-empty string when present",
                path=f"{base}.parent_delegation_id",
            )
        )
        parent = None
    if not isinstance(fn, str) or not isinstance(tn, str) or not isinstance(cap, str) or not isinstance(sc, str):
        return None
    if not fn.strip() or not tn.strip() or not cap.strip():
        return None
    return DelegationEdge(
        delegation_id=did.strip(),
        from_node_id=fn.strip(),
        to_node_id=tn.strip(),
        capability_id=cap.strip(),
        scope=sc if isinstance(sc, str) else "",
        expires_at=None if ex is None else str(ex).strip(),
        parent_delegation_id=None if parent is None else str(parent).strip(),
    )


def delegation_graph_document_from_dict(
    data: Any,
) -> tuple[DelegationGraphDocument | None, tuple[ValidationIssue, ...]]:
    issues: list[ValidationIssue] = []
    if not isinstance(data, Mapping):
        return None, (ValidationIssue(code="root_invalid", message="document root must be an object", path=""),)

    issues.extend(find_raw_content_fields(data))

    sv = data.get("schema_version")
    if not isinstance(sv, str) or not sv.strip():
        issues.append(
            ValidationIssue(
                code="schema_version_required",
                message="schema_version is required",
                path="schema_version",
            )
        )

    gid = data.get("graph_id")
    if not isinstance(gid, str) or not gid.strip():
        issues.append(
            ValidationIssue(
                code="graph_id_required",
                message="graph_id is required",
                path="graph_id",
            )
        )

    ts = data.get("tenant_scope")
    if not isinstance(ts, str) or not ts.strip():
        issues.append(
            ValidationIssue(
                code="tenant_scope_required",
                message="tenant_scope is required",
                path="tenant_scope",
            )
        )

    nodes_raw = data.get("nodes")
    if not isinstance(nodes_raw, list) or len(nodes_raw) == 0:
        issues.append(
            ValidationIssue(
                code="nodes_required",
                message="nodes must be a non-empty array",
                path="nodes",
            )
        )
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))

    node_map: dict[str, DelegationNode] = {}
    for i, raw in enumerate(nodes_raw):
        n = _parse_node(raw, i, issues)
        if n is None:
            continue
        if n.node_id in node_map:
            issues.append(
                ValidationIssue(
                    code="node_id_duplicate",
                    message=f"duplicate node_id: {n.node_id}",
                    path=f"nodes[{i}].node_id",
                )
            )
            continue
        node_map[n.node_id] = n

    edges_raw = data.get("edges", [])
    if not isinstance(edges_raw, list):
        issues.append(
            ValidationIssue(
                code="edges_invalid",
                message="edges must be an array",
                path="edges",
            )
        )
        edges_raw = []

    edges: list[DelegationEdge] = []
    seen_del: set[str] = set()
    for i, raw in enumerate(edges_raw):
        e = _parse_edge(raw, i, issues)
        if e is None:
            continue
        if e.delegation_id in seen_del:
            issues.append(
                ValidationIssue(
                    code="delegation_id_duplicate",
                    message=f"duplicate delegation_id: {e.delegation_id}",
                    path=f"edges[{i}].delegation_id",
                )
            )
            continue
        seen_del.add(e.delegation_id)
        edges.append(e)

    if not isinstance(sv, str) or not sv.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    if not isinstance(gid, str) or not gid.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    if not isinstance(ts, str) or not ts.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))

    if len(node_map) == 0:
        issues.append(
            ValidationIssue(
                code="nodes_invalid",
                message="no valid nodes parsed",
                path="nodes",
            )
        )

    doc = DelegationGraphDocument(
        schema_version=sv.strip(),
        graph_id=gid.strip(),
        tenant_scope=ts.strip(),
        nodes=tuple(node_map.values()),
        edges=tuple(edges),
    )
    return doc, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))


def _has_cycle(adj: dict[str, list[str]]) -> bool:
    """Kahn topological sort: if processed count != |V|, the graph has a cycle."""
    all_nodes: set[str] = set(adj.keys())
    for vs in adj.values():
        all_nodes.update(vs)
    indeg = {n: 0 for n in all_nodes}
    for u, vs in adj.items():
        for v in vs:
            indeg[v] = indeg.get(v, 0) + 1
    q: deque[str] = deque(n for n in all_nodes if indeg[n] == 0)
    processed = 0
    while q:
        u = q.popleft()
        processed += 1
        for v in adj.get(u, ()):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return processed != len(all_nodes)


def canonical_delegation_graph_document(doc: DelegationGraphDocument) -> dict[str, Any]:
    nodes_sorted = sorted(doc.nodes, key=lambda n: n.node_id)
    edges_sorted = sorted(doc.edges, key=lambda e: (e.delegation_id,))
    return {
        "edges": [
            {
                "capability_id": e.capability_id,
                "delegation_id": e.delegation_id,
                "expires_at": e.expires_at,
                "from_node_id": e.from_node_id,
                "parent_delegation_id": e.parent_delegation_id,
                "scope": e.scope,
                "to_node_id": e.to_node_id,
            }
            for e in edges_sorted
        ],
        "graph_id": doc.graph_id,
        "nodes": [
            {
                "agent_id": n.agent_id,
                "node_id": n.node_id,
                "node_type": n.node_type.value,
                "principal_id": n.principal_id,
            }
            for n in nodes_sorted
        ],
        "schema_version": doc.schema_version,
        "tenant_scope": doc.tenant_scope,
    }


def digest_delegation_graph_document(doc: DelegationGraphDocument) -> str:
    return canonical_digest(canonical_delegation_graph_document(doc))


def validate_delegation_graph_document(data: Any) -> ValidationResult:
    doc, parse_issues = delegation_graph_document_from_dict(data)
    issues = list(parse_issues)
    if doc is None:
        return ValidationResult(ok=False, issues=tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message))))

    node_ids = {n.node_id for n in doc.nodes}
    del_ids = {e.delegation_id for e in doc.edges}

    adj: dict[str, list[str]] = defaultdict(list)
    for i, e in enumerate(doc.edges):
        base = f"edges[{i}]"
        if e.from_node_id not in node_ids:
            issues.append(
                ValidationIssue(
                    code="edge_from_unknown",
                    message=f"from_node_id not found: {e.from_node_id}",
                    path=f"{base}.from_node_id",
                )
            )
        if e.to_node_id not in node_ids:
            issues.append(
                ValidationIssue(
                    code="edge_to_unknown",
                    message=f"to_node_id not found: {e.to_node_id}",
                    path=f"{base}.to_node_id",
                )
            )
        if e.parent_delegation_id is not None and e.parent_delegation_id not in del_ids:
            issues.append(
                ValidationIssue(
                    code="parent_delegation_unresolved",
                    message=f"parent_delegation_id not found: {e.parent_delegation_id}",
                    path=f"{base}.parent_delegation_id",
                )
            )
        adj[e.from_node_id].append(e.to_node_id)

    if _has_cycle(adj):
        issues.append(
            ValidationIssue(
                code="graph_cycle",
                message="delegation graph contains a cycle (from_node_id -> to_node_id edges)",
                path="edges",
            )
        )

    issues_sorted = tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    ok = len(issues_sorted) == 0
    d = digest_delegation_graph_document(doc) if ok else None
    return ValidationResult(ok=ok, issues=issues_sorted, digest=d)
