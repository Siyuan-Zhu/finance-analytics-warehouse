-- Monthly P&L: one row per month and reporting line, every line present (zero when nothing posted).
-- amount is everything posted; excluded_amount is the part booked by run-rate-excluded journals (kept in the report).
with months as (
    select month_start, is_closed from {{ ref('int_month_status') }}
),

posted as (
    select
        month_start,
        reporting_line_key,
        sum(reporting_amount) as amount,
        sum(reporting_amount) filter (where excluded_from_run_rate) as excluded_amount,
        count(*) as entries
    from {{ ref('fct_gl_entries') }}
    where reporting_line_key is not null
    group by month_start, reporting_line_key
)

select
    strftime(m.month_start, '%Y-%m') || ':' || l.reporting_line_key as row_key,
    m.month_start,
    year(m.month_start) as fiscal_year,
    not m.is_closed as is_partial_month,
    l.section_key,
    l.section_label,
    l.section_order,
    l.reporting_line_key,
    l.line_name,
    l.line_order,
    l.sign,
    coalesce(p.amount, 0) as amount,
    coalesce(p.excluded_amount, 0) as excluded_amount,
    coalesce(p.amount, 0) - coalesce(p.excluded_amount, 0) as amount_ex_excluded,
    coalesce(p.entries, 0) as entries
from months as m
cross join {{ ref('dim_reporting_line') }} as l
left join posted as p on p.month_start = m.month_start and p.reporting_line_key = l.reporting_line_key
