"""Paths, the seed and the month range. Business tunables (tolerances, windows) live in dbt vars and seeds."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_month(text: str) -> date:
    """'2026-09' -> date(2026, 9, 1)."""
    year, month = text.split("-")
    return date(int(year), int(month), 1)


def month_label(month: date) -> str:
    return f"{month.year:04d}-{month.month:02d}"


def months_between(first: date, last: date) -> list[date]:
    """Every first-of-month from first to last, both included."""
    out, current = [], date(first.year, first.month, 1)
    while current <= last:
        out.append(current)
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
    return out


@dataclass(frozen=True)
class Config:
    root: Path = REPO_ROOT
    seed: int = 20260101
    first_month: date = date(2024, 1, 1)
    last_month: date = date(2026, 10, 1)  # October 2026 holds only its first few days
    data_cutoff: date = date(2026, 10, 4)  # last posting day in the data; payments after it are unknown

    @property
    def landing_dir(self) -> Path:
        return self.root / "data" / "landing"

    @property
    def budget_path(self) -> Path:
        return self.landing_dir / "budget.csv"

    @property
    def warehouse_path(self) -> Path:
        return self.root / "warehouse" / "larkspur.duckdb"

    @property
    def output_dir(self) -> Path:
        return self.root / "output"

    @property
    def dbt_dir(self) -> Path:
        return REPO_ROOT / "dbt"

    @property
    def months(self) -> list[date]:
        return months_between(self.first_month, self.last_month)
