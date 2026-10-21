-- One row per channel item per day, from every source that provides daily sales.
-- Currently one source: M5.
with combined as (
    select * from {{ ref('int_m5__sales_daily') }}
)

select
    channel,
    channel_item_id,
    date_day,
    pos_units,
    cast(pos_sales_usd as decimal(12, 2)) as pos_sales_usd,
    source_system,
    source_file,
    source_file_version,
    current_timestamp as loaded_at
from combined