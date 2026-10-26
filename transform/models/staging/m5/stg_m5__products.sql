select
    cast(snapshot_date as date) as snapshot_date,
    sku,
    product_name,
    brand,
    category,
    upc,
    status,
    filename as source_file
from {{ source('m5', 'item_master_products') }}