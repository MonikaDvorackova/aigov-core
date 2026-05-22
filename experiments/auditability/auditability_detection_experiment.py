from __future__ import annotations

import json
import os
from collections import defaultdict


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

    if not run["has_evidence"]:
        return "BLOCKED"

    if not run["has_discovery"]:
        return "BLOCKED"

    if not run["has_approval"]:
        return "BLOCKED"

    return "VALID"


def generate_run(failure_type):
    run = {
        "model_validation_passed": True,
        "evaluation_passed": True,
        "has_evidence": True,
        "has_discovery": True,
        "has_approval": True,
        "audit_run_available": True,
        "run_context_consistent": True,
    }

    if failure_type == "missing_evidence":
        run["has_evidence"] = False

    elif failure_type == "missing_discovery":
        run["has_discovery"] = False

    elif failure_type == "missing_approval":
        run["has_approval"] = False

    elif failure_type == "failed_compliance_evaluation":
        run["evaluation_passed"] = False

    elif failure_type == "inconsistent_context":
        run["run_context_consistent"] = False

    elif failure_type == "unavailable_run":
        run["audit_run_available"] = False

    elif failure_type == "partial_evidence":
        run["has_evidence"] = False

    elif failure_type == "noisy_metadata":
        pass

    elif failure_type == "valid":
        pass

    else:
        raise ValueError(f"Unsupported failure type: {failure_type}")

    return run


def run_experiment():
    failure_types = [
        "valid",
        "missing_evidence",
        "missing_discovery",
        "missing_approval",
        "failed_compliance_evaluation",
        "inconsistent_context",
        "unavailable_run",
        "partial_evidence",
        "noisy_metadata",
    ]

    runs = []
    for failure_type in failure_types:
        for _ in range(100):
            runs.append((failure_type, generate_run(failure_type)))

    stats = defaultdict(
        lambda: {
            "total": 0,
            "baseline_miss": 0,
            "govai_detect": 0,
        }
    )

    for failure_type, run in runs:
        baseline = baseline_verdict(run)
        govai = govai_verdict(run)

        stats[failure_type]["total"] += 1

        if failure_type not in {"valid", "noisy_metadata"}:
            if baseline == "VALID":
                stats[failure_type]["baseline_miss"] += 1

            if govai in {"INVALID", "BLOCKED"}:
                stats[failure_type]["govai_detect"] += 1

    return stats


def main():
    results = run_experiment()

    output_dir = "experiments/results/auditability_detection"
    os.makedirs(output_dir, exist_ok=True)

    with open(f"{output_dir}/summary.json", "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
