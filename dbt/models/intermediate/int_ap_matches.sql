-- One row per platform bill: matched to one document, platform-only, or ambiguous (held out).
with per_bill as (
    select platform_bill_id, count(*) as candidate_count, min(doc_id) as only_doc,
        string_agg(doc_id, '|' order by doc_id) as candidate_docs
    from {{ ref('int_ap_candidates') }}
    group by platform_bill_id
),

per_doc as (
    select doc_id, count(*) as claim_count
    from {{ ref('int_ap_candidates') }}
    group by doc_id
),

classified as (
    select
        b.*,
        coalesce(p.candidate_count, 0) as candidate_count,
        p.candidate_docs,
        case
            when coalesce(p.candidate_count, 0) = 0 then 'platform_only'
            when p.candidate_count > 1 then 'ambiguous'
            when d.claim_count > 1 then 'ambiguous'
            else 'matched'
        end as match_status,
        case
            when p.candidate_count > 1 then 'several candidate documents'
            when p.candidate_count = 1 and d.claim_count > 1 then 'document also claimed by another platform bill'
        end as ambiguity_reason,
        case when p.candidate_count = 1 and d.claim_count = 1 then p.only_doc end as matched_doc_id
    from {{ ref('stg_platform_bills') }} as b
    left join per_bill as p on p.platform_bill_id = b.platform_bill_id
    left join per_doc as d on d.doc_id = p.only_doc and p.candidate_count = 1
)

select
    c.*,
    c.gl_code is null and doc.primary_gl_code is not null and c.match_status = 'matched' as gl_backfilled,
    case when c.match_status = 'matched' then coalesce(c.gl_code, doc.primary_gl_code) else c.gl_code end as resolved_gl_code,
    case
        when c.location is null or c.location <> 'Split' then c.location
        when c.match_status = 'matched' and doc.locations is not null then 'ALLOC:' || doc.locations
        else 'ALLOC:UNRESOLVED'
    end as allocation
from classified as c
left join {{ ref('int_ap_documents') }} as doc on doc.doc_id = c.matched_doc_id
