-- depends_on: {{ ref('dim_fiscal_calendar') }}
-- One row per channel item per day, from every source that provides daily sales.
-- Currently one source: M5.
--
-- Incremental: whole days are replaced (delete+insert on channel + date_day).
--   dbt build --vars '{fiscal_year_weeks: [201205, 201206]}'  reprocesses those weeks
--   dbt build                                                  adds only dates newer than the table's latest
--   dbt build --full-refresh                                   rebuilds everything from bronze
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['channel', 'date_day'],
    )
}}

{% set fiscal_year_weeks = var('fiscal_year_weeks', []) %}

with combined as (
    select * from {{ ref('int_m5__sales_daily') }}
),

selected as (
    select *
    from combined
    {% if is_incremental() %}
        {% if fiscal_year_weeks %}
        where date_day in (
            select date_day
            from {{ ref('dim_fiscal_calendar') }}
            where calendar_name = 'walmart'
              and fiscal_year_week in ({{ fiscal_year_weeks | join(', ') }})
        )
        {% else %}
        -- No weeks named: reprocess the last 4 weeks already loaded, plus anything newer,
        -- so recent corrections are picked up, not only new dates.
        where date_day > (select max(date_day) - interval 28 day from {{ this }})
        {% endif %}
    {% endif %}
)

select
    channel,
    channel_item_id,
    date_day,
    pos_units,
    cast(pos_sales_usd as decimal(12, 2)) as pos_sales_usd,
    source_system,
    source_file,
    source_file_version,
    current_timestamp as loaded_at
from selected