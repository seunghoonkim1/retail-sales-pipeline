-- Monthly sales per channel item and SKU. Each week belongs to the calendar month
-- containing its end date, matching existing reports.
-- U/S/W for the month is units / store-weeks: never an average of weekly U/S/W.
-- Grain: one row per channel, channel item, SKU, and calendar month.
select
    channel,
    channel_name,
    channel_item_id,
    sku,
    product_name,
    brand,
    category,
    product_status,
    week_calendar_year as calendar_year,
    week_calendar_month as calendar_month,
    count(*) as weeks_in_month,
    sum(pos_units) as pos_units,
    case
        when bool_or(pos_sales_usd is null) then null
        else sum(pos_sales_usd)
    end as pos_sales_usd,
    sum(stores_carrying) as store_weeks_carrying,
    round(sum(pos_units) / nullif(sum(stores_carrying), 0), 2) as units_per_store_per_week
from {{ ref('mart_sales_weekly_sku') }}
group by all