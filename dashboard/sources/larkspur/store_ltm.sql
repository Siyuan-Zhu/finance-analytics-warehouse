with last_year as (
    select month_start from marts.rpt_store_pl where not is_partial_month group by month_start
    order by month_start desc limit 12
)
select cost_center_code, any_value(cost_center_name) as cost_center_name, any_value(kind) as kind,
    sum(revenue) as revenue, sum(cogs) as cogs, sum(gross_margin) as gross_margin,
    sum(gross_margin) / nullif(sum(revenue), 0) as gross_margin_pct,
    sum(store_opex) as store_opex, sum(ho_opex) as ho_opex, sum(operating_income) as operating_income
from marts.rpt_store_pl
where month_start in (select month_start from last_year)
group by cost_center_code
order by cost_center_code
