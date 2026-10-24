-- A month is closed when its last posting is on the last day of the month. A month that stops earlier is partial.
select
    month_start,
    min(entry_date) as first_posting,
    max(entry_date) as last_posting,
    (date_trunc('month', month_start) + interval 1 month - interval 1 day)::date as month_end,
    max(entry_date) = (date_trunc('month', month_start) + interval 1 month - interval 1 day)::date as is_closed,
    count(*) as entries
from {{ ref('stg_gl_entries') }}
group by month_start
