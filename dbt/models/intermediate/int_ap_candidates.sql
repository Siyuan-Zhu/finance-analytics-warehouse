-- Every platform bill / accounting document pair that looks like the same bill: same normalized vendor, amount
-- within the tolerance, date within the window. The tolerance and window are dbt vars.
select
    b.platform_bill_id,
    d.doc_id
from {{ ref('stg_platform_bills') }} as b
inner join {{ ref('int_ap_documents') }} as d
    on d.vendor_key = b.vendor_key
    and abs(d.amount - b.amount) <= {{ var('ap_amount_tolerance') }} + 0.000001
    and abs(date_diff('day', d.bill_date, b.bill_date)) <= {{ var('ap_date_window_days') }}
