-- Daily sales per channel item, with SKU, product, channel, and calendar details
-- joined in. Each day's sales use the item mapping valid on that day.
-- Grain: one row per channel, channel item, and day.
with sales as (
    select * from {{ ref('fct_sales_daily') }}
),

item_map as (
    select * from {{ ref('map_channel_item') }}
),

products as (
    select * from {{ ref('dim_product') }}
),

channels as (
    select * from {{ ref('dim_channel') }}
),

dates as (
    select * from {{ ref('dim_date') }}
),

fiscal_days as (
    select * from {{ ref('dim_fiscal_calendar') }}
)

select
    sales.channel,
    channels.channel_name,
    sales.channel_item_id,
    item_map.sku,
    products.product_name,
    products.brand,
    products.category,
    products.status as product_status,
    sales.date_day,
    dates.day_of_week,
    dates.calendar_year,
    dates.calendar_month,
    fiscal_days.fiscal_year,
    fiscal_days.fiscal_month,
    fiscal_days.fiscal_week,
    fiscal_days.fiscal_year_week,
    sales.pos_units,
    sales.pos_sales_usd
from sales
join channels
    on sales.channel = channels.channel
join dates
    on sales.date_day = dates.date_day
join fiscal_days
    on fiscal_days.calendar_name = channels.calendar_name
    and fiscal_days.date_day = sales.date_day
left join item_map
    on item_map.channel = sales.channel
    and item_map.channel_item_id = sales.channel_item_id
    and sales.date_day between item_map.valid_from and coalesce(item_map.valid_to, date '9999-12-31')
left join products
    on products.sku = item_map.sku