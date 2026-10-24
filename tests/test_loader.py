import csv
from datetime import date

import duckdb
import openpyxl
import pytest

from src.config import month_label, months_between, parse_month
from src.loader import LoaderError, load_budget, load_month
from src.warehouse import append_close_log, init_raw
from tests.conftest import txn, write_gl

PLATFORM_COLS = ["bill_id", "vendor", "bill_date", "due_date", "paid_date", "amount", "payment_method", "gl_code", "location"]
LINE_COLS = ["doc_id", "line_no", "vendor", "bill_date", "due_date", "paid_date", "gl_code", "location", "amount"]


def write_csv(path, cols, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)


def make_month(root, label, n_gl=2, n_pb=1, n_lines=2, year=2024, month=1):
    d = root / label
    d.mkdir(parents=True)
    rows = [txn(month, f"S-{i}", "sales", "ST01", credit=100.0 + i, year=year, day=5 + i) for i in range(n_gl)]
    write_gl(d / "gl.xlsx", [("4045", "Apparel Sales", rows)])
    pb = [[f"PB-{label}-{i}", "Cedar Ridge Freight Inc", f"{label}-10", f"{label}-28", "", "500.00", "ach", "", "ST01"]
          for i in range(n_pb)]
    write_csv(d / "platform_bills.csv", PLATFORM_COLS, pb)
    ln = [[f"BILL-{label}-1", i + 1, "Cedar Ridge Freight Inc", f"{label}-10", f"{label}-28", f"{label}-25", "5205", "ST01", "250.00"]
          for i in range(n_lines)]
    write_csv(d / "ap_bill_lines.csv", LINE_COLS, ln)
    return d


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    init_raw(c)
    return c


def test_month_helpers():
    assert parse_month("2026-09") == date(2026, 9, 1)
    assert month_label(date(2026, 9, 1)) == "2026-09"
    assert months_between(date(2024, 11, 1), date(2025, 2, 1)) == [
        date(2024, 11, 1), date(2024, 12, 1), date(2025, 1, 1), date(2025, 2, 1)]
    with pytest.raises(ValueError):
        parse_month("2026-13")


def test_load_month_counts_rows_per_source(tmp_path, con):
    make_month(tmp_path, "2024-01", n_gl=3, n_pb=2, n_lines=4)
    counts = load_month(con, tmp_path, date(2024, 1, 1))
    assert (counts.gl_entries, counts.platform_bills, counts.ap_bill_lines) == (3, 2, 4)
    assert con.execute("select count(*) from raw.gl_entries").fetchone()[0] == 3
    row = con.execute("select account_code, cost_center, credit, entry_date, landing_month from raw.gl_entries "
                      "order by source_row limit 1").fetchone()
    assert row[0] == "4045" and row[1] == "ST01" and float(row[2]) == 100.0
    assert row[3] == date(2024, 1, 5) and row[4] == date(2024, 1, 1)


def test_reloading_a_month_does_not_double_rows(tmp_path, con):
    make_month(tmp_path, "2024-01")
    first = load_month(con, tmp_path, date(2024, 1, 1))
    second = load_month(con, tmp_path, date(2024, 1, 1))
    assert first == second
    for table, expected in (("gl_entries", 2), ("platform_bills", 1), ("ap_bill_lines", 2)):
        assert con.execute(f"select count(*) from raw.{table}").fetchone()[0] == expected


def test_reload_replaces_that_month_only(tmp_path, con):
    make_month(tmp_path, "2024-01", n_gl=2)
    make_month(tmp_path, "2024-02", n_gl=3, month=2)
    load_month(con, tmp_path, date(2024, 1, 1))
    load_month(con, tmp_path, date(2024, 2, 1))
    make_month_files = tmp_path / "2024-01"
    for f in make_month_files.iterdir():
        f.unlink()
    make_month_files.rmdir()
    make_month(tmp_path, "2024-01", n_gl=5)
    counts = load_month(con, tmp_path, date(2024, 1, 1))
    assert counts.gl_entries == 5
    per_month = dict(con.execute("select strftime(landing_month, '%Y-%m'), count(*) from raw.gl_entries group by 1").fetchall())
    assert per_month == {"2024-01": 5, "2024-02": 3}


def test_unparseable_gl_raises_and_keeps_old_rows(tmp_path, con):
    make_month(tmp_path, "2024-01", n_gl=2)
    load_month(con, tmp_path, date(2024, 1, 1))
    wb = openpyxl.load_workbook(tmp_path / "2024-01" / "gl.xlsx")
    wb.active.append(["a stray footer"])
    wb.save(tmp_path / "2024-01" / "gl.xlsx")
    with pytest.raises(LoaderError, match="unrecognised"):
        load_month(con, tmp_path, date(2024, 1, 1))
    assert con.execute("select count(*) from raw.gl_entries").fetchone()[0] == 2


def test_missing_file_raises(tmp_path, con):
    make_month(tmp_path, "2024-01")
    (tmp_path / "2024-01" / "platform_bills.csv").unlink()
    with pytest.raises(LoaderError, match="platform_bills.csv"):
        load_month(con, tmp_path, date(2024, 1, 1))


def test_blank_paid_date_loads_as_null(tmp_path, con):
    make_month(tmp_path, "2024-01")
    load_month(con, tmp_path, date(2024, 1, 1))
    assert con.execute("select paid_date from raw.platform_bills").fetchone()[0] is None
    assert con.execute("select paid_date from raw.ap_bill_lines limit 1").fetchone()[0] == date(2024, 1, 25)


def test_budget_is_replaced_not_appended(tmp_path, con):
    path = tmp_path / "budget.csv"
    write_csv(path, ["month", "account_code", "cost_center", "amount"],
              [["2025-01-01", "4045", "ST01", "1000.00"], ["2025-02-01", "4045", "ST01", "1100.00"]])
    assert load_budget(con, path) == 2
    assert load_budget(con, path) == 2
    assert con.execute("select count(*), sum(amount) from raw.budget").fetchone() == (2, 2100)


def test_close_log_appends(con):
    append_close_log(con, {"month": date(2024, 1, 1), "gl_rows": 3, "platform_rows": 1, "ap_line_rows": 2,
                           "budget_rows": 0, "checks_passed": 10, "checks_total": 10, "status": "closed",
                           "detail": ""})
    append_close_log(con, {"month": date(2024, 1, 1), "gl_rows": 3, "platform_rows": 1, "ap_line_rows": 2,
                           "budget_rows": 0, "checks_passed": 9, "checks_total": 10, "status": "failed",
                           "detail": "verify: x"})
    rows = con.execute("select status, checks_passed, run_at is not null from raw.close_log order by run_at").fetchall()
    assert rows == [("closed", 10, True), ("failed", 9, True)]
