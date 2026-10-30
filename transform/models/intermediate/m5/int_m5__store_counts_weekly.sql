-- Stores per M5 item per Walmart week:
--   carrying: stores with a price that week (M5 lists prices only while an item is on sale)
--   selling:  stores that sold at least one unit that week
with weeks as (
    select distinct wm_yr_wk, fiscal_year, fiscal_week
    from {{ ref('stg_m5__calendar') }}
),

carrying as (
    select
        channel_item_id,
        wm_yr_wk,
        count(distinct store_id) as stores_carrying
    from {{ ref('stg_m5__prices') }}
    group by channel_item_id, wm_yr_wk
),

selling as (
    select
        channel_item_id,
        wm_yr_wk,
        count(distinct store_id) as stores_selling
    from {{ ref('stg_m5__sales') }}
    where units > 0
    group by channel_item_id, wm_yr_wk
)

select
    'walmart' as channel,
    carrying.channel_item_id,
    weeks.fiscal_year,
    weeks.fiscal_week,
    carrying.stores_carrying,
    coalesce(selling.stores_selling, 0) as stores_selling
from carrying
join weeks using (wm_yr_wk)
left join selling using (channel_item_id, wm_yr_wk)