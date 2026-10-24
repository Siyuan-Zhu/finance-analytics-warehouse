-- Row-level result of matching the bill-pay platform against the accounting system.
--   matched          platform bill with exactly one document; counted once
--   platform_only    platform bill with no document (never synced)
--   accounting_only  document that no platform bill resembles (entered directly)
--   ambiguous        platform bill held out: two candidate documents, or its document is claimed twice
select
    'pb:' || platform_bill_id as row_key,
    match_status as status,
    platform_bill_id,
    matched_doc_id as doc_id,
    candidate_docs,
    vendor_key,
    vendor_name,
    bill_date,
    amount,
    resolved_gl_code as gl_code,
    gl_backfilled,
    allocation,
    ambiguity_reason as note
from {{ ref('int_ap_matches') }}

union all

select
    'doc:' || d.doc_id,
    'accounting_only',
    cast(null as varchar),
    d.doc_id,
    cast(null as varchar),
    d.vendor_key,
    d.vendor_name,
    d.bill_date,
    d.amount,
    d.primary_gl_code,
    false,
    d.locations,
    cast(null as varchar)
from {{ ref('int_ap_documents') }} as d
where d.doc_id not in (select doc_id from {{ ref('int_ap_candidates') }})
