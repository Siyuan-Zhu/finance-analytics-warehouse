select as_of, bucket_order, bucket, bill_count, open_amount
from marts.rpt_ap_aging
order by as_of, bucket_order
