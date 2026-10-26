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
    channel,
    channel_item_id,
    fiscal_year,
    fiscal_week,
    week_start_date,
    pos_units,
    cast(pos_sales_usd as decimal(12, 2)) as pos_sales_usd,
    cast(null as integer) as store_count,
    'daily' as source_grain,
    source_system,
    source_file,
    source_file_version,
    current_timestamp as loaded_at
from rolled_up