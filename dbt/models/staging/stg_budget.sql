select
    strftime(month_start, '%Y-%m') || ':' || account_code || ':' || upper(trim(cost_center)) as budget_key,
    month_start,
    account_code,
    upper(trim(cost_center)) as cost_center_code,
    amount as budget_amount
from {{ source('raw', 'budget') }}
