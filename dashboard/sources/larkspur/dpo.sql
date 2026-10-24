select month_start, as_of, open_amount, bills_90d, dpo, avg_days_to_pay, share_paid_late, bills_paid
from marts.rpt_dpo
order by month_start
