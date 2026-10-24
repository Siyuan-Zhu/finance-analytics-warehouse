"""Run `dbt build` against the warehouse file and read the result. The only module that knows how dbt is called."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PASSED_STATUSES = {"pass"}
BAD_STATUSES = {"fail", "error", "runtime error"}


@dataclass(frozen=True)
class DbtResult:
    ok: bool
    tests_total: int
    tests_passed: int
    tests_failed: int
    failures: tuple[str, ...]


def summarise_run_results(run_results: dict | None, returncode: int, output: str = "") -> DbtResult:
    """Count tests (data tests and unit tests) and collect failures from dbt's run_results.json."""
    if run_results is None:
        return DbtResult(False, 0, 0, 0, (f"dbt did not produce results (exit {returncode}): {output.strip()[-400:]}",))
    total = passed = 0
    failures: list[str] = []
    for r in run_results.get("results", []):
        uid, status = r["unique_id"], r["status"]
        if uid.startswith(("test.", "unit_test.")):
            total += 1
            passed += status in PASSED_STATUSES
        if status in BAD_STATUSES:
            failures.append(f"{uid}: {status} {r.get('message') or ''}".strip())
    skipped = [r["unique_id"] for r in run_results.get("results", []) if r["status"] == "skipped"]
    if skipped:
        failures.append(f"{len(skipped)} nodes skipped after an upstream failure")
    ok = returncode == 0 and not failures
    return DbtResult(ok, total, passed, total - passed, tuple(failures))


def run_dbt(db_path, dbt_dir) -> DbtResult:
    """dbt build (seeds, models and tests) on the DuckDB file at db_path."""
    dbt_dir = Path(dbt_dir)
    env = {**os.environ, "LARKSPUR_DB": str(Path(db_path).resolve()), "DBT_SEND_ANONYMOUS_USAGE_STATS": "false"}
    results_file = dbt_dir / "target" / "run_results.json"
    results_file.unlink(missing_ok=True)
    proc = subprocess.run(
        [sys.executable, "-c", "from dbt.cli.main import cli; cli()", "build", "--project-dir", str(dbt_dir),
         "--profiles-dir", str(dbt_dir), "--no-use-colors"],
        capture_output=True, text=True, env=env, check=False,
    )
    run_results = json.loads(results_file.read_text()) if results_file.exists() else None
    return summarise_run_results(run_results, proc.returncode, proc.stdout + proc.stderr)
