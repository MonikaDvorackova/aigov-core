import json
import os
import uuid
from datetime import datetime, timezone
import hashlib

import requests
from joblib import dump
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from .prototype_domain import (
  approved_human_event_id_for_run,
  dataset_governance_iris,
  model_version_id_for_run,
  risk_lifecycle_payloads,
)

AUDIT_URL = os.environ.get("GOVAI_AUDIT_BASE_URL") or os.environ.get("AIGOV_AUDIT_URL", "http://127.0.0.1:8088")
SYSTEM = os.environ.get("AIGOV_SYSTEM", "aigov_poc")
ACTOR = os.environ.get("AIGOV_ACTOR", "monika")
THRESHOLD = float(os.environ.get("AIGOV_ACC_THRESHOLD", "0.8"))


def now_utc() -> str:
  return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def post_event(event: dict) -> dict:
  api_key = os.environ.get("GOVAI_API_KEY", "").strip()
  project = os.environ.get("GOVAI_PROJECT", "github-actions").strip() or "github-actions"

  headers = {
    "X-GovAI-Project": project,
    "Content-Type": "application/json",
  }

  if api_key:
    headers["Authorization"] = f"Bearer {api_key}"

  r = requests.post(f"{AUDIT_URL}/evidence", json=event, headers=headers, timeout=10)
  try:
    return r.json()
  except Exception:
    return {"ok": False, "error": f"non_json_response status={r.status_code}", "text": r.text}


