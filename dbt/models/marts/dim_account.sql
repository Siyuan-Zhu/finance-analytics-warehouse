select account_code, account_name, statement, account_class
from {{ ref('accounts') }}
