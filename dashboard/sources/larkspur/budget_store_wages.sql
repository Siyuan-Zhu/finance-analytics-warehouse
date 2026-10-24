select month_start, cost_center_code, budget_amount, actual_amount, variance_pct
from marts.rpt_budget_vs_actual
where line_name = 'Store Wages' and not is_partial_month
order by month_start, cost_center_code
