-- Platform bills: matched + platform_only + ambiguous = all of them. Fact rows = documents + platform-only bills.
with c as (
    select
        (select count(*) from {{ ref('stg_platform_bills') }}) as bills,
        (select count(*) from {{ ref('int_ap_matches') }}) as classified,
        (select count(*) from {{ ref('int_ap_documents') }}) as docs,
        (select count(*) from {{ ref('int_ap_matches') }} where match_status = 'platform_only') as platform_only,
        (select count(*) from {{ ref('fct_ap_bills') }}) as fact_rows,
        (select count(*) from {{ ref('rpt_ap_reconciliation') }} where status <> 'accounting_only') as listed_bills
)

select * from c where bills <> classified or fact_rows <> docs + platform_only or listed_bills <> bills
