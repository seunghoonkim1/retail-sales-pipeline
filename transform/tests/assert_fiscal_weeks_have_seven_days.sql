-- Every fiscal week has exactly 7 days. Returns weeks that don't.
select
    calendar_name,
    fiscal_year_week,
    count(*) as days_in_week
from {{ ref('dim_fiscal_calendar') }}
group by calendar_name, fiscal_year_week
having count(*) <> 7