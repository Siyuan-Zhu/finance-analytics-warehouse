-- Budget against actual neither loses nor repeats money. For the months that are in both the ledger and the budget:
-- the actual column equals the mapped ledger, and the budget column equals the budget file, for each sign.
with months as (
    select s.month_start
    from {{ ref('int_month_status') }} as s
    where s.month_start in (select month_start from {{ ref('stg_budget') }})
),

report as (
    select sign, sum(actual_amount) as actual, sum(budget_amount) as budget
    from {{ ref('rpt_budget_vs_actual') }}
    group by sign
),

ledger as (
    select l.sign, sum(g.reporting_amount) as actual
    from {{ ref('fct_gl_entries') }} as g
    inner join {{ ref('dim_reporting_line') }} as l using (reporting_line_key)
    where g.month_start in (select month_start from months)
    group by l.sign
),

plan as (
    select l.sign, sum(b.budget_amount) as budget
    from {{ ref('fct_budget') }} as b
    inner join {{ ref('dim_reporting_line') }} as l using (reporting_line_key)
    where b.month_start in (select month_start from months)
    group by l.sign
),

file_total as (
    select sum(budget_amount) as budget
    from {{ ref('stg_budget') }}
    where month_start in (select month_start from months)
)

select r.sign, r.actual, g.actual as ledger_actual, r.budget, p.budget as plan_budget
from report as r
left join ledger as g on g.sign = r.sign
left join plan as p on p.sign = r.sign
where abs(r.actual - coalesce(g.actual, 0)) > 0.01 or abs(r.budget - coalesce(p.budget, 0)) > 0.01

union all

select 'all', null, null, (select sum(budget) from report), budget
from file_total
where abs((select sum(budget) from report) - budget) > 0.01
