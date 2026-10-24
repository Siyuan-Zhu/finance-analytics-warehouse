select month_start, section_label, section_order, line_name, line_order, is_partial_month, amount, excluded_amount
from marts.rpt_monthly_pl
order by month_start, section_order, line_order
