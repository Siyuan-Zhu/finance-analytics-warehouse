-- One row: how the naive total (platform + accounting) turns into the de-duplicated total.
select
    (select coalesce(sum(amount), 0) from {{ ref('stg_platform_bills') }}) as platform_total,
    (select coalesce(sum(amount), 0) from {{ ref('stg_ap_bill_lines') }}) as accounting_total,
    (select coalesce(sum(amount), 0) from {{ ref('rpt_ap_reconciliation') }} where status = 'matched') as matched_total,
    (select coalesce(sum(amount), 0) from {{ ref('rpt_ap_reconciliation') }} where status = 'ambiguous') as held_out_total,
    (select coalesce(sum(amount), 0) from {{ ref('fct_ap_bills') }}) as deduplicated_total,
    (select count(*) from {{ ref('rpt_ap_reconciliation') }} where status = 'matched') as matched_count,
    (select count(*) from {{ ref('rpt_ap_reconciliation') }} where status = 'platform_only') as platform_only_count,
    (select count(*) from {{ ref('rpt_ap_reconciliation') }} where status = 'accounting_only') as accounting_only_count,
    (select count(*) from {{ ref('rpt_ap_reconciliation') }} where status = 'ambiguous') as ambiguous_count
