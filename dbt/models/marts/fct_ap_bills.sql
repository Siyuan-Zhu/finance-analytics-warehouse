-- One row per real payable, after removing the platform/accounting double count.
--   synced               accounting document that a platform bill matched (platform dates and coding used)
--   direct               accounting document entered directly, no platform bill
--   unresolved_candidate accounting document that an ambiguous platform bill might match
--   platform_only        platform bill with no accounting document
-- Ambiguous platform bills themselves are held out; they appear in rpt_ap_reconciliation.
with documents as (
    select
        'doc:' || d.doc_id as ap_bill_key,
        case
            when m.platform_bill_id is not null then 'synced'
            when c.doc_id is not null then 'unresolved_candidate'
            else 'direct'
        end as source,
        m.platform_bill_id,
        d.doc_id,
        d.vendor_key,
        coalesce(m.bill_date, d.bill_date) as bill_date,
        coalesce(m.due_date, d.due_date) as due_date,
        coalesce(m.paid_date, d.paid_date) as paid_date,
        d.amount,
        coalesce(m.resolved_gl_code, d.primary_gl_code) as gl_code,
        case
            when m.platform_bill_id is not null and m.location <> 'Split' then m.location
            else d.primary_cost_center
        end as cost_center_code,
        coalesce(m.allocation, d.locations) as allocation
    from {{ ref('int_ap_documents') }} as d
    left join {{ ref('int_ap_matches') }} as m on m.matched_doc_id = d.doc_id
    left join (select distinct doc_id from {{ ref('int_ap_candidates') }}) as c on c.doc_id = d.doc_id
),

platform_only as (
    select
        'pb:' || platform_bill_id as ap_bill_key,
        'platform_only' as source,
        platform_bill_id,
        cast(null as varchar) as doc_id,
        vendor_key,
        bill_date,
        due_date,
        paid_date,
        amount,
        gl_code,
        case when location <> 'Split' then location end as cost_center_code,
        allocation
    from {{ ref('int_ap_matches') }}
    where match_status = 'platform_only'
)

select * from documents
union all
select * from platform_only
