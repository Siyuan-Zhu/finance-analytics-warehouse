-- One row per normalized vendor. The display name is the platform's spelling when there is one.
with names as (
    select vendor_key, vendor_name, 1 as priority from {{ ref('stg_platform_bills') }}
    union all
    select vendor_key, vendor_name, 2 as priority from {{ ref('stg_ap_bill_lines') }}
)

select
    vendor_key,
    arg_min(vendor_name, priority * 1000000 + length(vendor_name)) as vendor_name
from names
group by vendor_key
