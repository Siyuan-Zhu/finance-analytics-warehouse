"""Shared helpers: hand-built raw GL exports in the same multi-header layout the parser reads."""
from __future__ import annotations

from datetime import date

import openpyxl

BANNER = ("Date", "Reference", "Description", "Cost Center", "Debit", "Credit")


def write_gl(path, accounts, title="Test Co", period="For the period 1 January 2025 to 31 December 2025"):
    """accounts: list of (code, name, [(date, ref, description, cost_center, debit, credit), ...])."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([title])
    ws.append(["Account Transactions"])
    ws.append([period])
    ws.append([])
    for code, name, rows in accounts:
        ws.append([f"{code} {name}"])
        ws.append(list(BANNER))
        for row in rows:
            ws.append(list(row))
        debit = sum(r[4] or 0 for r in rows)
        credit = sum(r[5] or 0 for r in rows)
        ws.append([f"Total {code} {name}", None, None, None, debit, credit])
        ws.append([])
    wb.save(path)
    return path


def txn(month, ref, desc, cc, debit=None, credit=None, year=2025, day=10):
    return (date(year, month, day), ref, desc, cc, debit, credit)
