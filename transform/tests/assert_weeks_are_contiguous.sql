-- Each week starts the day after the previous week ends: no gaps or overlaps.
with ordered as (
    select
        calendar_name,
        fiscal_year_week,
        week_start_date,
        lag(week_end_date) over (partition by calendar_name order by week_start_date) as previous_week_end
    from {{ ref('dim_fiscal_week') }}
)

select *
from ordered
where previous_week_end is not null
  and week_start_date <> previous_week_end + 1