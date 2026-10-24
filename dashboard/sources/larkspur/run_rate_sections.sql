select section_label, section_order, any_value(window_start) as window_start, any_value(window_end) as window_end,
    sum(monthly_run_rate) as monthly_run_rate, sum(monthly_run_rate_incl_excluded) as monthly_run_rate_incl_excluded
from marts.rpt_run_rate
group by section_label, section_order
order by section_order
