"""The monthly close: load a month's landing files, build the warehouse, run the checks, write the pack, log the result.

    python -m src.close --month 2026-09

A failed step marks the close failed, writes a failed row to raw.close_log and exits non-zero. The log is
append-only: closing a month again adds a row. The raw tables are delete-and-insert by month, so a re-run never
doubles anything.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date

import duckdb

from src.audit import audit_workbook
from src.config import Config, month_label, parse_month
from src.dbt_runner import run_dbt
from src.loader import LoaderError, load_budget, load_month
from src.pack import build_pack
from src.verify import verify
from src.warehouse import append_close_log, connect, init_raw


@dataclass(frozen=True)
class CloseResult:
    month: date
    status: str  # "closed" or "failed"
    gl_rows: int
    platform_rows: int
    ap_line_rows: int
    budget_rows: int
    checks_passed: int
    checks_total: int
    failures: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.status == "closed"


def _log(config: Config, month: date, counts: tuple[int, int, int, int], passed: int, total: int, failures) -> CloseResult:
    status = "failed" if failures else "closed"
    con = connect(config.warehouse_path)
    try:
        init_raw(con)
        append_close_log(con, {"month": month, "gl_rows": counts[0], "platform_rows": counts[1],
                               "ap_line_rows": counts[2], "budget_rows": counts[3], "checks_passed": passed,
                               "checks_total": total, "status": status, "detail": "; ".join(failures)[:2000]})
    finally:
        con.close()
    return CloseResult(month, status, *counts, passed, total, tuple(failures))


def _load(config: Config, month: date) -> tuple[int, int, int, int]:
    con = connect(config.warehouse_path)
    try:
        init_raw(con)
        loaded = load_month(con, config.landing_dir, month)
        if not config.budget_path.exists():
            raise LoaderError(f"missing budget file {config.budget_path}")
        budget_rows = load_budget(con, config.budget_path)
        return loaded.gl_entries, loaded.platform_bills, loaded.ap_bill_lines, budget_rows
    finally:
        con.close()  # dbt needs the file to itself


def close_month(config: Config, month: date, runner=run_dbt) -> CloseResult:
    """Close one month. runner(db_path, dbt_dir) -> DbtResult runs the SQL layer; tests pass a fake."""
    try:
        counts = _load(config, month)
    except Exception as exc:  # any load problem fails the close; the reason goes in the log
        return _log(config, month, (0, 0, 0, 0), 0, 3, [f"load: {exc}"])

    dbt = runner(config.warehouse_path, config.dbt_dir)
    failures = [f"dbt: {f}" for f in dbt.failures]
    passed = 1 + dbt.tests_passed
    total = 3 + dbt.tests_total
    if dbt.ok:
        # A crash inside a check is a failed check, not an unlogged traceback: the close log shows every attempt.
        try:
            check = verify(config.landing_dir, config.warehouse_path, month)
            failures += [f"verify: {e}" for e in check.errors]
            passed += check.ok
        except Exception as exc:
            failures.append(f"verify: crashed: {exc}")
        try:
            con = duckdb.connect(str(config.warehouse_path), read_only=True)
            try:
                pack_path = config.output_dir / f"pack_{month_label(month)}.xlsx"
                expected = build_pack(con, pack_path, month)
            finally:
                con.close()
            audit = audit_workbook(pack_path, expected)
            failures += [f"audit: {e}" for e in audit.errors]
            passed += audit.ok
        except Exception as exc:
            failures.append(f"audit: pack crashed: {exc}")
    return _log(config, month, counts, passed, total, failures)


def main(argv=None, config: Config | None = None, runner=run_dbt) -> int:
    parser = argparse.ArgumentParser(description="Close one month of the Larkspur warehouse.")
    parser.add_argument("--month", required=True, help="month to close, as YYYY-MM")
    args = parser.parse_args(argv)
    result = close_month(config or Config(), parse_month(args.month), runner=runner)
    print(f"{month_label(result.month)} {result.status}: gl {result.gl_rows}, platform bills {result.platform_rows}, "
          f"bill lines {result.ap_line_rows}, checks {result.checks_passed}/{result.checks_total}")
    for failure in result.failures:
        print(f"  {failure}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
