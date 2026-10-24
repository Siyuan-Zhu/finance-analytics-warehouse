-- Accounting-system bill lines collapsed to one row per document.
with lines as (
    select * from {{ ref('stg_ap_bill_lines') }}
),

totals as (
    select
        doc_id,
        min(vendor_name) as vendor_name,
        min(vendor_key) as vendor_key,
        min(bill_date) as bill_date,
        min(due_date) as due_date,
        min(paid_date) as paid_date,
        sum(amount) as amount,
        count(*) as line_count
    from lines
    group by doc_id
),

primary_code as (
    select doc_id, gl_code as primary_gl_code
    from lines
    where gl_code is not null
    qualify row_number() over (partition by doc_id order by abs(amount) desc, gl_code) = 1
),

primary_cost_center as (
    select doc_id, location as primary_cost_center
    from lines
    where location is not null and location <> 'Split'
    qualify row_number() over (partition by doc_id order by abs(amount) desc, location) = 1
),

locations as (
    select doc_id, string_agg(distinct location, '+' order by location) as locations
    from lines
    where location is not null and location <> 'Split'
    group by doc_id
)

select t.*, c.primary_gl_code, p.primary_cost_center, l.locations
from totals as t
left join primary_code as c using (doc_id)
left join primary_cost_center as p using (doc_id)
left join locations as l using (doc_id)
