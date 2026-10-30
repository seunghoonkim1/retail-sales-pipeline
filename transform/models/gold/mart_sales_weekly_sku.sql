-- Weekly sales per channel item, with SKU, product, channel, and calendar details,
-- store counts, and U/S/W. Built from the daily mart, so each day's sales already
-- use the mapping valid on that day.
-- Grain: one row per channel, channel item, SKU, and fiscal week.
with daily as (
    select * from {{ ref('mart_sales_daily_sku') }}
),

channels as (
    select * from {{ ref('dim_channel') }}
),

weeks as (
    select * from {{ ref('dim_fiscal_week') }}
),

store_counts as (
    select * from {{ ref('fct_sales_weekly') }}
),

rolled_up as (
    select
        channel,
        channel_name,
        channel_item_id,
        sku,
        product_name,
        brand,
        category,
        product_status,
        fiscal_year_week,
        sum(pos_units) as pos_units,
        case
            when bool_or(pos_sales_usd is null) then null
            else sum(pos_sales_usd)
        end as pos_sales_usd
    from daily
    group by all
)

select
    rolled_up.channel,
    rolled_up.channel_name,
    rolled_up.channel_item_id,
    rolled_up.sku,
    rolled_up.product_name,
    rolled_up.brand,
    rolled_up.category,
    rolled_up.product_status,
    weeks.fiscal_year,
    weeks.fiscal_month,
    weeks.fiscal_week,
    weeks.fiscal_year_week,
    weeks.week_start_date,
    weeks.week_end_date,
    weeks.week_calendar_year,
    weeks.week_calendar_month,
    rolled_up.pos_units,
    rolled_up.pos_sales_usd,
    store_counts.stores_carrying,
    store_counts.stores_selling,
    round(rolled_up.pos_units / nullif(store_counts.stores_carrying, 0), 2) as units_per_store_per_week
from rolled_up
join channels
    on rolled_up.channel = channels.channel
join weeks
    on weeks.calendar_name = channels.calendar_name
    and weeks.fiscal_year_week = rolled_up.fiscal_year_week
left join store_counts
    on store_counts.channel = rolled_up.channel
    and store_counts.channel_item_id = rolled_up.channel_item_id
    and store_counts.week_start_date = weeks.week_start_date