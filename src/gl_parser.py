"""Flatten the multi-header GL "account transactions" export into immutable transaction records.

The parser knows the layout only. It does not know which accounts are profit and loss: that is a database rule.

Layout read: title rows, then for each account a single-cell header row ("6105 Store Wages"), a repeated
column banner, transaction rows, a subtotal row ("Total 6105 Store Wages") and blank spacer rows.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import openpyxl

HEADER_RE = re.compile(r"^(\d{4}) (.+)$")
SUBTOTAL_RE = re.compile(r"^Total (\d{4}) (.+)$")
TOLERANCE = 0.01


@dataclass(frozen=True)
class GLTransaction:
    source: str  # file name
    row: int  # 1-based worksheet row, unique within a source
    account_code: str
    account_name: str
    entry_date: date
    reference: str
    description: str
    cost_center: str
    debit: float
    credit: float

    @property
    def amount(self) -> float:
        """Debit minus credit."""
        return round(self.debit - self.credit, 2)

    @property
    def key(self) -> str:
        return f"{self.source}:{self.row}"


@dataclass(frozen=True)
class ParsedGL:
    transactions: tuple[GLTransaction, ...]
    dispositions: dict[str, int]
    errors: tuple[str, ...]


def _num(value) -> float:
    return round(float(value), 2) if value not in (None, "") else 0.0


def _is_blank(cells) -> bool:
    return all(c is None or (isinstance(c, str) and not c.strip()) for c in cells)


def parse_gl(path) -> ParsedGL:
    path = Path(path)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    dispositions: Counter[str] = Counter()
    errors: list[str] = []
    txns: list[GLTransaction] = []
    current: tuple[str, str] | None = None
    sums = {"debit": 0.0, "credit": 0.0}

    for row_no, cells in enumerate(ws.iter_rows(values_only=True), start=1):
        first = cells[0]
        if _is_blank(cells):
            dispositions["blank"] += 1
        elif isinstance(first, (date, datetime)):
            if current is None:
                dispositions["unrecognised"] += 1
                errors.append(f"{path.name} row {row_no}: transaction before any account header")
                continue
            code, name = current
            d = first.date() if isinstance(first, datetime) else first
            debit, credit = _num(cells[4]), _num(cells[5])
            sums["debit"] += debit
            sums["credit"] += credit
            txns.append(
                GLTransaction(path.name, row_no, code, name, d, str(cells[1] or ""), str(cells[2] or ""),
                              str(cells[3] or ""), debit, credit)
            )
            dispositions["transaction"] += 1
        elif isinstance(first, str) and first == "Date":
            dispositions["banner"] += 1
        elif isinstance(first, str) and (m := SUBTOTAL_RE.match(first)):
            dispositions["subtotal"] += 1
            if current != (m.group(1), m.group(2)):
                errors.append(f"{path.name} row {row_no}: subtotal '{first}' does not match open account {current}")
            else:
                for label, idx in (("debit", 4), ("credit", 5)):
                    if abs(_num(cells[idx]) - sums[label]) > TOLERANCE:
                        errors.append(
                            f"{path.name} row {row_no}: subtotal {label} for {m.group(1)} is {_num(cells[idx])} "
                            f"but rows sum to {round(sums[label], 2)}"
                        )
            current = None
        elif isinstance(first, str) and (m := HEADER_RE.match(first)) and _is_blank(cells[1:]):
            dispositions["account_header"] += 1
            if current is not None:
                errors.append(f"{path.name} row {row_no}: account {current[0]} has no subtotal row before the next header")
            current = (m.group(1), m.group(2))
            sums = {"debit": 0.0, "credit": 0.0}
        elif current is None and not txns and isinstance(first, str):
            dispositions["title"] += 1
        else:
            dispositions["unrecognised"] += 1
            errors.append(f"{path.name} row {row_no}: unrecognised row {first!r}")
    wb.close()
    if current is not None:
        errors.append(f"{path.name}: account {current[0]} has no subtotal row at the end of the file")
    return ParsedGL(tuple(txns), dict(dispositions), tuple(errors))
