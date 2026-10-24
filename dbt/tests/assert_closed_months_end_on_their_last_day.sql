-- Closed-month detection, checked against the raw postings with a different date function than the model uses.
-- A month is closed when its last posting is on the calendar month's last day. Only the newest month in the ledger may
-- be partial: a short month anywhere else means a missing export, not an open month.
with raw_months as (
    select
        date_trunc('month', entry_date)::date as month_start,
        max(entry_date) as last_posting
    from {{ source('raw', 'gl_entries') }}
    group by 1
),

expected as (
    select
        month_start,
        last_posting = last_day(last_posting) as should_be_closed,
        month_start = max(month_start) over () as is_newest
    from raw_months
)

select e.month_start, s.is_closed, e.should_be_closed, e.is_newest
from expected as e
left join {{ ref('int_month_status') }} as s on s.month_start = e.month_start
where s.month_start is null
    or s.is_closed <> e.should_be_closed
    or (not e.should_be_closed and not e.is_newest)
