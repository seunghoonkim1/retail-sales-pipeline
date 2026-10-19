-- One row per fiscal week per calendar, derived from dim_fiscal_calendar.
select distinct
    calendar_name,
    fiscal_year_week,
    fiscal_year,
    fiscal_month,
    fiscal_week,
    week_index,
    week_start_date,
    week_end_date,
    week_calendar_year,
    week_calendar_month
from {{ ref('dim_fiscal_calendar') }}