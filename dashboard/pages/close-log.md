---
title: Close log
---

<Alert status="info">
All data on this page is synthetic. The close log is written by the monthly close of the demo warehouse.
</Alert>

Each row is one run of `python -m src.close --month YYYY-MM`. The close loads that month's files, builds the warehouse with dbt (which runs its tests), re-reads the raw file with an independent check, writes the Excel pack and evaluates every formula in it. If any check fails the status is failed and the close exits non-zero.

```sql log
select * from larkspur.close_log order by month, run_at
```

```sql log_totals
select count(*) as runs, count(*) filter (where status = 'closed') as closed, sum(checks_passed) as checks_passed,
    sum(checks_total) as checks_total
from larkspur.close_log
```

<BigValue data={log_totals} value=runs title="Close runs" />
<BigValue data={log_totals} value=closed title="Closed" />
<BigValue data={log_totals} value=checks_passed title="Checks passed" fmt="#,##0" />

<DataTable data={log} rows=40 search=true>
    <Column id=month_label title="Month" />
    <Column id=run_at title="Run at" fmt="yyyy-mm-dd hh:mm" />
    <Column id=status />
    <Column id=gl_rows title="Ledger rows" />
    <Column id=platform_rows title="AP bills" />
    <Column id=ap_line_rows title="Bill lines" />
    <Column id=budget_rows title="Budget rows" />
    <Column id=checks_passed title="Checks passed" />
    <Column id=checks_total title="Checks" />
</DataTable>

<BarChart
    data={log}
    x=month
    y=gl_rows
    title="Ledger rows loaded per month"
    subtitle="Synthetic data. October 2026 is a partial month."
/>
