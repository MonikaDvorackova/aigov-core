from __future__ import annotations

import os
import subprocess
import uuid


def _run(cmd: list[str], env: dict[str, str]) -> None:
    p = subprocess.run(cmd, env=env, check=False)
    if p.returncode != 0:
        raise SystemExit(f"Command failed: {' '.join(cmd)}")


def main() -> None:
    run_id = os.environ.get("RUN_ID", "").strip() or str(uuid.uuid4())

    env = os.environ.copy()
    env["RUN_ID"] = run_id

    _run(["python", "-m", "aigov_py.demo"], env=env)
    _run(["make", "bundle", f"RUN_ID={run_id}"], env=env)
    _run(["make", "verify", f"RUN_ID={run_id}"], env=env)
    _run(["make", "db_ingest", f"RUN_ID={run_id}"], env=env)

    print(f"OK: e2e completed RUN_ID={run_id}")
    print(f"Dashboard: /runs/{run_id}")


if __name__ == "__main__":
    main()
