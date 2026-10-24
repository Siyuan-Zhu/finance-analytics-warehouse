select month_start, section_label, sum(budget_amount) as budget, sum(actual_amount) as actual,
    sum(adverse_amount) as adverse
from marts.rpt_budget_vs_actual
where not is_partial_month
group by month_start, section_label, sign
order by month_start
