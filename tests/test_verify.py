import ast
from datetime import date
from pathlib import Path

import duckdb
import pytest

from src.verify import verify
from tests.conftest import txn, write_gl


@pytest.fixture
def world(tmp_path):
    """A landing folder for 2025-01 and a warehouse whose fct_gl_entries agrees with it."""
    landing = tmp_path / "landing"
    (landing / "2025-01").mkdir(parents=True)
    write_gl(
        landing / "2025-01" / "gl.xlsx",
        [
            ("4045", "Apparel Sales", [txn(1, "S1", "sales", "ST01", credit=500.0), txn(1, "S2", "sales", "ST01", credit=300.0)]),
            ("6105", "Store Wages", [txn(1, "P1", "pay", "ST01", debit=120.0)]),
            ("1010", "Operating Bank Account", [txn(1, "S1", "receipt", "ST01", debit=500.0)]),
        ],
    )
    db = tmp_path / "w.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create schema marts")
    con.execute("create table marts.fct_gl_entries (entry_key varchar, entry_date date, month_start date, "
                "account_code varchar, debit decimal(14,2), credit decimal(14,2), amount decimal(14,2))")
    rows = [("a", date(2025, 1, 10), date(2025, 1, 1), "4045", 0, 500),
            ("b", date(2025, 1, 10), date(2025, 1, 1), "4045", 0, 300),
            ("c", date(2025, 1, 10), date(2025, 1, 1), "6105", 120, 0),
            ("d", date(2025, 1, 10), date(2025, 1, 1), "1010", 500, 0),
            ("other month", date(2025, 2, 10), date(2025, 2, 1), "6105", 999, 0)]
    for k, d, ms, a, dr, cr in rows:
        con.execute("insert into marts.fct_gl_entries values (?, ?, ?, ?, ?, ?, ?)", [k, d, ms, a, dr, cr, dr - cr])
    return {"landing": landing, "db": db, "con": con}


def run(world):
    world["con"].close()
    return verify(world["landing"], world["db"], date(2025, 1, 1))


def test_consistent_warehouse_passes(world):
    result = run(world)
    assert result.ok, result.errors
    assert result.checked >= 4  # row count plus one total per account


def test_a_changed_total_is_reported_by_account(world):
    world["con"].execute("update marts.fct_gl_entries set credit = 450, amount = -450 where entry_key = 'a'")
    result = run(world)
    assert not result.ok
    assert any("4045" in e for e in result.errors)


def test_a_missing_row_is_reported(world):
    world["con"].execute("delete from marts.fct_gl_entries where entry_key = 'd'")
    result = run(world)
    assert not result.ok
    assert any("row count" in e for e in result.errors)
    assert any("1010" in e for e in result.errors)


def test_an_extra_account_in_the_warehouse_is_reported(world):
    world["con"].execute("insert into marts.fct_gl_entries values ('x', date '2025-01-12', date '2025-01-01', '6999', 5, 0, 5)")
    result = run(world)
    assert any("6999" in e for e in result.errors)


def test_a_missing_landing_file_is_an_error_not_a_pass(world):
    (world["landing"] / "2025-01" / "gl.xlsx").unlink()
    result = run(world)
    assert not result.ok


def test_verify_imports_nothing_from_the_code_it_checks():
    tree = ast.parse(Path("src/verify.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert "src" not in imported
    assert imported <= {"__future__", "re", "dataclasses", "datetime", "pathlib", "openpyxl", "duckdb", "collections", "calendar"}
