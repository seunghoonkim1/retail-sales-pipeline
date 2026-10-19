-- One row per day per fiscal calendar. Currently one calendar: Walmart, from M5.
-- Only complete weeks are kept; the M5 calendar file ends partway through a week.
with walmart as (
    select
        'walmart' as calendar_name,
        date_day,
        fiscal_year,
        fiscal_week
    from {{ ref('stg_m5__calendar') }}
),

with_week_dates as (
    select
        *,
        min(date_day) over (partition by calendar_name, fiscal_year, fiscal_week) as week_start_date,
        max(date_day) over (partition by calendar_name, fiscal_year, fiscal_week) as week_end_date,
        count(*) over (partition by calendar_name, fiscal_year, fiscal_week) as days_in_week
    from walmart
),

-- Walmart uses a 4-5-4 calendar: each 13-week quarter has months of 4, 5, and 4 weeks.
-- In a 53-week year, week 53 is assumed to belong to fiscal month 12.
with_quarters as (
    select
        *,
        least((fiscal_week - 1) // 13, 3) as quarter_index
    from with_week_dates
    where days_in_week = 7
)

select
    calendar_name,
    date_day,
    fiscal_year,
    quarter_index * 3
        + case
            when fiscal_week - 1 - 13 * quarter_index < 4 then 1
            when fiscal_week - 1 - 13 * quarter_index < 9 then 2
            else 3
        end as fiscal_month,
    fiscal_week,
    fiscal_year * 100 + fiscal_week as fiscal_year_week,
    dense_rank() over (partition by calendar_name order by week_start_date) as week_index,
    week_start_date,
    week_end_date,
    -- a week belongs to the calendar month containing its end date
    year(week_end_date) as week_calendar_year,
    month(week_end_date) as week_calendar_month
from with_quarters