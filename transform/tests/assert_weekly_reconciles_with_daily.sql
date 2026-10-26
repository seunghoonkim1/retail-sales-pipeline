-- For daily sources, each week's totals equal the sum of that week's daily rows.
-- Returns weeks where they differ, or that exist on only one side.
with daily_totals as (
    select
        daily.channel,
        daily.channel_item_id,
        calendar.week_start_date,
        sum(daily.pos_units) as pos_units,
        sum(daily.pos_sales_usd) as pos_sales_usd
    from {{ ref('fct_sales_daily') }} as daily
    join {{ ref('dim_channel') }} as channels
        on daily.channel = channels.channel
    join {{ ref('dim_fiscal_calendar') }} as calendar
        on calendar.calendar_name = channels.calendar_name
        and calendar.date_day = daily.date_day
    group by daily.channel, daily.channel_item_id, calendar.week_start_date
),

weekly as (
    select channel, channel_item_id, week_start_date, pos_units, pos_sales_usd
    from {{ ref('fct_sales_weekly') }}
    where source_grain = 'daily'
)

select
    coalesce(weekly.channel, daily_totals.channel) as channel,
    coalesce(weekly.channel_item_id, daily_totals.channel_item_id) as channel_item_id,
    coalesce(weekly.week_start_date, daily_totals.week_start_date) as week_start_date,
    weekly.pos_units as weekly_units,
    daily_totals.pos_units as daily_units,
    weekly.pos_sales_usd as weekly_sales,
    daily_totals.pos_sales_usd as daily_sales
from weekly
full outer join daily_totals
    on weekly.channel = daily_totals.channel
    and weekly.channel_item_id = daily_totals.channel_item_id
    and weekly.week_start_date = daily_totals.week_start_date
where weekly.pos_units is distinct from daily_totals.pos_units
   or weekly.pos_sales_usd is distinct from daily_totals.pos_sales_usd