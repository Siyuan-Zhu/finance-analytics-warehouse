-- P&L by cost centre and month with gross margin. HQ01 carries online sales and head office expense.
select
    strftime(g.month_start, '%Y-%m') || ':' || g.cost_center_code as row_key,
    g.month_start,
    year(g.month_start) as fiscal_year,
    not s.is_closed as is_partial_month,
    g.cost_center_code,
    c.cost_center_name,
    c.kind,
    sum(g.reporting_amount) filter (where l.section_key = 'revenue') as revenue,
    sum(g.reporting_amount) filter (where l.section_key = 'cogs') as cogs,
    sum(g.reporting_amount) filter (where l.section_key = 'revenue')
        - sum(g.reporting_amount) filter (where l.section_key = 'cogs') as gross_margin,
    (sum(g.reporting_amount) filter (where l.section_key = 'revenue')
        - sum(g.reporting_amount) filter (where l.section_key = 'cogs'))
        / nullif(sum(g.reporting_amount) filter (where l.section_key = 'revenue'), 0) as gross_margin_pct,
    coalesce(sum(g.reporting_amount) filter (where l.section_key = 'store_opex'), 0) as store_opex,
    coalesce(sum(g.reporting_amount) filter (where l.section_key = 'ho_opex'), 0) as ho_opex,
    coalesce(sum(g.reporting_amount) filter (where l.section_key = 'revenue'), 0)
        - coalesce(sum(g.reporting_amount) filter (where l.section_key in ('cogs', 'store_opex', 'ho_opex')), 0)
        as operating_income
from {{ ref('fct_gl_entries') }} as g
inner join {{ ref('dim_reporting_line') }} as l on l.reporting_line_key = g.reporting_line_key
inner join {{ ref('dim_cost_center') }} as c on c.cost_center_code = g.cost_center_code
inner join {{ ref('int_month_status') }} as s on s.month_start = g.month_start
group by g.month_start, g.cost_center_code, c.cost_center_name, c.kind, s.is_closed
