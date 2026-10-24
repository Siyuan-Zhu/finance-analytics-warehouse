-- Days payable outstanding at each closed month end: open payables divided by the bills dated in the 90 days up to
-- that date, times the days covered (at most 90). Also the amount-weighted days from bill to payment for bills paid
-- in the month, and the share of bills (by count) paid after their due date.
with snapshots as (
    select month_start, month_end as as_of from {{ ref('dim_date') }} where is_month_end and is_closed_month
),

first_bill as (
    select min(bill_date) as first_date from {{ ref('fct_ap_bills') }}
),

open_ap as (
    select s.as_of, coalesce(sum(b.amount), 0) as open_amount
    from snapshots as s
    left join {{ ref('fct_ap_bills') }} as b
        on b.bill_date <= s.as_of and (b.paid_date is null or b.paid_date > s.as_of)
    group by s.as_of
),

purchases as (
    select s.as_of, coalesce(sum(b.amount), 0) as bills_90d
    from snapshots as s
    left join {{ ref('fct_ap_bills') }} as b
        on b.bill_date <= s.as_of and b.bill_date > s.as_of - interval 90 day
    group by s.as_of
),

paid as (
    select
        s.as_of,
        sum(b.amount * date_diff('day', b.bill_date, b.paid_date)) / nullif(sum(b.amount), 0) as avg_days_to_pay,
        count(*) filter (where b.paid_date > b.due_date)::double / nullif(count(*), 0) as share_paid_late,
        count(*) as bills_paid
    from snapshots as s
    inner join {{ ref('fct_ap_bills') }} as b
        on date_trunc('month', b.paid_date)::date = s.month_start
    group by s.as_of
)

select
    strftime(s.as_of, '%Y-%m') as row_key,
    s.month_start,
    s.as_of,
    o.open_amount,
    p.bills_90d,
    least(90, date_diff('day', f.first_date, s.as_of) + 1) as days_covered,
    o.open_amount / nullif(p.bills_90d, 0) * least(90, date_diff('day', f.first_date, s.as_of) + 1) as dpo,
    d.avg_days_to_pay,
    d.share_paid_late,
    d.bills_paid
from snapshots as s
cross join first_bill as f
inner join open_ap as o on o.as_of = s.as_of
inner join purchases as p on p.as_of = s.as_of
left join paid as d on d.as_of = s.as_of
