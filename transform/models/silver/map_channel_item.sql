-- One row per channel item per period its mapping was valid (SCD2),
-- rebuilt from the item master snapshots. A new period starts when the item's
-- SKU, prime item, or vendor stock ID changes. valid_from is the item master's
-- effective date when one is given, otherwise the snapshot date.
with snapshots as (
    select * from {{ ref('stg_m5__channel_items') }}
),

compared as (
    select
        *,
        lag(sku) over item_history as previous_sku,
        lag(prime_item_id) over item_history as previous_prime_item_id,
        lag(vendor_stock_id) over item_history as previous_vendor_stock_id,
        row_number() over item_history as snapshot_number
    from snapshots
    window item_history as (
        partition by channel, channel_item_id
        order by snapshot_date
    )
),

version_starts as (
    select
        channel,
        channel_item_id,
        sku,
        prime_item_id,
        vendor_stock_id,
        coalesce(effective_date, snapshot_date) as valid_from
    from compared
    where snapshot_number = 1
        or sku is distinct from previous_sku
        or prime_item_id is distinct from previous_prime_item_id
        or vendor_stock_id is distinct from previous_vendor_stock_id
),

with_next as (
    select
        *,
        lead(valid_from) over (
            partition by channel, channel_item_id
            order by valid_from
        ) as next_valid_from
    from version_starts
)

select
    channel,
    channel_item_id,
    sku,
    prime_item_id,
    vendor_stock_id,
    valid_from,
    next_valid_from - 1 as valid_to,
    next_valid_from is null as is_current
from with_next