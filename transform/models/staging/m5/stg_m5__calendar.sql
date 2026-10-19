select
    cast(date as date) as date_day,
    weekday as day_of_week,
    wm_yr_wk,
    -- wm_yr_wk is C + YY + WW: century digit (1 = 2000s, 0 = 1900s), year, week.
    -- The year is the calendar year the Walmart year starts in. Walmart's official
    -- fiscal year is named for the year it ends in, one later:
    -- '11101' (week starting 2011-01-29) is fiscal year 2012, week 1.
    1901
        + 100 * cast(substr(wm_yr_wk, 1, 1) as integer)
        + cast(substr(wm_yr_wk, 2, 2) as integer) as fiscal_year,
    cast(substr(wm_yr_wk, 4, 2) as integer) as fiscal_week,
    d as day_code
from {{ source('m5', 'calendar') }}