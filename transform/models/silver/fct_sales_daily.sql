-- depends_on: {{ ref('stg_m5__calendar') }}
-- One row per channel item per day, from every source that provides daily sales.
-- Currently one source: M5.
--
-- Incremental (ADR 0006, ADR 0007): whole days are replaced (delete+insert on
-- channel + date_day), and only the selected source partitions' bronze files are read.
--   dbt build --vars '{partitions: {m5: ["11452"]}}'   reprocesses those M5 partitions
--   dbt build                                          reprocesses the partitions covering
--                                                      the last 4 loaded weeks, plus newer
--   dbt build --full-refresh                           rebuilds everything from bronze
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['channel', 'date_day'],
    )
}}

{% set partitions = var('partitions', {}) %}

{# Lookback: when no partitions are named, find the M5 partitions covering the last
   4 loaded weeks, plus any newer weeks in the calendar, so the query below still
   receives literal values it can prune on. #}
{% if is_incremental() and not partitions and execute %}
    {% set lookback_query %}
        select distinct wm_yr_wk
        from {{ ref('stg_m5__calendar') }}
        where date_day > (select max(date_day) - interval 28 day from {{ this }})
        order by wm_yr_wk
    {% endset %}
    {% set partitions = {'m5': run_query(lookback_query).columns[0].values() | list} %}
{% endif %}

with combined as (
    select *
    from {{ ref('int_m5__sales_daily') }}
    {% if is_incremental() %}
        {% if partitions.get('m5') %}
            -- literal partition keys, so DuckDB reads only these bronze folders
            where source_partition in ('{{ partitions['m5'] | join("', '") }}')
        {% else %}
            -- incremental, but no M5 partitions to process in this run
            where false
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
    source_partition,
    source_file_version,
    current_timestamp as loaded_at
from combined