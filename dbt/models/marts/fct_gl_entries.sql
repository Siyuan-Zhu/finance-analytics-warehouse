-- One row per ledger posting. Profit-and-loss rows carry their reporting line, the rule that placed them and the
-- run-rate exclusion flag. Balance-sheet and transfer rows carry nulls there.
select
    e.entry_key,
    e.entry_date,
    e.month_start,
    e.account_code,
    e.cost_center_code,
    m.reporting_line_key,
    e.reference,
    e.description,
    e.debit,
    e.credit,
    e.amount,
    m.reporting_amount,
    m.mapping_rule_type,
    m.mapping_rule_order,
    coalesce(m.excluded_from_run_rate, false) as excluded_from_run_rate
from {{ ref('stg_gl_entries') }} as e
left join {{ ref('int_gl_mapped') }} as m on m.entry_key = e.entry_key
