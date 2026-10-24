-- Budget against actual by month, reporting line and cost centre, for months that are in the ledger and have a budget.
-- adverse_amount is positive when the result is worse than budget: an expense over budget or revenue under it.
with actual as (
    select month_start, reporting_line_key, cost_center_code, sum(reporting_amount) as actual_amount
    from {{ ref('fct_gl_entries') }}
    where reporting_line_key is not null
    group by all
),

budget as (
    select month_start, reporting_line_key, cost_center_code, sum(budget_amount) as budget_amount
    from {{ ref('fct_budget') }}
    group by all
),

joined as (
    select
        coalesce(a.month_start, b.month_start) as month_start,
        coalesce(a.reporting_line_key, b.reporting_line_key) as reporting_line_key,
        coalesce(a.cost_center_code, b.cost_center_code) as cost_center_code,
        coalesce(b.budget_amount, 0) as budget_amount,
        coalesce(a.actual_amount, 0) as actual_amount
    from actual as a
    full outer join budget as b
        on b.month_start = a.month_start
        and b.reporting_line_key = a.reporting_line_key
        and b.cost_center_code = a.cost_center_code
)

select
    strftime(j.month_start, '%Y-%m') || ':' || j.reporting_line_key || ':' || j.cost_center_code as row_key,
    j.month_start,
    year(j.month_start) as fiscal_year,
    date_trunc('quarter', j.month_start)::date as quarter_start,
    not s.is_closed as is_partial_month,
    l.section_key,
    l.section_label,
    l.reporting_line_key,
    l.line_name,
    l.sign,
    j.cost_center_code,
    j.budget_amount,
    j.actual_amount,
    j.actual_amount - j.budget_amount as variance_amount,
    (j.actual_amount - j.budget_amount) / nullif(j.budget_amount, 0) as variance_pct,
    case l.sign when 'expense' then j.actual_amount - j.budget_amount else j.budget_amount - j.actual_amount end
        as adverse_amount
from joined as j
inner join {{ ref('dim_reporting_line') }} as l on l.reporting_line_key = j.reporting_line_key
inner join {{ ref('int_month_status') }} as s on s.month_start = j.month_start
where j.month_start in (select month_start from {{ ref('stg_budget') }})
