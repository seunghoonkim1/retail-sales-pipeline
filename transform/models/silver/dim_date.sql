-- One row per calendar day, covering every date in the source calendars.
with bounds as (
    select
        min(date_day) as first_day,
        max(date_day) as last_day
    from {{ ref('stg_m5__calendar') }}
),

days as (
    select cast(unnest(generate_series(first_day, last_day, interval 1 day)) as date) as date_day
    from bounds
)

select
    date_day,
    dayname(date_day) as day_of_week,
    year(date_day) as calendar_year,
    month(date_day) as calendar_month
from days