-- A profit-and-loss row that no rule can place is a failure, never a silent drop.
select entry_key, account_code, reference, description
from {{ ref('fct_gl_entries') }} as g
inner join {{ ref('accounts') }} as a using (account_code)
where a.statement = 'pl' and g.reporting_line_key is null
