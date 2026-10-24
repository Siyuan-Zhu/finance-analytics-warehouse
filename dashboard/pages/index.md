---
title: Overview
---

<Alert status="info">
All data on this page is synthetic. Larkspur Outfitters is a fictional five-store outdoor-gear retailer. Amounts are in NIU (normalized index units).
</Alert>

This dashboard reads the warehouse that the monthly close builds. Every number comes from a table in the `marts` schema.
The pages are Overview, Stores, Budget vs actual, Payables and Close log.

```sql run_rate_totals
select
    sum(monthly_run_rate) filter (where section_order = 1) as revenue,
    sum(monthly_run_rate) filter (where section_order = 1) - sum(monthly_run_rate) filter (where section_order > 1) as operating_income,
    sum(monthly_run_rate_incl_excluded) filter (where section_order = 1) - sum(monthly_run_rate_incl_excluded) filter (where section_order > 1) as operating_income_incl,
    any_value(window_start) as window_start,
    any_value(window_end) as window_end
from larkspur.run_rate_sections
```

<BigValue data={run_rate_totals} value=revenue title="Revenue run rate per month (NIU)" fmt="#,##0" />
<BigValue data={run_rate_totals} value=operating_income title="Operating income run rate per month (NIU)" fmt="#,##0" />
<BigValue data={run_rate_totals} value=operating_income_incl title="Same, if the year-end count adjustments were left in (NIU)" fmt="#,##0" />

The run rate is the average month over the last 12 closed months, <Value data={run_rate_totals} column=window_start fmt="mmm yyyy" /> to <Value data={run_rate_totals} column=window_end fmt="mmm yyyy" />. The partial month is not in it.

## Monthly P&L

```sql monthly
select * from larkspur.monthly_summary order by month_start
```

<LineChart
    data={monthly}
    x=month_start
    y={['revenue', 'gross_margin', 'operating_income']}
    yFmt="#,##0"
    title="Revenue, gross margin and operating income by month"
    subtitle="Synthetic data. NIU. The last point is a partial month."
/>

November and December are the holiday peak. The last month, October 2026, holds only its first few days.

<DataTable data={monthly} rows=12 search=true>
    <Column id=month_label title="Month" />
    <Column id=revenue fmt="#,##0" />
    <Column id=cogs title="Cost of goods" fmt="#,##0" />
    <Column id=gross_margin fmt="#,##0" />
    <Column id=store_opex title="Store expense" fmt="#,##0" />
    <Column id=ho_opex title="Head office expense" fmt="#,##0" />
    <Column id=operating_income fmt="#,##0" />
</DataTable>

## The year-end count adjustment

Each December a journal books the annual physical-count true-up into cost of goods. It stays in the monthly P&L. It is on the excluded list, so it is not in the run rate.

```sql shrinkage
select month_start,
    amount - excluded_amount as regular_shrinkage,
    excluded_amount as count_adjustment
from larkspur.monthly_lines
where line_name = 'Inventory Shrinkage' and not is_partial_month
order by month_start
```

<BarChart
    data={shrinkage}
    x=month_start
    y={['regular_shrinkage', 'count_adjustment']}
    type=stacked
    yFmt="#,##0"
    title="Inventory shrinkage by month"
    subtitle="Synthetic data. NIU. The December count adjustment is shown separately."
/>

## Run rate by section

```sql sections
select section_label as section, monthly_run_rate, monthly_run_rate_incl_excluded,
    monthly_run_rate_incl_excluded - monthly_run_rate as excluded_journals_effect
from larkspur.run_rate_sections
order by section_order
```

<DataTable data={sections}>
    <Column id=section />
    <Column id=monthly_run_rate title="Run rate per month" fmt="#,##0" />
    <Column id=monthly_run_rate_incl_excluded title="If excluded journals were left in" fmt="#,##0" />
    <Column id=excluded_journals_effect title="Effect of excluded journals" fmt="#,##0" />
</DataTable>

## Variance: this year against last year

The last 12 closed months against the 12 before them. A line is flagged when it moved by more than 15 percent and by more than 1,000 NIU a month. The right-hand columns show what the comparison says if the excluded journals are left in.

```sql flagged
select line_name as line, section_label as section, current_monthly, prior_monthly, change_pct,
    case when is_flagged then 'yes' else '' end as flagged,
    change_pct_gross as change_pct_with_excluded,
    case when is_flagged_gross then 'yes' else '' end as flagged_with_excluded
from larkspur.variance
where not is_section_total and (is_flagged or is_flagged_gross)
order by abs(change_pct_gross) desc
```

<DataTable data={flagged}>
    <Column id=line />
    <Column id=section />
    <Column id=current_monthly title="Current per month" fmt="#,##0" />
    <Column id=prior_monthly title="Prior per month" fmt="#,##0" />
    <Column id=change_pct title="Change" fmt="pct1" />
    <Column id=flagged />
    <Column id=change_pct_with_excluded title="Change, excluded journals left in" fmt="pct1" />
    <Column id=flagged_with_excluded title="Flagged" />
</DataTable>

```sql all_variance
select line_name as line, section_label as section, is_section_total, current_monthly, prior_monthly, change_pct
from larkspur.variance
order by section_order, line_order
```

<DataTable data={all_variance} rows=30 title="All lines">
    <Column id=line />
    <Column id=section />
    <Column id=current_monthly title="Current per month" fmt="#,##0" />
    <Column id=prior_monthly title="Prior per month" fmt="#,##0" />
    <Column id=change_pct title="Change" fmt="pct1" />
</DataTable>
