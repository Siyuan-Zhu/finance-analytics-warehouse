-- One row per budget line, with the reporting line its account maps to (the account rule in the mapping seed).
select
    b.budget_key,
    b.month_start,
    b.account_code,
    b.cost_center_code,
    r.reporting_line_key,
    b.budget_amount
from {{ ref('stg_budget') }} as b
left join {{ ref('mapping_rules') }} as r on r.rule_type = 'account' and r.match_value = b.account_code
