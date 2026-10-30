-- One row per channel item per fiscal week, for every source.
-- Daily sources are rolled up from fct_sales_daily using each channel's fiscal calendar.
-- Sources that only provide weekly data will be added here directly (none yet).
with daily as (
    select * from {{ ref('fct_sales_daily') }}
),

channels as (
    select * from {{ ref('dim_channel') }}
),

calendar as (
    select * from {{ ref('dim_fiscal_calendar') }}
),

store_counts as (
    select * from {{ ref('int_m5__store_counts_weekly') }}
),

rolled_up as (
    select
        daily.channel,
        daily.channel_item_id,
        calendar.fiscal_year,
        calendar.fiscal_week,
        calendar.week_start_date,
        sum(daily.pos_units) as pos_units,
        -- unknown for the week if any day's sales dollars are unknown
        case
            when bool_or(daily.pos_sales_usd is null) then null
            else sum(daily.pos_sales_usd)
        end as pos_sales_usd,
        any_value(daily.source_system) as source_system,
        any_value(daily.source_file) as source_file,
        any_value(daily.source_file_version) as source_file_version
    from daily
    join channels
        on daily.channel = channels.channel
    join calendar
        on calendar.calendar_name = channels.calendar_name
        and calendar.date_day = daily.date_day
    group by
        daily.channel,
        daily.channel_item_id,
        calendar.fiscal_year,
        calendar.fiscal_week,
        calendar.week_start_date
)

select
    rolled_up.channel,
    rolled_up.channel_item_id,
    rolled_up.fiscal_year,
    rolled_up.fiscal_week,
    rolled_up.week_start_date,
    rolled_up.pos_units,
    cast(rolled_up.pos_sales_usd as decimal(12, 2)) as pos_sales_usd,
    store_counts.stores_carrying,
    store_counts.stores_selling,
    'daily' as source_grain,
    rolled_up.source_system,
    rolled_up.source_file,
    rolled_up.source_file_version,
    current_timestamp as loaded_at
from rolled_up
left join store_counts
    on rolled_up.channel = store_counts.channel
    and rolled_up.channel_item_id = store_counts.channel_item_id
    and rolled_up.fiscal_year = store_counts.fiscal_year
    and rolled_up.fiscal_week = store_counts.fiscal_week