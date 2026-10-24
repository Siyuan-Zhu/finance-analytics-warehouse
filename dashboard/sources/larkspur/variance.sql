select line_name, section_label, section_order, line_order, is_section_total, current_monthly, prior_monthly,
    change_monthly, change_pct, is_flagged, current_monthly_gross, prior_monthly_gross, change_pct_gross, is_flagged_gross
from marts.rpt_variance
order by section_order, line_order
