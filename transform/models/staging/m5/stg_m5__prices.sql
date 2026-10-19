select
    item_id as channel_item_id,
    store_id,
    wm_yr_wk,
    cast(sell_price as decimal(12, 2)) as sell_price_usd,
    filename as source_file
from {{ source('m5', 'prices') }}