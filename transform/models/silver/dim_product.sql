-- One row per SKU with its latest values (SCD1), from the item master snapshots.
-- A SKU missing from later snapshots keeps its last known values, so older sales
-- of that SKU can still be described.
select
    sku,
    product_name,
    brand,
    category,
    upc,
    status
from {{ ref('stg_m5__products') }}
qualify row_number() over (partition by sku order by snapshot_date desc) = 1