-- Postings: the fact table carries every staged row, so debits and credits agree month by month.
-- Reports: net income in rpt_monthly_pl equals credits minus debits on the staged profit-and-loss rows.
with staged as (
    select month_start, count(*) as n, sum(debit) as debit, sum(credit) as credit
    from {{ ref('stg_gl_entries') }} group by month_start
),

fact as (
    select month_start, count(*) as n, sum(debit) as debit, sum(credit) as credit
    from {{ ref('fct_gl_entries') }} group by month_start
),

staged_pl as (
    select e.month_start, sum(e.credit - e.debit) as net_income
    from {{ ref('stg_gl_entries') }} as e
    inner join {{ ref('accounts') }} as a on a.account_code = e.account_code
    where a.statement = 'pl'
    group by e.month_start
),

report as (
    select month_start,
        sum(amount) filter (where sign = 'income') - sum(amount) filter (where sign = 'expense') as net_income
    from {{ ref('rpt_monthly_pl') }} group by month_start
)

select s.month_start, 'fact differs from staging' as problem
from staged as s
left join fact as f on f.month_start = s.month_start
where f.month_start is null or f.n <> s.n or abs(f.debit - s.debit) > 0.005 or abs(f.credit - s.credit) > 0.005

union all

select p.month_start, 'report differs from staging'
from staged_pl as p
left join report as r on r.month_start = p.month_start
where r.month_start is null or abs(r.net_income - p.net_income) > 0.005
