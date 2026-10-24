import shutil
from datetime import date

import duckdb
import openpyxl
import pytest

from src.close import close_month
from src.close import main as close_main
from src.config import Config
from src.dbt_runner import DbtResult
from src.generate_data import generate
from src.warehouse import connect


def fake_dbt(ok=True, passed=10, failed=0, failures=()):
    def runner(db_path, dbt_dir):
        return DbtResult(ok, passed + failed, passed, failed, tuple(failures))
    return runner


@pytest.fixture
def cfg(tmp_path):
    c = Config(root=tmp_path)
    generate(c, [date(2024, 1, 1), date(2024, 2, 1)])
    return c


def log_rows(cfg):
    con = duckdb.connect(str(cfg.warehouse_path), read_only=True)
    try:
        return con.execute("select strftime(month, '%Y-%m'), status, gl_rows, platform_rows, ap_line_rows, budget_rows, "
                           "checks_passed, checks_total, detail from raw.close_log order by run_at").fetchall()
    finally:
        con.close()


def test_failed_dbt_marks_the_close_failed_and_is_logged(cfg):
    result = close_month(cfg, date(2024, 1, 1), runner=fake_dbt(ok=False, passed=8, failed=2,
                                                                failures=["test.larkspur.assert_x: fail"]))
    assert not result.ok and result.status == "failed"
    row = log_rows(cfg)[0]
    assert row[1] == "failed" and row[2] > 0 and row[3] > 0 and row[5] > 0
    assert "assert_x" in row[8]
    assert row[6] < row[7]  # not every check passed


def test_loader_errors_fail_the_close_without_running_dbt(cfg):
    calls = []

    def runner(db_path, dbt_dir):
        calls.append(1)
        return DbtResult(True, 0, 0, 0, ())

    wb = openpyxl.load_workbook(cfg.landing_dir / "2024-01" / "gl.xlsx")
    wb.active.append(["a stray footer"])
    wb.save(cfg.landing_dir / "2024-01" / "gl.xlsx")
    result = close_month(cfg, date(2024, 1, 1), runner=runner)
    assert not result.ok and calls == []
    assert log_rows(cfg)[0][1] == "failed" and "unrecognised" in log_rows(cfg)[0][8]


def test_a_crash_in_verify_or_the_pack_fails_the_close_and_is_logged(cfg):
    # the fake dbt reports success but builds no marts, so the independent check cannot read them
    result = close_month(cfg, date(2024, 1, 1), runner=fake_dbt(ok=True))
    assert not result.ok and result.status == "failed"
    rows = log_rows(cfg)
    assert len(rows) == 1 and rows[0][1] == "failed" and "verify" in rows[0][8]
    assert close_main(["--month", "2024-01"], config=cfg, runner=fake_dbt(ok=True)) == 1


def test_a_missing_month_fails_the_close(cfg):
    shutil.rmtree(cfg.landing_dir / "2024-02")
    assert not close_month(cfg, date(2024, 2, 1), runner=fake_dbt()).ok


def test_main_exits_non_zero_on_failure(cfg):
    shutil.rmtree(cfg.landing_dir / "2024-02")
    assert close_main(["--month", "2024-02"], config=cfg, runner=fake_dbt()) == 1


def test_close_log_is_append_only_and_reload_does_not_double_raw_rows(cfg):
    close_month(cfg, date(2024, 1, 1), runner=fake_dbt(ok=False, failures=["x"]))
    close_month(cfg, date(2024, 1, 1), runner=fake_dbt(ok=False, failures=["x"]))
    rows = log_rows(cfg)
    assert len(rows) == 2 and rows[0][2] == rows[1][2]
    con = connect(cfg.warehouse_path)
    assert con.execute("select count(*) from raw.gl_entries").fetchone()[0] == rows[0][2]
    con.close()


# ---- end to end with the real dbt: slow, so each scenario runs once

@pytest.fixture(scope="module")
def e2e_year_end(tmp_path_factory):
    cfg = Config(root=tmp_path_factory.mktemp("e2e_year_end"))
    months = [date(2024, 11, 1), date(2024, 12, 1)]
    generate(cfg, months)
    from src.dbt_runner import run_dbt
    results = [close_month(cfg, m, runner=run_dbt) for m in months]
    return cfg, results


def query(cfg, sql, params=None):
    con = duckdb.connect(str(cfg.warehouse_path), read_only=True)
    try:
        return con.execute(sql, params or []).fetchall()
    finally:
        con.close()


def test_real_close_passes_every_check_and_logs_each_month(e2e_year_end):
    cfg, results = e2e_year_end
    assert all(r.ok for r in results), [r.failures for r in results]
    rows = log_rows(cfg)
    assert [r[:2] for r in rows] == [("2024-11", "closed"), ("2024-12", "closed")]
    assert all(r[6] == r[7] > 100 for r in rows)  # dozens of dbt tests plus load, verify and audit
    for month in ("2024-11", "2024-12"):
        assert (cfg.output_dir / f"pack_{month}.xlsx").exists()


def test_year_end_count_adjustment_is_in_the_report_but_not_the_run_rate(e2e_year_end):
    cfg, _ = e2e_year_end
    in_report = query(cfg, "select sum(excluded_amount) from marts.rpt_monthly_pl where month_start = date '2024-12-01'")[0][0]
    assert float(in_report) == pytest.approx(64300.00)
    line = query(cfg, "select monthly_run_rate, monthly_run_rate_incl_excluded, excluded_total from marts.rpt_run_rate "
                      "where reporting_line_key = 'inventory_shrinkage'")[0]
    assert float(line[2]) == pytest.approx(64300.00)
    assert float(line[1]) - float(line[0]) == pytest.approx(64300.00 / 2)  # two closed months in the window


def test_raw_rows_equal_mart_rows(e2e_year_end):
    cfg, _ = e2e_year_end
    raw, fact = query(cfg, "select (select count(*) from raw.gl_entries), (select count(*) from marts.fct_gl_entries)")[0]
    assert raw == fact > 500


@pytest.fixture(scope="module")
def e2e_partial(tmp_path_factory):
    cfg = Config(root=tmp_path_factory.mktemp("e2e_partial"))
    months = [date(2026, 9, 1), date(2026, 10, 1)]
    generate(cfg, months)
    from src.dbt_runner import run_dbt
    return cfg, [close_month(cfg, m, runner=run_dbt) for m in months]


def test_partial_october_closes_but_stays_out_of_the_run_rate(e2e_partial):
    cfg, results = e2e_partial
    assert all(r.ok for r in results), [r.failures for r in results]
    window = query(cfg, "select distinct window_start, window_end, months_in_window from marts.rpt_run_rate")
    assert window == [(date(2026, 9, 1), date(2026, 9, 1), 1)]
    partial = query(cfg, "select is_closed from intermediate.int_month_status where month_start = date '2026-10-01'")
    assert partial == [(False,)]
