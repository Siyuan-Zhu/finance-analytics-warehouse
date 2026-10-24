select month_start, is_partial_month, cost_center_code, cost_center_name, kind, revenue, cogs, gross_margin,
    gross_margin_pct, store_opex, ho_opex, operating_income
from marts.rpt_store_pl
order by month_start, cost_center_code
