"""A tiny hand-built marts schema, so the pack can be tested without running dbt."""
from __future__ import annotations

from datetime import date

import duckdb

TABLES = {
    "rpt_monthly_pl": "month_start date, fiscal_year int, is_partial_month boolean, section_key varchar, "
                      "section_label varchar, section_order int, reporting_line_key varchar, line_name varchar, "
                      "line_order int, sign varchar, amount decimal(14,2), excluded_amount decimal(14,2)",
    "rpt_store_pl": "month_start date, fiscal_year int, is_partial_month boolean, cost_center_code varchar, "
                    "cost_center_name varchar, revenue decimal(14,2), cogs decimal(14,2), gross_margin decimal(14,2), "
                    "gross_margin_pct double, store_opex decimal(14,2), ho_opex decimal(14,2), operating_income decimal(14,2)",
    "rpt_budget_vs_actual": "month_start date, fiscal_year int, is_partial_month boolean, section_key varchar, "
                            "section_label varchar, sign varchar, budget_amount decimal(14,2), actual_amount decimal(14,2)",
    "rpt_budget_misses": "quarter_start date, line_name varchar, cost_center_code varchar, budget_amount decimal(14,2), "
                         "actual_amount decimal(14,2), adverse_amount decimal(14,2), adverse_pct double, is_miss boolean",
    "rpt_run_rate": "section_label varchar, section_order int, line_name varchar, line_order int, sign varchar, "
                    "monthly_run_rate decimal(14,2), monthly_run_rate_incl_excluded decimal(14,2), "
                    "excluded_total decimal(14,2), window_start date, window_end date, months_in_window int",
    "rpt_variance": "line_name varchar, section_label varchar, section_order int, line_order int, is_section_total boolean, "
                    "current_monthly decimal(14,2), prior_monthly decimal(14,2), change_pct double, is_flagged boolean, "
                    "current_monthly_gross decimal(14,2), prior_monthly_gross decimal(14,2), change_pct_gross double, "
                    "is_flagged_gross boolean",
    "rpt_ap_totals": "platform_total decimal(14,2), accounting_total decimal(14,2), matched_total decimal(14,2), "
                     "held_out_total decimal(14,2), deduplicated_total decimal(14,2), matched_count int, "
                     "platform_only_count int, accounting_only_count int, ambiguous_count int",
    "rpt_ap_aging": "as_of date, bucket_order int, bucket varchar, bill_count int, open_amount decimal(14,2)",
    "rpt_dpo": "month_start date, as_of date, open_amount decimal(14,2), bills_90d decimal(14,2), dpo double, "
               "avg_days_to_pay double, share_paid_late double",
}


def make_marts(con: duckdb.DuckDBPyConnection, **rows) -> None:
    """Create every marts table; rows maps a table name to a list of value tuples."""
    con.execute("create schema if not exists marts")
    for name, columns in TABLES.items():
        con.execute(f"create table marts.{name} ({columns})")
        for r in rows.get(name, []):
            con.execute(f"insert into marts.{name} values ({', '.join('?' * len(r))})", list(r))


def line(month, key, name, section, order, sign, amount, partial=False, excluded=0, line_order=1, section_order=1):
    """A rpt_monthly_pl row."""
    return (month, month.year, partial, key, section, section_order, key + "_" + name, name, line_order, sign, amount, excluded)


JAN, FEB, MAR = date(2025, 1, 1), date(2025, 2, 1), date(2025, 3, 1)
