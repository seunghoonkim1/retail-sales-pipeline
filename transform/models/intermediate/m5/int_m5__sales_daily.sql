-- M5 daily sales in the contract's shape: units joined with that week's price,
-- then summed across stores to one row per item per day.
with sales as (
    select * from {{ ref('stg_m5__sales') }}
),

prices as (
    select * from {{ ref('stg_m5__prices') }}
),

priced as (
    select
        sales.channel_item_id,
        sales.date_day,
        sales.units,
        prices.sell_price_usd,
        sales.source_file
    from sales
    left join prices
        on sales.channel_item_id = prices.channel_item_id
        and sales.store_id = prices.store_id
        and sales.wm_yr_wk = prices.wm_yr_wk
)

select
    'walmart' as channel,
    channel_item_id,
    date_day,
    sum(units) as pos_units,
    -- Empty (null) if any store sold units with no known price; otherwise the sum,
    -- where a store with no units and no price contributes 0.
    case
        when bool_or(units > 0 and sell_price_usd is null) then null
        else sum(coalesce(units * sell_price_usd, 0))
    end as pos_sales_usd,
    'm5' as source_system,
    any_value(source_file) as source_file,
    cast(null as varchar) as source_file_version
from priced
group by channel_item_id, date_day