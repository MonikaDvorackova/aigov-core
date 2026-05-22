#!/usr/bin/env python3
"""Executable scenarios against live AI decision trace + tenant-console APIs."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid


def req(
    method: str,
    url: str,
    token: str,
    team_id: str,
    body: dict | None = None,
) -> tuple[int, dict]:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "x-govai-team-id": team_id,
    }
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        data = raw
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            status = resp.getcode()
            payload = json.loads(resp.read().decode("utf-8"))
            return status, payload
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"ok": False, "raw": raw}
        return e.code, payload


def main() -> int:
    base = os.environ.get("GOVAI_BASE_URL", "").rstrip("/")
    token = os.environ.get("GOVAI_ACCESS_TOKEN", "")
    team = os.environ.get("GOVAI_TEAM_ID", "")
    if not base or not token or not team:
        print("Set GOVAI_BASE_URL, GOVAI_ACCESS_TOKEN, GOVAI_TEAM_ID", file=sys.stderr)
        return 2

    sfx = uuid.uuid4().hex[:12]

    def started(run: str, agent: str, role: str) -> dict:
        return {
            "run_id": run,
            "correlation_id": f"corr-{run}",
            "trace_started": {
                "model_provider": "openai",
                "model_name": "gpt-4o-mini",
                "model_version": "2024-07-18",
                "prompt_hash": f"p-{run}",
                "input_hash": f"i-{run}",
                "agent_id": agent,
                "agent_role": role,
            },
        }

    # A: single-agent VALID — hash chain + export integrity
    run_a = f"ai_single_{sfx}"
    st, j = req("POST", f"{base}/api/ai-decision-traces", token, team, started(run_a, "solo", "decider"))
    assert st == 201 and j.get("ok") is True, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_a}/events",
        token,
        team,
        {"event_type": "completed", "payload": {"final_audit_verdict": "VALID", "output_hash": "out-a"}},
    )
    assert st == 200 and j.get("ok") is True, (st, j)
    st, ex = req("GET", f"{base}/api/ai-decision-traces/{run_a}/export", token, team)
    assert st == 200 and ex.get("trace_version") == 2, ex
    assert ex["final_audit_verdict"] == "VALID", ex
    assert ex.get("trace_integrity", {}).get("status") == "ok", ex
    assert ex.get("derived_audit_verdict") == "VALID", ex
    assert ex.get("verdict_consistent") is True, ex
    ev0 = ex["events"][0]
    assert ev0.get("event_seq") == 1 and ev0.get("event_hash"), ev0
    assert "GET /compliance-summary" in ex.get("relation_to_compliance_summary", "")

    # B: delegation multi-agent
    run_b = f"ai_multi_{sfx}"
    st, j = req("POST", f"{base}/api/ai-decision-traces", token, team, started(run_b, "lead", "orchestrator"))
    assert st == 201, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_b}/events",
        token,
        team,
        {
            "event_type": "delegation",
            "payload": {
                "parent_agent_id": "lead",
                "child_agent_id": "worker",
                "child_role": "executor",
            },
        },
    )
    assert st == 200, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_b}/events",
        token,
        team,
        {"event_type": "completed", "payload": {"final_audit_verdict": "VALID", "output_hash": "out-b"}},
    )
    assert st == 200, (st, j)
    st, ex = req("GET", f"{base}/api/ai-decision-traces/{run_b}/export", token, team)
    assert len(ex["agents"]["delegations"]) == 1, ex
    assert ex["agents"]["delegation_graph"]["delegation_chain_valid"] is True, ex

    # C: tool call + explainability on policy_eval
    run_c = f"ai_tool_{sfx}"
    st, j = req("POST", f"{base}/api/ai-decision-traces", token, team, started(run_c, "tooler", "planner"))
    assert st == 201, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_c}/events",
        token,
        team,
        {"event_type": "tool_call", "payload": {"tool_name": "search", "input_hash": "t1", "output_hash": "t2"}},
    )
    assert st == 200, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_c}/events",
        token,
        team,
        {
            "event_type": "policy_eval",
            "payload": {
                "policy_id": "pol_demo",
                "policy_version": "v1",
                "outcome": "allow",
                "reason_codes": ["OK"],
                "triggered_controls": ["ctrl-1"],
                "evidence_refs": ["ev://1"],
                "decision_rationale": "within bounds",
                "explanation_summary": "allowed",
            },
        },
    )
    assert st == 200, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_c}/events",
        token,
        team,
        {
            "event_type": "completed",
            "payload": {
                "final_audit_verdict": "VALID",
                "output_hash": "out-c",
                "explanation_summary": "run finished",
            },
        },
    )
    assert st == 200, (st, j)
    st, ex = req("GET", f"{base}/api/ai-decision-traces/{run_c}/export", token, team)
    assert ex["tool_calls"][0]["tool_name"] == "search", ex
    assert ex["policies_evaluated"][0].get("explanation_summary") == "allowed", ex

    # D: blocked derived verdict
    run_d = f"ai_block_{sfx}"
    st, j = req("POST", f"{base}/api/ai-decision-traces", token, team, started(run_d, "risk", "risk"))
    assert st == 201, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_d}/events",
        token,
        team,
        {
            "event_type": "policy_eval",
            "payload": {"policy_id": "pol_x", "policy_version": "v1", "outcome": "block", "reason_codes": ["X"]},
        },
    )
    assert st == 200, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_d}/events",
        token,
        team,
        {"event_type": "completed", "payload": {"final_audit_verdict": "BLOCKED", "output_hash": "out-d"}},
    )
    assert st == 200, (st, j)
    st, ex = req("GET", f"{base}/api/ai-decision-traces/{run_d}/export", token, team)
    assert ex["policies_evaluated"][0]["outcome"] == "block" and ex["final_audit_verdict"] == "BLOCKED", ex
    assert ex["derived_audit_verdict"] == "BLOCKED", ex

    # E: human override + warn policy + INVALID completed (consistent)
    run_e = f"ai_human_{sfx}"
    st, j = req("POST", f"{base}/api/ai-decision-traces", token, team, started(run_e, "human-loop", "approver"))
    assert st == 201, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_e}/events",
        token,
        team,
        {
            "event_type": "policy_eval",
            "payload": {
                "policy_id": "pol_warn",
                "policy_version": "v1",
                "outcome": "warn",
                "reason_codes": ["SOFT"],
            },
        },
    )
    assert st == 200, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_e}/events",
        token,
        team,
        {
            "event_type": "human_gate",
            "payload": {
                "approval_state": "approved",
                "override_state": "applied",
                "approver_principal": "alice",
                "approval_timestamp": "2026-01-02T00:00:03Z",
                "approval_reason": "exception",
            },
        },
    )
    assert st == 200, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_e}/events",
        token,
        team,
        {"event_type": "completed", "payload": {"final_audit_verdict": "INVALID", "output_hash": "out-e"}},
    )
    assert st == 200, (st, j)
    st, ex = req("GET", f"{base}/api/ai-decision-traces/{run_e}/export", token, team)
    assert ex["human"]["approval_state"] == "approved" and ex["final_audit_verdict"] == "INVALID", ex
    assert ex["human_approval_workflow"].get("override_conflicts_derived_verdict") is False, ex

    # F: invalid delegation DAG (cycle) — still VALID verdict if policy allows
    run_f = f"ai_dag_{sfx}"
    st, j = req("POST", f"{base}/api/ai-decision-traces", token, team, started(run_f, "lead", "orchestrator"))
    assert st == 201, (st, j)
    for payload in (
        {"parent_agent_id": "lead", "child_agent_id": "w1", "child_role": "a"},
        {"parent_agent_id": "w1", "child_agent_id": "lead", "child_role": "b"},
    ):
        st, j = req(
            "POST",
            f"{base}/api/ai-decision-traces/{run_f}/events",
            token,
            team,
            {"event_type": "delegation", "payload": payload},
        )
        assert st == 200, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_f}/events",
        token,
        team,
        {
            "event_type": "policy_eval",
            "payload": {"policy_id": "pol_open", "policy_version": "v1", "outcome": "allow", "reason_codes": []},
        },
    )
    assert st == 200, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_f}/events",
        token,
        team,
        {"event_type": "completed", "payload": {"final_audit_verdict": "VALID", "output_hash": "out-f"}},
    )
    assert st == 200, (st, j)
    st, ex = req("GET", f"{base}/api/ai-decision-traces/{run_f}/export", token, team)
    assert ex["agents"]["delegation_graph"]["delegation_chain_valid"] is False, ex
    assert ex["agents"]["delegation_graph"]["delegation_cycle_detected"] is True, ex

    # G: producer verdict mismatch rejected
    run_g = f"ai_mismatch_{sfx}"
    st, j = req("POST", f"{base}/api/ai-decision-traces", token, team, started(run_g, "solo", "decider"))
    assert st == 201, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_g}/events",
        token,
        team,
        {
            "event_type": "policy_eval",
            "payload": {"policy_id": "pol_b", "policy_version": "v1", "outcome": "block", "reason_codes": ["B"]},
        },
    )
    assert st == 200, (st, j)
    st, j = req(
        "POST",
        f"{base}/api/ai-decision-traces/{run_g}/events",
        token,
        team,
        {"event_type": "completed", "payload": {"final_audit_verdict": "VALID", "output_hash": "bad"}},
    )
    assert st == 400 and j.get("error", {}).get("code") == "VERDICT_MISMATCH", (st, j)

    st, snap = req("GET", f"{base}/api/tenant-console/snapshot", token, team)
    assert st == 200 and snap.get("snapshot_version") == 3, snap
    ada = snap["ai_decision_audit"]
    assert ada["data_source"] in ("postgres", "ledger_binding_required", "forbidden", "unavailable"), ada
    assert isinstance(ada["recent_traces"], list)
    assert "GET /compliance-summary" in ada["relation_to_compliance_summary"]
    if ada["data_source"] == "postgres":
        ids = {t.get("run_id") for t in ada["recent_traces"]}
        assert {run_a, run_b, run_c, run_d, run_e, run_f} & ids, ids
        row = next(x for x in ada["recent_traces"] if x.get("run_id") == run_a)
        assert row.get("trace_integrity_status") == "ok", row
        assert row.get("derived_audit_verdict") in ("VALID", "BLOCKED", "INVALID", "UNKNOWN"), row

    print("ai-decision-audit scenarios: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
