"""Load one month's landing files into the raw tables. Delete-and-insert by month, so a re-run never doubles rows.

Everything is parsed before the database is touched: a bad file raises LoaderError and leaves the old rows alone.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.config import month_label
from src.gl_parser import parse_gl

GL_FILE, PLATFORM_FILE, LINES_FILE = "gl.xlsx", "platform_bills.csv", "ap_bill_lines.csv"


class LoaderError(Exception):
    pass


@dataclass(frozen=True)
class LoadCounts:
    gl_entries: int
    platform_bills: int
    ap_bill_lines: int


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise LoaderError(f"missing landing file {path}")
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _date(text: str):
    return date.fromisoformat(text) if text else None


def load_month(con, landing_dir, month: date) -> LoadCounts:
    folder = Path(landing_dir) / month_label(month)
    gl_path = folder / GL_FILE
    if not gl_path.exists():
        raise LoaderError(f"missing landing file {gl_path}")
    parsed = parse_gl(gl_path)
    if parsed.errors:
        raise LoaderError(f"{gl_path}: " + "; ".join(parsed.errors[:5]))
    platform = _read_csv(folder / PLATFORM_FILE)
    lines = _read_csv(folder / LINES_FILE)

    gl_rows = [
        [month, t.row, t.account_code, t.account_name, t.entry_date, t.reference, t.description, t.cost_center,
         t.debit, t.credit]
        for t in parsed.transactions
    ]
    pb_rows = [
        [month, r["bill_id"], r["vendor"], _date(r["bill_date"]), _date(r["due_date"]), _date(r["paid_date"]),
         r["amount"], r["payment_method"], r["gl_code"], r["location"]]
        for r in platform
    ]
    ln_rows = [
        [month, r["doc_id"], int(r["line_no"]), r["vendor"], _date(r["bill_date"]), _date(r["due_date"]),
         _date(r["paid_date"]), r["gl_code"], r["location"], r["amount"]]
        for r in lines
    ]
    con.execute("begin")
    try:
        for table, rows in (("gl_entries", gl_rows), ("platform_bills", pb_rows), ("ap_bill_lines", ln_rows)):
            con.execute(f"delete from raw.{table} where landing_month = ?", [month])
            if rows:
                marks = ", ".join("?" * len(rows[0]))
                con.executemany(f"insert into raw.{table} values ({marks})", rows)
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    return LoadCounts(len(gl_rows), len(pb_rows), len(ln_rows))


def load_budget(con, path) -> int:
    """Replace the whole budget table from the budget file. Returns the row count."""
    rows = [[date.fromisoformat(r["month"]), r["account_code"], r["cost_center"], r["amount"]]
            for r in _read_csv(Path(path))]
    con.execute("begin")
    try:
        con.execute("delete from raw.budget")
        if rows:
            con.executemany("insert into raw.budget values (?, ?, ?, ?)", rows)
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    return len(rows)
