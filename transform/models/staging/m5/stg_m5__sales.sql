select
    item_id as channel_item_id,
    store_id,
    dept_id,
    cat_id,
    state_id,
    cast(date as date) as date_day,
    wm_yr_wk,
    cast(units as integer) as units,
    filename as source_file
from {{ source('m5', 'sales') }}