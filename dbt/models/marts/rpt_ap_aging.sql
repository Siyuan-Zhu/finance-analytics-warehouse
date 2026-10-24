-- Open payables at each closed month end, by how far past due they are. A bill is open at a month end if it was
-- dated on or before it and not paid until after it (or not paid yet).
with snapshots as (
    select month_end as as_of from {{ ref('dim_date') }} where is_month_end and is_closed_month
),

buckets as (
    select * from (values
        (1, 'Not yet due'), (2, '1-30 days past due'), (3, '31-60 days past due'), (4, '61+ days past due')
    ) as t(bucket_order, bucket)
),

open_bills as (
    select
        s.as_of,
        b.amount,
        case
            when b.due_date >= s.as_of then 1
            when date_diff('day', b.due_date, s.as_of) <= 30 then 2
            when date_diff('day', b.due_date, s.as_of) <= 60 then 3
            else 4
        end as bucket_order
    from snapshots as s
    inner join {{ ref('fct_ap_bills') }} as b
        on b.bill_date <= s.as_of and (b.paid_date is null or b.paid_date > s.as_of)
)

select
    strftime(s.as_of, '%Y-%m') || ':' || k.bucket_order::varchar as row_key,
    s.as_of,
    k.bucket_order,
    k.bucket,
    count(o.amount) as bill_count,
    coalesce(sum(o.amount), 0) as open_amount
from snapshots as s
cross join buckets as k
left join open_bills as o on o.as_of = s.as_of and o.bucket_order = k.bucket_order
group by s.as_of, k.bucket_order, k.bucket
