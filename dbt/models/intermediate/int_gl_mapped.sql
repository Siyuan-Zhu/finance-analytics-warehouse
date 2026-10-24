-- Every profit-and-loss posting, mapped to one reporting line by the ordered rules in the mapping_rules seed.
-- The lowest rule_order that matches wins. The rule that fired is kept on the row. A row no rule can place keeps a
-- null reporting_line_key so a test can fail on it; nothing is dropped.
with pl as (
    select e.*
    from {{ ref('stg_gl_entries') }} as e
    inner join {{ ref('accounts') }} as a on a.account_code = e.account_code
    where a.statement = 'pl'
),

hits as (
    select
        pl.entry_key,
        r.rule_order,
        r.rule_type,
        r.match_value,
        r.reporting_line_key
    from pl
    inner join {{ ref('mapping_rules') }} as r
        on (r.rule_type = 'reference' and pl.reference = r.match_value)
        or (r.rule_type = 'account' and pl.account_code = r.match_value)
        or (r.rule_type = 'keyword' and lower(pl.description) like '%' || lower(r.match_value) || '%')
),

first_hit as (
    select *
    from hits
    qualify row_number() over (partition by entry_key order by rule_order) = 1
)

select
    pl.entry_key,
    pl.landing_month,
    pl.entry_date,
    pl.month_start,
    pl.account_code,
    pl.cost_center_code,
    pl.reference,
    pl.description,
    pl.debit,
    pl.credit,
    pl.amount,
    h.rule_order as mapping_rule_order,
    h.rule_type as mapping_rule_type,
    h.match_value as mapping_match_value,
    h.reporting_line_key,
    case l.sign when 'income' then pl.credit - pl.debit when 'expense' then pl.debit - pl.credit end as reporting_amount,
    x.reference is not null as excluded_from_run_rate
from pl
left join first_hit as h on h.entry_key = pl.entry_key
left join {{ ref('reporting_lines') }} as l on l.reporting_line_key = h.reporting_line_key
left join (
    select distinct reference from {{ ref('excluded_journals') }} where excluded_from = 'run_rate'
) as x on x.reference = pl.reference
