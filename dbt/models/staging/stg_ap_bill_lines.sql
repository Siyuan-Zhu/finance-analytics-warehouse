select
    doc_id || '-' || line_no::varchar as line_key,
    doc_id,
    line_no,
    landing_month,
    trim(vendor) as vendor_name,
    {{ normalize_vendor('vendor') }} as vendor_key,
    bill_date,
    due_date,
    paid_date,
    nullif(trim(gl_code), '') as gl_code,
    nullif(trim(location), '') as location,
    amount
from {{ source('raw', 'ap_bill_lines') }}
