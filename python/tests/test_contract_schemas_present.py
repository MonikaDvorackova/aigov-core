import json
from pathlib import Path


def test_contract_schemas_exist_and_have_expected_ids() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    contracts = repo_root / "contracts"

    schema_files = [
        ("govai.policy.v1.schema.json", "https://aigov.dev/schemas/govai.policy.v1.schema.json"),
        (
            "govai.signature_report.v1.schema.json",
            "https://aigov.dev/schemas/govai.signature_report.v1.schema.json",
        ),
        (
            "govai.immutable_anchor.v1.schema.json",
            "https://aigov.dev/schemas/govai.immutable_anchor.v1.schema.json",
        ),
    ]

    for filename, expected_id in schema_files:
        p = contracts / filename
        assert p.exists(), f"missing schema file: {p}"
        body = json.loads(p.read_text(encoding="utf-8"))
        assert body.get("$schema"), f"{filename} missing $schema"
        assert body.get("$id") == expected_id, f"{filename} $id mismatch"
        assert body.get("type") == "object", f"{filename} must be an object schema"
        assert body.get("additionalProperties") is False, f"{filename} must be strict by default"

