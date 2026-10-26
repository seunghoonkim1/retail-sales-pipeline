-- A channel item never maps to two SKUs at the same time.
-- Returns pairs of periods for the same item that overlap.
select
    a.channel,
    a.channel_item_id,
    a.sku as first_sku,
    a.valid_from as first_from,
    a.valid_to as first_to,
    b.sku as second_sku,
    b.valid_from as second_from
from {{ ref('map_channel_item') }} as a
join {{ ref('map_channel_item') }} as b
    on a.channel = b.channel
    and a.channel_item_id = b.channel_item_id
    and a.valid_from < b.valid_from
where coalesce(a.valid_to, date '9999-12-31') >= b.valid_from