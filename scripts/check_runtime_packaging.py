#!/usr/bin/env python3
"""Validate runtime packaging artifacts (Docker, Compose, K8s, Helm, ops docs)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    ROOT / "Dockerfile",
    ROOT / ".dockerignore",
    ROOT / "deployments/docker-compose/docker-compose.yml",
    ROOT / "deployments/kubernetes/namespace.yaml",
    ROOT / "deployments/kubernetes/deployment.yaml",
    ROOT / "deployments/kubernetes/service.yaml",
    ROOT / "deployments/kubernetes/pvc.yaml",
    ROOT / "deployments/kubernetes/configmap.yaml",
    ROOT / "deployments/kubernetes/secret.example.yaml",
    ROOT / "deployments/helm/aigov-core/Chart.yaml",
    ROOT / "deployments/helm/aigov-core/values.yaml",
    ROOT / "deployments/helm/aigov-core/templates/deployment.yaml",
    ROOT / "deployments/helm/aigov-core/templates/service.yaml",
    ROOT / "deployments/helm/aigov-core/templates/pvc.yaml",
    ROOT / "deployments/helm/aigov-core/templates/configmap.yaml",
    ROOT / "docs/runtime-operations.md",
    ROOT / "docs/backup-and-recovery.md",
    ROOT / "docs/threat-model.md",
    ROOT / "docs/reports/runtime-packaging-and-operations.md",
)

SCAN_DIRS = (
    ROOT / "deployments",
    ROOT / "docs/runtime-operations.md",
    ROOT / "docs/backup-and-recovery.md",
    ROOT / "docs/threat-model.md",
    ROOT / "docs/reports/runtime-packaging-and-operations.md",
    ROOT / "Dockerfile",
    ROOT / ".dockerignore",
)

FORBIDDEN_TERMS = (
    "stripe",
    "billing",
    "pricing",
    "onboarding",
    "kovali",
    "hosted saas",
    "platform entitlements",
    "dashboard acl",
    "react dashboard",
    "auth portal",
)

DOCKERFILE_REQUIRED = (
    ("ENTRYPOINT", re.compile(r'ENTRYPOINT\s+\["/app/aigov_audit"\]')),
    ("EXPOSE 8088", re.compile(r"EXPOSE\s+8088")),
    ("USER", re.compile(r"^USER\s+govai\s*$", re.MULTILINE)),
    ("GOVAI_LEDGER_DIR", re.compile(r"GOVAI_LEDGER_DIR")),
    ("DATABASE_URL", re.compile(r"DATABASE_URL|#.*DATABASE")),
    ("AIGOV_BIND", re.compile(r"AIGOV_BIND")),
)


def _iter_scan_files() -> list[Path]:
    out: list[Path] = []
    for item in SCAN_DIRS:
        if item.is_file():
            out.append(item)
        elif item.is_dir():
            for p in sorted(item.rglob("*")):
                if p.is_file() and p.suffix in {
                    ".yml",
                    ".yaml",
                    ".md",
                    ".tpl",
                    ".txt",
                    "",
                } or p.name in ("Dockerfile", ".dockerignore", "NOTES.txt"):
                    if p.suffix in {".pyc"} or "node_modules" in p.parts:
                        continue
                    out.append(p)
    return out


def main() -> int:
    errors: list[str] = []

    for path in REQUIRED_PATHS:
        if not path.exists():
            errors.append(f"missing required path: {path.relative_to(ROOT)}")

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    for label, pattern in DOCKERFILE_REQUIRED:
        if not pattern.search(dockerfile):
            errors.append(f"Dockerfile missing requirement: {label}")

    for path in _iter_scan_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace").lower()
        except OSError as exc:
            errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
            continue
        for term in FORBIDDEN_TERMS:
            if term in text:
                errors.append(
                    f"forbidden term {term!r} in {path.relative_to(ROOT)}"
                )

    if errors:
        print("runtime-packaging-check failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("runtime-packaging-check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
