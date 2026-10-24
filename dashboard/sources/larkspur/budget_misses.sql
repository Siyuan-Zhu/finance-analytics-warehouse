select quarter_start, quarter_start::varchar as quarter_label, line_name, cost_center_code, section_label,
    budget_amount, actual_amount, adverse_amount, adverse_pct
from marts.rpt_budget_misses
where is_miss
order by quarter_start, adverse_amount desc
