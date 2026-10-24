-- No partial month may sit inside the run-rate window.
select r.window_start, r.window_end, p.month_start as partial_month
from (select distinct window_start, window_end from {{ ref('rpt_run_rate') }}) as r
inner join {{ ref('int_month_status') }} as p
    on not p.is_closed and p.month_start between r.window_start and r.window_end
