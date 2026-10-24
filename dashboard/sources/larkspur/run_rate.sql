select section_label, section_order, line_name, line_order, window_start, window_end, months_in_window,
    monthly_run_rate, monthly_run_rate_incl_excluded, excluded_total
from marts.rpt_run_rate
order by section_order, line_order
