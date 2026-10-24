---
title: Stores
---

<Alert status="info">
All data on this page is synthetic. The five stores and the head office are fictional. Amounts are in NIU (normalized index units).
</Alert>

Gross margin is revenue less cost of goods. The head office row carries online sales and the head office expense.

```sql ltm
select cost_center_code as code, cost_center_name as name, revenue, cogs, gross_margin, gross_margin_pct,
    store_opex, ho_opex, operating_income
from larkspur.store_ltm
order by code
```

<DataTable data={ltm} title="Last 12 closed months">
    <Column id=code />
    <Column id=name />
    <Column id=revenue fmt="#,##0" />
    <Column id=cogs title="Cost of goods" fmt="#,##0" />
    <Column id=gross_margin fmt="#,##0" />
    <Column id=gross_margin_pct title="Gross margin %" fmt="pct1" />
    <Column id=store_opex title="Store expense" fmt="#,##0" />
    <Column id=ho_opex title="Head office expense" fmt="#,##0" />
    <Column id=operating_income fmt="#,##0" />
</DataTable>

```sql monthly_store
select month_start, cost_center_name as store, revenue, gross_margin, gross_margin_pct
from larkspur.store_pl
where not is_partial_month and kind = 'store'
order by month_start
```

<LineChart
    data={monthly_store}
    x=month_start
    y=revenue
    series=store
    yFmt="#,##0"
    title="Revenue by store"
    subtitle="Synthetic data. NIU."
/>

<LineChart
    data={monthly_store}
    x=month_start
    y=gross_margin_pct
    series=store
    yFmt="pct1"
    yMin=0.4
    title="Gross margin % by store"
    subtitle="Synthetic data. Share of revenue."
/>

<BarChart
    data={ltm.filter(d => d.code !== 'HQ01')}
    x=name
    y=gross_margin
    yFmt="#,##0"
    title="Gross margin by store, last 12 closed months"
    subtitle="Synthetic data. NIU."
/>
