#!/usr/bin/env python3
"""
Paper failure-injection harness entrypoint (repo root).

Delegates to ``aigov_py.experiments.controlled_failure_injection`` so the
implementation stays importable from the ``python/`` package (tests, CLI).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PY_ROOT = _REPO_ROOT / "python"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from aigov_py.experiments.controlled_failure_injection import write_outputs  # noqa: E402


def main() -> None:
    out_dir = _REPO_ROOT / "experiments" / "output"
    paths = write_outputs(out_dir)
    print("Wrote:")
    for _k, v in sorted(paths.items()):
        print(f"  - {v}")


if __name__ == "__main__":
    main()
