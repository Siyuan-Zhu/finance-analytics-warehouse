-- Run rate now against the run rate a year earlier: the last N closed months against the N before them.
-- Lines and section totals. Two views: without the excluded journals (the run rate) and with them.
-- A line is flagged when its percent change and its change per month both exceed the vars.
with closed as (
    select month_start, row_number() over (order by month_start desc) as age
    from {{ ref('int_month_status') }}
    where is_closed
),

windows as (
    select month_start, case when age <= {{ var('run_rate_window_months') }} then 'current' else 'prior' end as period
    from closed
    where age <= 2 * {{ var('run_rate_window_months') }}
),

counts as (
    select period, count(*) as months from windows group by period
),

by_line as (
    select
        w.period,
        g.reporting_line_key,
        sum(g.reporting_amount) as gross_total,
        sum(g.reporting_amount) filter (where not g.excluded_from_run_rate) as net_total
    from {{ ref('fct_gl_entries') }} as g
    inner join windows as w on w.month_start = g.month_start
    where g.reporting_line_key is not null
    group by w.period, g.reporting_line_key
),

lines as (
    select
        l.reporting_line_key,
        l.line_name,
        l.section_key,
        l.section_label,
        l.section_order,
        l.line_order,
        false as is_section_total,
        coalesce(max(b.net_total) filter (where b.period = 'current'), 0) as current_total,
        coalesce(max(b.net_total) filter (where b.period = 'prior'), 0) as prior_total,
        coalesce(max(b.gross_total) filter (where b.period = 'current'), 0) as current_total_gross,
        coalesce(max(b.gross_total) filter (where b.period = 'prior'), 0) as prior_total_gross
    from {{ ref('dim_reporting_line') }} as l
    left join by_line as b on b.reporting_line_key = l.reporting_line_key
    group by all
),

sections as (
    select
        'total_' || section_key as reporting_line_key,
        'Total ' || lower(section_label) as line_name,
        section_key,
        section_label,
        section_order,
        99 as line_order,
        true as is_section_total,
        sum(current_total), sum(prior_total), sum(current_total_gross), sum(prior_total_gross)
    from lines
    group by section_key, section_label, section_order
),

combined as (
    select * from lines
    union all
    select * from sections
),

per_month as (
    select
        c.*,
        cur.months as current_months,
        pri.months as prior_months,
        c.current_total / cur.months as current_monthly,
        c.prior_total / nullif(pri.months, 0) as prior_monthly,
        c.current_total_gross / cur.months as current_monthly_gross,
        c.prior_total_gross / nullif(pri.months, 0) as prior_monthly_gross
    from combined as c
    cross join (select coalesce(max(months) filter (where period = 'current'), 1) as months from counts) as cur
    cross join (select max(months) filter (where period = 'prior') as months from counts) as pri
)

select
    reporting_line_key as row_key,
    reporting_line_key,
    line_name,
    section_key,
    section_label,
    section_order,
    line_order,
    is_section_total,
    current_months,
    prior_months,
    current_monthly,
    prior_monthly,
    current_monthly - prior_monthly as change_monthly,
    (current_monthly - prior_monthly) / nullif(abs(prior_monthly), 0) as change_pct,
    not is_section_total
        and abs((current_monthly - prior_monthly) / nullif(abs(prior_monthly), 0)) > {{ var('variance_pct_threshold') }}
        and abs(current_monthly - prior_monthly) > {{ var('variance_min_abs_monthly') }} as is_flagged,
    current_monthly_gross,
    prior_monthly_gross,
    current_monthly_gross - prior_monthly_gross as change_monthly_gross,
    (current_monthly_gross - prior_monthly_gross) / nullif(abs(prior_monthly_gross), 0) as change_pct_gross,
    not is_section_total
        and abs((current_monthly_gross - prior_monthly_gross) / nullif(abs(prior_monthly_gross), 0))
            > {{ var('variance_pct_threshold') }}
        and abs(current_monthly_gross - prior_monthly_gross) > {{ var('variance_min_abs_monthly') }}
        as is_flagged_gross
from per_month
