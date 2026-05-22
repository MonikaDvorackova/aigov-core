from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict


REQUIRED_EVENTS = {
    "input_received",
    "ai_discovery_completed",
    "evidence_registered",
    "evaluation_completed",
    "approval_recorded",
    "promotion_decided",
}


REQUIRED_EVIDENCE_ITEMS = {
    "model_metadata",
    "policy_reference",
    "ai_discovery_report",
    "approval_record",
    "evaluation_result",
}


def baseline_verdict(run):
    if run["model_validation_passed"]:
        return "VALID"
    return "INVALID"


def govai_verdict(run):
    if not run["audit_run_available"]:
        return "BLOCKED"

    if not run["run_context_consistent"]:
        return "BLOCKED"

    if run["evaluation_passed"] is False:
        return "INVALID"

    if run["evaluation_passed"] is None:
        return "BLOCKED"

    if not REQUIRED_EVENTS.issubset(set(run["events"])):
        return "BLOCKED"

    if not REQUIRED_EVIDENCE_ITEMS.issubset(set(run["evidence_items"])):
        return "BLOCKED"

    if not run["approval_recorded"]:
        return "BLOCKED"

    if run["approval_granted"] is not True:
        return "BLOCKED"

    return "VALID"


def load_jsonl(path):
    events = []

    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} in {path}: {exc}"
                ) from exc

    return events


def group_by_run_id(events):
    grouped = defaultdict(list)

    for event in events:
        run_id = event.get("run_id")

        if isinstance(run_id, str) and run_id:
            grouped[run_id].append(event)

    return grouped


def latest_bool(events, key):
    for event in reversed(events):
        value = event.get(key)

        if isinstance(value, bool):
            return value

    return None


def infer_evidence_items(events):
    evidence_items = set()

    for event in events:
        event_type = event.get("event_type")

        if event_type == "ai_discovery_completed":
            evidence_items.add("ai_discovery_report")

        if event_type == "evaluation_completed":
            evidence_items.add("evaluation_result")

        if event_type == "approval_recorded":
            evidence_items.add("approval_record")

        if event_type == "evidence_registered":
            raw_items = event.get("evidence_items")
            if isinstance(raw_items, list):
                for item in raw_items:
                    if isinstance(item, str):
                        evidence_items.add(item)

            evidence_kind = event.get("evidence_kind")
            if isinstance(evidence_kind, str):
                evidence_items.add(evidence_kind)

    return sorted(evidence_items)


def infer_failure_class(run):
    if not run["run_context_consistent"]:
        return "inconsistent_context"

    if run["evaluation_passed"] is False:
        return "failed_compliance_evaluation"

    if "ai_discovery_completed" not in run["events"]:
        return "missing_discovery"

    if "evidence_registered" not in run["events"]:
        return "missing_evidence"

    if not run["approval_recorded"] or run["approval_granted"] is not True:
        return "missing_approval"

    if not REQUIRED_EVENTS.issubset(set(run["events"])):
        return "incomplete_trace"

    if not REQUIRED_EVIDENCE_ITEMS.issubset(set(run["evidence_items"])):
        return "partial_evidence"

    return "valid"


def infer_run(run_id, events):
    event_types = [
        event.get("event_type")
        for event in events
        if isinstance(event.get("event_type"), str)
    ]

    project_ids = {
        event.get("project_id")
        for event in events
        if isinstance(event.get("project_id"), str)
    }

    evaluation_events = [
        event for event in events if event.get("event_type") == "evaluation_completed"
    ]

    approval_events = [
        event for event in events if event.get("event_type") == "approval_recorded"
    ]

    evaluation_passed = latest_bool(evaluation_events, "evaluation_passed")
    approval_granted = latest_bool(approval_events, "approval_granted")

    run = {
        "run_id": run_id,
        "audit_run_available": True,
        "events": event_types,
        "evidence_items": infer_evidence_items(events),
        "model_validation_passed": evaluation_passed is not False,
        "evaluation_passed": evaluation_passed,
        "approval_recorded": "approval_recorded" in event_types,
        "approval_granted": approval_granted,
        "run_context_consistent": len(project_ids) <= 1,
        "project_ids": sorted(project_ids),
    }

    run["failure_class"] = infer_failure_class(run)

    return run


def evaluate_runs(runs):
    summary = {}

    for run in runs:
        failure_class = run["failure_class"]
        baseline = baseline_verdict(run)
        govai = govai_verdict(run)

        if failure_class not in summary:
            summary[failure_class] = {
                "total": 0,
                "baseline_miss": 0,
                "govai_detect": 0,
            }

        summary[failure_class]["total"] += 1

        if failure_class != "valid":
            if baseline == "VALID":
                summary[failure_class]["baseline_miss"] += 1

            if govai in {"INVALID", "BLOCKED"}:
                summary[failure_class]["govai_detect"] += 1

    return summary


def parse_args():
    parser = argparse.ArgumentParser(
        description="Replay GovAI JSONL audit logs into auditability detection evaluation."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to GovAI audit event JSONL file.",
    )

    parser.add_argument(
        "--out-dir",
        default="experiments/results/govai_replay",
        help="Directory where replay results will be written.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    events = load_jsonl(args.input)
    grouped = group_by_run_id(events)

    runs = [
        infer_run(run_id, run_events)
        for run_id, run_events in sorted(grouped.items())
    ]

    summary = evaluate_runs(runs)

    os.makedirs(args.out_dir, exist_ok=True)

    with open(os.path.join(args.out_dir, "replayed_runs.json"), "w", encoding="utf-8") as handle:
        json.dump(runs, handle, indent=2)

    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
