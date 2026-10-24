select platform_bill_id, vendor_name, bill_date, amount, note, candidate_docs
from marts.rpt_ap_reconciliation
where status = 'ambiguous'
order by bill_date
