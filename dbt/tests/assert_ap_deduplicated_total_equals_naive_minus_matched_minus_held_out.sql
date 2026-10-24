-- deduplicated = naive (platform + accounting) - platform bills that matched a document - ambiguous platform bills.
with parts as (
    select
        (select coalesce(sum(amount), 0) from {{ ref('stg_platform_bills') }})
            + (select coalesce(sum(amount), 0) from {{ ref('stg_ap_bill_lines') }}) as naive,
        (select coalesce(sum(amount), 0) from {{ ref('int_ap_matches') }} where match_status = 'matched') as matched,
        (select coalesce(sum(amount), 0) from {{ ref('int_ap_matches') }} where match_status = 'ambiguous') as held_out,
        (select coalesce(sum(amount), 0) from {{ ref('fct_ap_bills') }}) as deduplicated
)

select *
from parts
where abs(deduplicated - (naive - matched - held_out)) > 0.01
