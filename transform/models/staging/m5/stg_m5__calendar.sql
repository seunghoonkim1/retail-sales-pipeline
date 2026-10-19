select
    cast(date as date) as date_day,
    weekday as day_of_week,
    wm_yr_wk,
    -- wm_yr_wk is 1 + YY + WW: '11101' = Walmart year 2011, week 1
    2000 + cast(substr(wm_yr_wk, 2, 2) as integer) as fiscal_year,
    cast(substr(wm_yr_wk, 4, 2) as integer) as fiscal_week,
    d as day_code
from {{ source('m5', 'calendar') }}