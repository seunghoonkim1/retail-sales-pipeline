select
    cast(snapshot_date as date) as snapshot_date,
    channel,
    channel_item_id,
    sku,
    prime_item_id,
    vendor_stock_id,
    -- empty in the file means "no effective date given"
    cast(nullif(effective_date, '') as date) as effective_date,
    filename as source_file
from {{ source('m5', 'item_master_channel_items') }}