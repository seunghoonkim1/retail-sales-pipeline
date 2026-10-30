-- Total units in every gold mart equal total units in silver.
with totals as (
    select 'fct_sales_daily' as source, sum(pos_units) as units from {{ ref('fct_sales_daily') }}
    union all
    select 'mart_sales_daily_sku', sum(pos_units) from {{ ref('mart_sales_daily_sku') }}
    union all
    select 'mart_sales_weekly_sku', sum(pos_units) from {{ ref('mart_sales_weekly_sku') }}
    union all
    select 'mart_sales_monthly_sku', sum(pos_units) from {{ ref('mart_sales_monthly_sku') }}
)

select *
from totals
where units <> (select units from totals where source = 'fct_sales_daily')