def sha256_file(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
      h.update(chunk)
  return h.hexdigest()


def main() -> None:
  run_id = (os.environ.get("RUN_ID") or "").strip() or str(uuid.uuid4())

  dataset_gov = dataset_governance_iris()
  ai_system_id = dataset_gov["ai_system_id"]
  dataset_id = dataset_gov["dataset_id"]
  dataset_commitment = dataset_gov["dataset_governance_commitment"]
  risk_recorded_payload, risk_mitigated_payload, risk_reviewed_payload = risk_lifecycle_payloads(run_id)
  assessment_id = risk_recorded_payload["assessment_id"]
  risk_id = risk_recorded_payload["risk_id"]
  model_version_id = model_version_id_for_run(run_id)

  res = post_event(
    {
      "event_id": str(uuid.uuid4()),
      "event_type": "run_started",
      "ts_utc": now_utc(),
      "actor": ACTOR,
      "system": SYSTEM,
      "run_id": run_id,
      "payload": {
        "purpose": "poc_train_pending_approval",
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "risk_id": risk_id,
      },
    }
  )
  if not res.get("ok"):
    raise SystemExit(f"run_started failed: {res}")

  res = post_event(
    {
      "event_id": str(uuid.uuid4()),
      "event_type": "data_registered",
      "ts_utc": now_utc(),
      "actor": ACTOR,
      "system": SYSTEM,
      "run_id": run_id,
      "payload": {
        # Dataset governance fields + commitment (Article 10 core in this prototype).
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "dataset": dataset_gov["dataset"],
        "dataset_version": dataset_gov["dataset_version"],
        "dataset_fingerprint": dataset_gov["dataset_fingerprint"],
        "dataset_governance_id": dataset_gov["dataset_governance_id"],
        "dataset_governance_commitment": dataset_commitment,
        "source": dataset_gov["source"],
        "intended_use": dataset_gov["intended_use"],
        "limitations": dataset_gov["limitations"],
        "quality_summary": dataset_gov["quality_summary"],
        "governance_status": dataset_gov["governance_status"],
        # Extra traceability (nice-to-have in thesis).
        "n_rows": dataset_gov.get("n_rows", 150),
        "n_features": dataset_gov.get("n_features", 4),
        "target_names": dataset_gov.get(
          "target_names", ["setosa", "versicolor", "virginica"]
        ),
      },
    }
  )
  if not res.get("ok"):
    raise SystemExit(f"data_registered failed: {res}")

  iris = load_iris()
  X_train, X_test, y_train, y_test = train_test_split(
    iris.data, iris.target, test_size=0.2, random_state=42, stratify=iris.target
  )
  model = LogisticRegression(max_iter=200)
  model.fit(X_train, y_train)

  acc = float(model.score(X_test, y_test))
  passed = acc >= THRESHOLD

  res = post_event(
    {
      "event_id": str(uuid.uuid4()),
      "event_type": "model_trained",
      "ts_utc": now_utc(),
      "actor": ACTOR,
      "system": SYSTEM,
      "run_id": run_id,
      "payload": {
        "model_version_id": model_version_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_type": "LogisticRegression",
        "training_params": model.get_params(),
        "artifact_path": f"python/artifacts/model_{run_id}.joblib",
        "artifact_sha256": "PENDING",
      },
    }
  )
  if not res.get("ok"):
    raise SystemExit(f"model_trained failed: {res}")

  res = post_event(
    {
      "event_id": str(uuid.uuid4()),
      "event_type": "evaluation_reported",
      "ts_utc": now_utc(),
      "actor": ACTOR,
      "system": SYSTEM,
      "run_id": run_id,
      "payload": {
        "metric": "accuracy",
        "value": acc,
        "threshold": THRESHOLD,
        "passed": passed,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
      },
    }
  )
  if not res.get("ok"):
    raise SystemExit(f"evaluation_reported failed: {res}")

  os.makedirs("artifacts", exist_ok=True)

  artifact_path = f"python/artifacts/model_{run_id}.joblib"
  artifact_path_fs = os.path.join("artifacts", f"model_{run_id}.joblib")
  dump(model, artifact_path_fs)
  artifact_sha = sha256_file(artifact_path_fs)

  # Re-emit model_trained with computed artifact digest (stable for bundle evidence).
  res = post_event(
    {
      "event_id": str(uuid.uuid4()),
      "event_type": "model_trained",
      "ts_utc": now_utc(),
      "actor": ACTOR,
      "system": SYSTEM,
      "run_id": run_id,
      "payload": {
        "model_version_id": model_version_id,
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_type": "LogisticRegression",
        "training_params": model.get_params(),
        "artifact_path": artifact_path,
        "artifact_sha256": artifact_sha,
      },
    }
  )
  if not res.get("ok"):
    raise SystemExit(f"model_trained (artifact digest) failed: {res}")

  # Risk register lifecycle evidence: recorded -> mitigated -> reviewed.
  for et, payload in (
    ("risk_recorded", risk_recorded_payload),
    ("risk_mitigated", risk_mitigated_payload),
    ("risk_reviewed", risk_reviewed_payload),
  ):
    res = post_event(
      {
        "event_id": str(uuid.uuid4()),
        "event_type": et,
        "ts_utc": now_utc(),
        "actor": ACTOR,
        "system": SYSTEM,
        "run_id": run_id,
        "payload": payload,
      }
    )
    if not res.get("ok"):
      raise SystemExit(f"{et} failed: {res}")

  print(f"done run_id={run_id} accuracy={acc} passed={passed}")
  print("")
  print("pending_human_approval")
  print("")
  print("approve (curl):")
  print(
    "curl -sS -X POST http://127.0.0.1:8088/evidence -H 'Content-Type: application/json' -d "
    + json.dumps(
      {
        "event_id": approved_human_event_id_for_run(run_id),
        "event_type": "human_approved",
        "ts_utc": now_utc(),
        "actor": ACTOR,
        "system": SYSTEM,
        "run_id": run_id,
        "payload": {
          "scope": "model_promoted",
          "decision": "approve",
          "approver": "compliance_officer",
          "justification": "metrics meet threshold and dataset governance commitment verified",
          "ai_system_id": ai_system_id,
          "dataset_id": dataset_id,
          "model_version_id": model_version_id,
          "assessment_id": assessment_id,
          "risk_id": risk_id,
          "dataset_governance_commitment": dataset_commitment,
        },
      }
    )
  )
  print("")
  print("promote (curl):")
  print(
    "curl -sS -X POST http://127.0.0.1:8088/evidence -H 'Content-Type: application/json' -d "
    + json.dumps(
      {
        "event_id": f"mp_after_approval_{run_id}",
        "event_type": "model_promoted",
        "ts_utc": now_utc(),
        "actor": ACTOR,
        "system": SYSTEM,
        "run_id": run_id,
        "payload": {
          "artifact_path": artifact_path,
          "artifact_sha256": artifact_sha,
          "promotion_reason": "approved_by_human",
          "ai_system_id": ai_system_id,
          "dataset_id": dataset_id,
          "model_version_id": model_version_id,
          "assessment_id": assessment_id,
          "risk_id": risk_id,
          "dataset_governance_commitment": dataset_commitment,
          "approved_human_event_id": approved_human_event_id_for_run(run_id),
        },
      }
    )
  )
  print("")
  print("bundle:")
  print(f"make bundle RUN_ID={run_id}")


if __name__ == "__main__":
  main()
