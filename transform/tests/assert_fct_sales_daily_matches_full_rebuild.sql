-- The incrementally built fact table must equal a full rebuild from bronze.
-- int_m5__sales_daily is a view, so it always reflects all of bronze.
-- Returns rows found in only one of the two; loaded_at is excluded, since it
-- legitimately differs between runs.
with fact as (
    select channel, channel_item_id, date_day, pos_units, pos_sales_usd
    from {{ ref('fct_sales_daily') }}
),

full_rebuild as (
    select
        channel,
        channel_item_id,
        date_day,
        pos_units,
        cast(pos_sales_usd as decimal(12, 2)) as pos_sales_usd
    from {{ ref('int_m5__sales_daily') }}
    where date_day in (select date_day from {{ ref('dim_fiscal_calendar') }})
),

only_in_fact as (
    select * from fact
    except
    select * from full_rebuild
),

only_in_rebuild as (
    select * from full_rebuild
    except
    select * from fact
)

select 'only_in_fact' as found_in, * from only_in_fact
union all
select 'only_in_rebuild' as found_in, * from only_in_rebuild