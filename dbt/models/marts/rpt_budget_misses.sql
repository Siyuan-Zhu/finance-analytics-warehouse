-- Quarterly budget misses: closed months only, by quarter, reporting line and cost centre. A miss is adverse by more
-- than budget_miss_pct of budget and by more than budget_miss_min_abs. Quarters with fewer than three closed months
-- are shown but not flagged.
with quarterly as (
    select
        quarter_start,
        reporting_line_key,
        line_name,
        section_label,
        sign,
        cost_center_code,
        count(*) as months_included,
        sum(budget_amount) as budget_amount,
        sum(actual_amount) as actual_amount,
        sum(adverse_amount) as adverse_amount
    from {{ ref('rpt_budget_vs_actual') }}
    where not is_partial_month
    group by all
)

select
    strftime(quarter_start, '%Y-%m') || ':' || reporting_line_key || ':' || cost_center_code as row_key,
    *,
    adverse_amount / nullif(abs(budget_amount), 0) as adverse_pct,
    months_included = 3
        and adverse_amount > {{ var('budget_miss_min_abs') }}
        and adverse_amount / nullif(abs(budget_amount), 0) > {{ var('budget_miss_pct') }} as is_miss
from quarterly
