select
    bill_id as platform_bill_id,
    landing_month,
    trim(vendor) as vendor_name,
    {{ normalize_vendor('vendor') }} as vendor_key,
    bill_date,
    due_date,
    paid_date,
    amount,
    payment_method,
    nullif(trim(gl_code), '') as gl_code,
    nullif(trim(location), '') as location
from {{ source('raw', 'platform_bills') }}
