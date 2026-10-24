select
    strftime(landing_month, '%Y-%m') || ':' || lpad(source_row::varchar, 6, '0') as entry_key,
    landing_month,
    source_row,
    account_code,
    trim(account_name) as account_name,
    entry_date,
    date_trunc('month', entry_date)::date as month_start,
    nullif(trim(reference), '') as reference,
    trim(description) as description,
    upper(trim(cost_center)) as cost_center_code,
    debit,
    credit,
    debit - credit as amount
from {{ source('raw', 'gl_entries') }}
