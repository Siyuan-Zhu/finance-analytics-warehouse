"""The DuckDB file: connecting, the DDL of the raw tables (the contract with dbt) and the close log."""
from __future__ import annotations

from pathlib import Path

import duckdb

RAW_DDL = (
    "create schema if not exists raw",
    """create table if not exists raw.gl_entries (
        landing_month date not null, source_row integer not null, account_code varchar not null,
        account_name varchar, entry_date date not null, reference varchar, description varchar,
        cost_center varchar, debit decimal(14, 2) not null, credit decimal(14, 2) not null)""",
    """create table if not exists raw.platform_bills (
        landing_month date not null, bill_id varchar not null, vendor varchar, bill_date date not null,
        due_date date, paid_date date, amount decimal(14, 2) not null, payment_method varchar,
        gl_code varchar, location varchar)""",
    """create table if not exists raw.ap_bill_lines (
        landing_month date not null, doc_id varchar not null, line_no integer not null, vendor varchar,
        bill_date date not null, due_date date, paid_date date, gl_code varchar, location varchar,
        amount decimal(14, 2) not null)""",
    """create table if not exists raw.budget (
        month_start date not null, account_code varchar not null, cost_center varchar not null,
        amount decimal(14, 2) not null)""",
    """create table if not exists raw.close_log (
        month date not null, run_at timestamp not null, gl_rows integer, platform_rows integer,
        ap_line_rows integer, budget_rows integer, checks_passed integer, checks_total integer,
        status varchar not null, detail varchar)""",
)


def connect(path) -> duckdb.DuckDBPyConnection:
    """Open (creating if needed) the warehouse file, or ':memory:'."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_raw(con) -> None:
    for statement in RAW_DDL:
        con.execute(statement)


def append_close_log(con, row: dict) -> None:
    """Append one close attempt. The log is append-only: a re-run adds a row, it never edits one."""
    con.execute(
        "insert into raw.close_log values (?, current_timestamp::timestamp, ?, ?, ?, ?, ?, ?, ?, ?)",
        [row["month"], row["gl_rows"], row["platform_rows"], row["ap_line_rows"], row["budget_rows"],
         row["checks_passed"], row["checks_total"], row["status"], row["detail"]],
    )
