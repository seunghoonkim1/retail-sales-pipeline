-- week_index increases by exactly 1 from each week to the next. Returns any jumps.
with ordered as (
    select
        calendar_name,
        fiscal_year_week,
        week_index,
        lag(week_index) over (partition by calendar_name order by week_start_date) as previous_week_index
    from {{ ref('dim_fiscal_week') }}
)

select *
from ordered
where previous_week_index is not null
  and week_index <> previous_week_index + 1