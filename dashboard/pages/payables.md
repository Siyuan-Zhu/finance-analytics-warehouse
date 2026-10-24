---
title: Payables
---

<Alert status="info">
All data on this page is synthetic. Vendors are invented. Amounts are in NIU (normalized index units).
</Alert>

Most bills appear in both the AP export and the accounting system. Adding the two counts those bills twice. The reconciliation matches bills by vendor, amount and date and removes the duplicates.

```sql totals
select * from larkspur.ap_totals
```

<BigValue data={totals} value=platform_total title="AP export total" fmt="#,##0" />
<BigValue data={totals} value=accounting_total title="Accounting total" fmt="#,##0" />
<BigValue data={totals} value=deduplicated_total title="After removing duplicates" fmt="#,##0" />

```sql steps
select 'Naive total (AP export plus accounting)' as step, platform_total + accounting_total as amount from larkspur.ap_totals
union all select 'Less AP bills matched to a document', -matched_total from larkspur.ap_totals
union all select 'Less ambiguous bills held out', -held_out_total from larkspur.ap_totals
union all select 'Deduplicated total', deduplicated_total from larkspur.ap_totals
```

<DataTable data={steps}>
    <Column id=step />
    <Column id=amount fmt="#,##0" />
</DataTable>

```sql status
select case status when 'matched' then 'Matched to one document'
    when 'platform_only' then 'AP export only'
    when 'accounting_only' then 'Accounting only (entered directly)'
    else 'Ambiguous (held out)' end as outcome, bills, amount
from larkspur.ap_status
```

<DataTable data={status}>
    <Column id=outcome />
    <Column id=bills />
    <Column id=amount fmt="#,##0" />
</DataTable>

```sql ambiguous
select platform_bill_id as bill, vendor_name as vendor, bill_date, amount, note, candidate_docs as candidates
from larkspur.ap_ambiguous
order by bill_date desc
```

<DataTable data={ambiguous} rows=10 title="Ambiguous bills held out for review">
    <Column id=bill />
    <Column id=vendor />
    <Column id=bill_date fmt="yyyy-mm-dd" />
    <Column id=amount fmt="#,##0.00" />
    <Column id=note />
    <Column id=candidates />
</DataTable>

## Aging

Open payables at each month end by how far past due they are.

```sql aging
select as_of, bucket, open_amount from larkspur.ap_aging order by as_of, bucket_order
```

<BarChart
    data={aging}
    x=as_of
    y=open_amount
    series=bucket
    type=stacked
    yFmt="#,##0"
    title="Open payables by age at each month end"
    subtitle="Synthetic data. NIU."
/>

## Days payable outstanding

DPO (days payable outstanding) is how many days of purchases are still unpaid at month end: open payables divided by the last 90 days of bills, times 90. It is a noisy monthly figure, so the chart also shows the average days from bill date to payment for bills paid that month.

```sql dpo
select month_start, dpo, avg_days_to_pay, share_paid_late from larkspur.dpo order by month_start
```

<LineChart
    data={dpo}
    x=month_start
    y={['dpo', 'avg_days_to_pay']}
    yFmt="0.0"
    title="DPO and days to pay"
    subtitle="Synthetic data. Days. Payments start to slip in July 2025."
/>

<LineChart
    data={dpo}
    x=month_start
    y=share_paid_late
    yFmt="pct0"
    title="Share of bills paid after the due date"
    subtitle="Synthetic data. By count, bills paid in the month."
/>
