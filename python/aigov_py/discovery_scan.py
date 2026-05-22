from __future__ import annotations

import csv
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

# directories we NEVER scan
IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "target",
    "dist",
    "build",
    ".next",
}

# file size cap (1MB)
MAX_FILE_SIZE = 1_000_000


_PII_COLUMN_TOKENS = frozenset(
    {
        "email",
        "e-mail",
        "e_mail",
        "mail",
        "phone",
        "phone_number",
        "mobile",
        "ssn",
        "social_security",
        "social_security_number",
        "national_id",
        "passport",
        "first_name",
        "firstname",
        "last_name",
        "lastname",
        "full_name",
        "name",
        "dob",
        "date_of_birth",
        "address",
        "street",
        "zip",
        "postal",
        "postcode",
    }
)

_EXT_AI_DEPS = (
    # Hosted LLM APIs
    "openai",
    "anthropic",
    "cohere",
    "google-generativeai",
    "vertexai",
    "azure-ai-inference",
    "mistralai",
    "groq",
    "together",
    "replicate",
    "ai21",
    # OSS / Hub clients
    "huggingface_hub",
    "huggingface",
    "transformers",
    "sentence-transformers",
    "onnxruntime",
    # App-layer orchestration (deterministic presence only)
    "langchain",
    "llama_index",
    "litellm",
)

_USER_FACING_SIGS = (
    # Python web frameworks
    "from fastapi import",
    "fastapi(",
    "from flask import",
    "flask(",
    "from django",
    "django.urls",
    "starlette",
    "uvicorn.run(",
    # Node/web frameworks (string-only heuristics)
    "express()",
    "require('express')",
    "require(\"express\")",
    "next/router",
    "next/server",
    "nextjs",
    "react",
    "useeffect(",
    "usestate(",
)

_EMBEDDING_SIGS = (
    "embeddings.create",
    "embedding",
    "sentence-transformers",
    "text-embedding",
)

_CLASSIFIER_SIGS = (
    "sklearn",
    "xgboost",
    "lightgbm",
    "catboost",
    "classification_report",
    "roc_auc",
)


def _is_text_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size <= MAX_FILE_SIZE
    except Exception:
        return False


def _relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _git_available(root: Path) -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return True
    except Exception:
        return False


