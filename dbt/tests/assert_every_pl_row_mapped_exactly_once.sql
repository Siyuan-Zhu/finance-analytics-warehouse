-- Each profit-and-loss row in staging appears in int_gl_mapped exactly once, and no mapped row is invented.
with staged as (
    select e.entry_key
    from {{ ref('stg_gl_entries') }} as e
    inner join {{ ref('accounts') }} as a on a.account_code = e.account_code
    where a.statement = 'pl'
),

mapped as (
    select entry_key, count(*) as times from {{ ref('int_gl_mapped') }} group by entry_key
)

select coalesce(s.entry_key, m.entry_key) as entry_key, m.times
from staged as s
full outer join mapped as m on m.entry_key = s.entry_key
where s.entry_key is null or m.entry_key is null or m.times <> 1
