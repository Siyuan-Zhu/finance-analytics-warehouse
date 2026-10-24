-- Run rate per reporting line: the average month over the last N closed months (N is a dbt var). The partial month is
-- never in the window. Journals listed in the excluded_journals seed stay in the monthly P&L and come out here.
with window_months as (
    select month_start
    from {{ ref('int_month_status') }}
    where is_closed
    order by month_start desc
    limit {{ var('run_rate_window_months') }}
),

bounds as (
    select min(month_start) as window_start, max(month_start) as window_end, count(*) as months_in_window
    from window_months
),

posted as (
    select
        g.reporting_line_key,
        sum(g.reporting_amount) as gross_total,
        coalesce(sum(g.reporting_amount) filter (where g.excluded_from_run_rate), 0) as excluded_total
    from {{ ref('fct_gl_entries') }} as g
    where g.reporting_line_key is not null
        and g.month_start in (select month_start from window_months)
    group by g.reporting_line_key
)

select
    l.reporting_line_key as row_key,
    l.section_key,
    l.section_label,
    l.section_order,
    l.reporting_line_key,
    l.line_name,
    l.line_order,
    l.sign,
    b.window_start,
    b.window_end,
    b.months_in_window,
    coalesce(p.gross_total, 0) as window_total_gross,
    coalesce(p.excluded_total, 0) as excluded_total,
    coalesce(p.gross_total, 0) - coalesce(p.excluded_total, 0) as window_total,
    (coalesce(p.gross_total, 0) - coalesce(p.excluded_total, 0)) / b.months_in_window as monthly_run_rate,
    coalesce(p.gross_total, 0) / b.months_in_window as monthly_run_rate_incl_excluded,
    12 * (coalesce(p.gross_total, 0) - coalesce(p.excluded_total, 0)) / b.months_in_window as annualised_run_rate
from {{ ref('dim_reporting_line') }} as l
cross join bounds as b
left join posted as p on p.reporting_line_key = l.reporting_line_key