def _git_change_summary(root: Path, rel_file: str) -> dict[str, Any] | None:
    """
    Best-effort, deterministic-ish summary that works in CI.
    Returns None if git is unavailable.
    """
    if not _git_available(root):
        return None
    try:
        cp = subprocess.run(
            ["git", "log", "-n", "1", "--pretty=format:%H|%ad|%s", "--date=iso-strict", "--", rel_file],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        line = (cp.stdout or "").strip()
        if not line:
            return {"commits": 0}
        parts = line.split("|", 2)
        if len(parts) != 3:
            return {"commits": 1}
        commit, ts, subject = parts
        return {
            "commits": 1,
            "last_commit": {"sha": commit, "ts": ts, "subject": subject},
        }
    except Exception:
        return None


def _scan_requirements(path: Path) -> set[str]:
    packages: set[str] = set()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return packages

    for line in text.splitlines():
        line = line.strip().lower()
        if not line or line.startswith("#"):
            continue
        pkg = line.split("==")[0].split(">=")[0].strip()
        # normalize common extras / markers without attempting full PEP 508 parsing
        pkg = pkg.split("[", 1)[0].strip()
        pkg = pkg.split(";", 1)[0].strip()
        packages.add(pkg)
    return packages


def _scan_package_json(path: Path) -> set[str]:
    deps: set[str] = set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return deps

    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        block = data.get(key, {})
        if isinstance(block, dict):
            for dep in block.keys():
                deps.add(dep.lower())

    return deps


def _normalize_token(s: str) -> str:
    t = (s or "").strip().lower()
    t = re.sub(r"[^a-z0-9_]+", "_", t)
    return t.strip("_")


def _csv_pii_possible(path: Path) -> bool:
    """
    Deterministic, lightweight CSV sniff:
    - reads only the header row (or first non-empty row)
    - checks column names against a fixed token list
    """
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_SIZE:
            return False
    except Exception:
        return False
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or not any(str(x or "").strip() for x in row):
                    continue
                cols = {_normalize_token(str(c)) for c in row if str(c or "").strip()}
                return bool(cols.intersection({_normalize_token(t) for t in _PII_COLUMN_TOKENS}))
    except Exception:
        return False
    return False


def _parquet_pii_possible(path: Path) -> bool:
    """
    Deterministic parquet sniff:
    - only attempts if pyarrow is available
    - reads schema column names only (no row reads)
    """
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_SIZE:
            return False
    except Exception:
        return False
    try:
        import pyarrow.parquet as pq  # type: ignore
    except Exception:
        return False
    try:
        pf = pq.ParquetFile(str(path))
        names = list(pf.schema.names or [])
        cols = {_normalize_token(str(n)) for n in names if str(n or "").strip()}
        return bool(cols.intersection({_normalize_token(t) for t in _PII_COLUMN_TOKENS}))
    except Exception:
        return False


def scan_repo(
    root: Path,
    *,
    include_history: bool = True,
) -> dict[str, Any]:
    root = root.resolve()

    openai = False
    transformers = False
    model_artifacts = False
    anthropic = False
    embeddings = False
    classifier = False
    user_facing = False
    pii_possible = False

    external_dependencies: set[str] = set()

    findings: list[dict[str, Any]] = []

    for path in sorted(root.rglob("*")):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        rel = _relpath(path, root)

        # --- model artifacts (filename only)
        if path.is_file():
            name = path.name.lower()

            if name.endswith((".pt", ".pth", ".onnx", ".safetensors")):
                model_artifacts = True
                findings.append(
                    {
                        "detected_ai_usage": "model_artifact",
                        "file_path": rel,
                        "detector_type": "artifact_extension",
                        "confidence": 0.95,
                        "evidence": {"reason": "extension", "ext": path.suffix.lower()},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )
                continue

            if name == "pytorch_model.bin":
                model_artifacts = True
                findings.append(
                    {
                        "detected_ai_usage": "model_artifact",
                        "file_path": rel,
                        "detector_type": "artifact_filename",
                        "confidence": 0.98,
                        "evidence": {"reason": "pytorch_model.bin"},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )
                continue

            # --- PII scan (data files, deterministic + lightweight)
            if not pii_possible and name.endswith(".csv"):
                if _csv_pii_possible(path):
                    pii_possible = True
            if not pii_possible and name.endswith(".parquet"):
                if _parquet_pii_possible(path):
                    pii_possible = True

        # --- requirements.txt
        if path.name.startswith("requirements") and path.suffix == ".txt":
            pkgs = _scan_requirements(path)
            for dep in _EXT_AI_DEPS:
                if dep in pkgs:
                    external_dependencies.add(dep)

            if "openai" in pkgs:
                openai = True
                findings.append(
                    {
                        "detected_ai_usage": "openai",
                        "file_path": rel,
                        "detector_type": "dependency_requirements_txt",
                        "confidence": 0.9,
                        "evidence": {"reason": "requirements", "package": "openai"},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )

            if "transformers" in pkgs:
                transformers = True
                findings.append(
                    {
                        "detected_ai_usage": "transformers",
                        "file_path": rel,
                        "detector_type": "dependency_requirements_txt",
                        "confidence": 0.9,
                        "evidence": {"reason": "requirements", "package": "transformers"},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )

            if "anthropic" in pkgs:
                anthropic = True
                findings.append(
                    {
                        "detected_ai_usage": "anthropic",
                        "file_path": rel,
                        "detector_type": "dependency_requirements_txt",
                        "confidence": 0.9,
                        "evidence": {"reason": "requirements", "package": "anthropic"},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )

        # --- package.json
        if path.name == "package.json":
            deps = _scan_package_json(path)
            for dep in _EXT_AI_DEPS:
                if dep in deps:
                    external_dependencies.add(dep)

            if "openai" in deps:
                openai = True
                findings.append(
                    {
                        "detected_ai_usage": "openai",
                        "file_path": rel,
                        "detector_type": "dependency_package_json",
                        "confidence": 0.9,
                        "evidence": {"reason": "package_json", "package": "openai"},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )

            if "transformers" in deps:
                transformers = True
                findings.append(
                    {
                        "detected_ai_usage": "transformers",
                        "file_path": rel,
                        "detector_type": "dependency_package_json",
                        "confidence": 0.9,
                        "evidence": {"reason": "package_json", "package": "transformers"},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )

            if "anthropic" in deps:
                anthropic = True
                findings.append(
                    {
                        "detected_ai_usage": "anthropic",
                        "file_path": rel,
                        "detector_type": "dependency_package_json",
                        "confidence": 0.9,
                        "evidence": {"reason": "package_json", "package": "anthropic"},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )

        # --- text scan (code)
        if _is_text_file(path):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            low = text.lower()

            if (
                "OpenAI(" in text
                or ".chat.completions" in text
                or ".responses.create" in text
                or "import openai" in text
                or "from openai" in text
            ):
                openai = True
                findings.append(
                    {
                        "detected_ai_usage": "openai",
                        "file_path": rel,
                        "detector_type": "code_signature",
                        "confidence": 0.75,
                        "evidence": {"reason": "code", "signature": "openai_sdk"},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )

            if (
                "import anthropic" in low
                or "from anthropic" in low
                or "anthropic(" in low
                or "client.messages.create" in low
            ):
                anthropic = True
                external_dependencies.add("anthropic")
                findings.append(
                    {
                        "detected_ai_usage": "anthropic",
                        "file_path": rel,
                        "detector_type": "code_signature",
                        "confidence": 0.75,
                        "evidence": {"reason": "code", "signature": "anthropic_sdk"},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )

            if (
                "from transformers" in text
                or "import transformers" in text
                or "pipeline(" in text
                or "AutoModel" in text
                or "AutoTokenizer" in text
            ):
                transformers = True
                findings.append(
                    {
                        "detected_ai_usage": "transformers",
                        "file_path": rel,
                        "detector_type": "code_signature",
                        "confidence": 0.75,
                        "evidence": {"reason": "code", "signature": "transformers"},
                        "change_summary": _git_change_summary(root, rel) if include_history else None,
                    }
                )

            if not user_facing:
                for sig in _USER_FACING_SIGS:
                    if sig in low:
                        user_facing = True
                        break

            if not embeddings:
                for sig in _EMBEDDING_SIGS:
                    if sig in low:
                        embeddings = True
                        break

            if not classifier:
                for sig in _CLASSIFIER_SIGS:
                    if sig in low:
                        classifier = True
                        break

            # If we didn't catch deps from manifests, infer from imports.
            for dep in _EXT_AI_DEPS:
                if f"import {dep.replace('-', '_')}" in low or f"from {dep.replace('-', '_')}" in low:
                    external_dependencies.add(dep)

    llm_used = bool(openai or anthropic)
    model_types: set[str] = set()
    if llm_used:
        model_types.add("llm")
    if classifier or transformers:
        # "transformers" can be LLM or classifier; we keep it conservative and include "classifier" only on classifier sigs.
        if classifier:
            model_types.add("classifier")
    if embeddings:
        model_types.add("embedding")

    ai_detected = bool(llm_used or transformers or model_artifacts or embeddings or classifier)

    return {
        "schema_version": "aigov.discovery_scan.v2",
        "root": str(root),
        "root_relative": os.getcwd() if os.getcwd() else None,
        "openai": openai,
        "transformers": transformers,
        "model_artifacts": model_artifacts,
        # Discovery v2+ context signals (append-only; deterministic)
        "ai_detected": ai_detected,
        "llm_used": llm_used,
        "model_types": sorted(model_types),
        "user_facing": user_facing,
        "pii_possible": pii_possible,
        "external_dependencies": sorted(external_dependencies),
        "findings": findings,
    }
