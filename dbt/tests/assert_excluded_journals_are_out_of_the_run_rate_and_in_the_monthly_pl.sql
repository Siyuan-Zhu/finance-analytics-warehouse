-- For every line: run rate x months = what the ledger says over the window without the excluded journals,
-- and the excluded journals are still present in the monthly report.
with window_months as (
    select month_start from {{ ref('int_month_status') }} where is_closed
    order by month_start desc limit {{ var('run_rate_window_months') }}
),

expected as (
    select reporting_line_key, sum(reporting_amount) as total
    from {{ ref('int_gl_mapped') }}
    where month_start in (select month_start from window_months)
        and coalesce(reference, '') not in (select reference from {{ ref('excluded_journals') }})
    group by reporting_line_key
),

run_rate_problems as (
    select r.reporting_line_key, 'run rate differs from ledger without excluded journals' as problem
    from {{ ref('rpt_run_rate') }} as r
    left join expected as e on e.reporting_line_key = r.reporting_line_key
    where abs(r.window_total - coalesce(e.total, 0)) > 0.01
),

report_problems as (
    select 'all' as reporting_line_key, 'excluded journal missing from monthly report' as problem
    from (
        select
            (select coalesce(sum(reporting_amount), 0) from {{ ref('int_gl_mapped') }}
                where reference in (select reference from {{ ref('excluded_journals') }})) as ledger_total,
            (select coalesce(sum(excluded_amount), 0) from {{ ref('rpt_monthly_pl') }}) as report_total
    )
    where abs(ledger_total - report_total) > 0.01
)

select * from run_rate_problems
union all
select * from report_problems
