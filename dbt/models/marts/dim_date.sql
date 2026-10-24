-- One row per day. Months come from the ledger's own month status: closed, partial, or not yet posted.
with days as (
    select d::date as date_day
    from generate_series(date '2024-01-01', date '2026-12-31', interval 1 day) as t(d)
)

select
    days.date_day,
    year(days.date_day) as fiscal_year,
    quarter(days.date_day) as fiscal_quarter,
    month(days.date_day) as month_num,
    date_trunc('month', days.date_day)::date as month_start,
    strftime(days.date_day, '%Y-%m') as month_label,
    (date_trunc('month', days.date_day) + interval 1 month - interval 1 day)::date as month_end,
    days.date_day = (date_trunc('month', days.date_day) + interval 1 month - interval 1 day)::date as is_month_end,
    coalesce(s.is_closed, false) as is_closed_month,
    s.month_start is not null and not s.is_closed as is_partial_month
from days
left join {{ ref('int_month_status') }} as s on s.month_start = date_trunc('month', days.date_day)::date
