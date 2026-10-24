select
    month_start,
    month_start::varchar as month_label,
    is_partial_month,
    sum(amount) filter (where section_key = 'revenue') as revenue,
    sum(amount) filter (where section_key = 'cogs') as cogs,
    sum(amount) filter (where section_key = 'revenue') - sum(amount) filter (where section_key = 'cogs') as gross_margin,
    sum(amount) filter (where section_key = 'store_opex') as store_opex,
    sum(amount) filter (where section_key = 'ho_opex') as ho_opex,
    sum(amount) filter (where section_key = 'revenue')
        - sum(amount) filter (where section_key in ('cogs', 'store_opex', 'ho_opex')) as operating_income,
    sum(excluded_amount) as excluded_journals
from marts.rpt_monthly_pl
group by month_start, is_partial_month
order by month_start
