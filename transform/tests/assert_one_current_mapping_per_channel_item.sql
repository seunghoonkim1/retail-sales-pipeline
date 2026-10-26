-- Every channel item has exactly one current mapping.
select
    channel,
    channel_item_id,
    count(*) filter (where is_current) as current_mappings
from {{ ref('map_channel_item') }}
group by channel, channel_item_id
having count(*) filter (where is_current) <> 1