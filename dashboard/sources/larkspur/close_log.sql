select month, month::varchar as month_label, run_at, gl_rows, platform_rows, ap_line_rows, budget_rows,
    checks_passed, checks_total, status, detail
from raw.close_log
order by month, run_at
