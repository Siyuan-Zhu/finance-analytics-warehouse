"""Independent check: re-read a month's raw .xlsx export with a separate minimal reader and compare with the marts.

This module deliberately imports nothing from src: not the parser, the loader or the config. It recomputes two things
that need no classification, the number of posting rows and the net amount (debit minus credit) per account, and
compares them with marts.fct_gl_entries for the same month. A test enforces the no-import rule.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb
import openpyxl

TOLERANCE = 0.01
HEADER = re.compile(r"^(\d{4}) \S")


@dataclass(frozen=True)
class VerifyResult:
    checked: int
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _read_raw(path: Path) -> tuple[int, dict[str, float]]:
    """(posting row count, net debit minus credit per account code) from the report-style export."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    count = 0
    net: dict[str, float] = defaultdict(float)
    code = None
    for cells in wb.worksheets[0].iter_rows(values_only=True):
        first = cells[0]
        if isinstance(first, str):
            m = HEADER.match(first)
            if m and all(c is None for c in cells[1:]):
                code = m.group(1)
            continue
        if isinstance(first, (date, datetime)) and code is not None:
            count += 1
            net[code] += float(cells[4] or 0) - float(cells[5] or 0)
    wb.close()
    return count, dict(net)


def verify(landing_dir, db_path, month: date) -> VerifyResult:
    path = Path(landing_dir) / f"{month.year:04d}-{month.month:02d}" / "gl.xlsx"
    if not path.exists():
        return VerifyResult(0, (f"landing file {path} is missing",))
    raw_count, raw_net = _read_raw(path)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        count = con.execute("select count(*) from marts.fct_gl_entries where month_start = ?", [month]).fetchone()[0]
        wh = {a: float(t) for a, t in con.execute(
            "select account_code, sum(debit - credit) from marts.fct_gl_entries where month_start = ? group by 1",
            [month]).fetchall()}
    finally:
        con.close()
    errors: list[str] = []
    checked = 1
    if count != raw_count:
        errors.append(f"row count: file has {raw_count} postings, warehouse has {count}")
    for account in sorted(set(raw_net) | set(wh)):
        checked += 1
        a, b = raw_net.get(account), wh.get(account)
        if a is None:
            errors.append(f"account {account}: in the warehouse ({b:.2f}) but not in the file")
        elif b is None:
            errors.append(f"account {account}: in the file ({a:.2f}) but not in the warehouse")
        elif abs(a - b) > TOLERANCE:
            errors.append(f"account {account}: file total {a:.2f}, warehouse total {b:.2f}")
    return VerifyResult(checked, tuple(errors))
