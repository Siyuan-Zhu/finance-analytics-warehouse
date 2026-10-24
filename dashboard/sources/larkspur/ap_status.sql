select status, count(*) as bills, sum(amount) as amount
from marts.rpt_ap_reconciliation
group by status
order by case status when 'matched' then 1 when 'platform_only' then 2 when 'accounting_only' then 3 else 4 end
