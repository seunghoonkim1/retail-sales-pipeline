# Silver layer data contract

Silver holds cleaned, standardized data in one format, regardless of source. Each source has its own staging model that maps into these tables. Nothing downstream should need to know which source a row came from.

## Conventions

- Names are `snake_case`.
- All identifiers (item numbers, SKUs, UPCs) are text, never numbers, to preserve leading zeros.
- Raw files are read with every column as text; each column is converted deliberately in staging.
- Money columns are `decimal(12,2)` and end in `_usd`.
- Dates are `date`; timestamps are UTC.
- Facts carry lineage columns: `source_system`, `source_file`, `source_file_version`, `loaded_at`.
- Derived metrics (for example U/S/W) are calculated in gold, not stored in silver.

## dim_channel

One row per sales channel.

| Column | Type | Null | Description |
|---|---|---|---|
| channel | text | no | Channel code, e.g. `walmart` |
| channel_name | text | no | Display name |
| calendar_name | text | no | Fiscal calendar this channel reports in |

Key: `channel`. Source: dbt seed.

## dim_date

One row per calendar day.

| Column | Type | Null | Description |
|---|---|---|---|
| date_day | date | no | The date |
| day_of_week | text | no | Day name, e.g. `Saturday` |
| calendar_year | integer | no | Calendar year |
| calendar_month | integer | no | Calendar month (1–12) |

Key: `date_day`. Source: generated.

## dim_fiscal_calendar

One row per day per fiscal calendar.

| Column | Type | Null | Description |
|---|---|---|---|
| calendar_name | text | no | e.g. `walmart` |
| date_day | date | no | The date |
| fiscal_year | integer | no | Fiscal year |
| fiscal_month | integer | no | Fiscal month. M5: derived using Walmart's 4-5-4 pattern; week 53 assumed in month 12 |
| fiscal_week | integer | no | Fiscal week (1–53) |
| fiscal_year_week | integer | no | Year and week as `YYYYWW`, e.g. `202633` |
| week_index | integer | no | Continuous week number across years; never resets |
| week_start_date | date | no | First day of the fiscal week |
| week_end_date | date | no | Last day of the fiscal week |
| week_calendar_year | integer | no | Calendar year of the week's end date |
| week_calendar_month | integer | no | Calendar month of the week's end date |

Key: `calendar_name` + `date_day`. Source: official calendar files (M5 `calendar.csv` for Walmart).

Tests:
- Every fiscal week has exactly 7 days.
- `week_end_date` is 6 days after `week_start_date`.
- `week_index` increases by exactly 1 from each week to the next.

## dim_fiscal_week

One row per fiscal week per calendar. Derived from `dim_fiscal_calendar`; never maintained by hand.

| Column | Type | Null | Description |
|---|---|---|---|
| calendar_name | text | no | e.g. `walmart` |
| fiscal_year_week | integer | no | `YYYYWW` |
| fiscal_year | integer | no | Fiscal year |
| fiscal_month | integer | no | Fiscal month. M5: derived using Walmart's 4-5-4 pattern; week 53 assumed in month 12 |
| fiscal_week | integer | no | Fiscal week |
| week_index | integer | no | Continuous week number |
| week_start_date | date | no | First day of the week |
| week_end_date | date | no | Last day of the week |
| week_calendar_year | integer | no | Calendar year of the week's end date |
| week_calendar_month | integer | no | Calendar month of the week's end date |

Key: `calendar_name` + `fiscal_year_week`.

## dim_product

One row per SKU, current values.

| Column | Type | Null | Description |
|---|---|---|---|
| sku | text | no | Internal product identifier |
| product_name | text | no | Product description |
| brand | text | yes | Brand |
| category | text | yes | Product category |
| upc | text | yes | UPC barcode |
| status | text | no | e.g. `active`, `discontinued` |

Key: `sku`. History: SCD1 (bronze keeps every source version).

## map_channel_item

One row per channel item per validity period. Maps channel item IDs to SKUs over time.

| Column | Type | Null | Description |
|---|---|---|---|
| channel | text | no | Links to `dim_channel` |
| channel_item_id | text | no | The channel's item ID |
| sku | text | no | Links to `dim_product` |
| prime_item_id | text | yes | Channel's grouping of item variants |
| vendor_stock_id | text | yes | Supplier stock ID used with this channel |
| valid_from | date | no | First day this mapping applies: the item master's effective date when given, otherwise the snapshot date |
| valid_to | date | yes | Last day it applies; empty means current |
| is_current | boolean | no | True for the active mapping |

Key: `channel` + `channel_item_id` + `valid_from`. History: SCD2, rebuilt from dated source versions in bronze.

Tests:
- No overlapping validity periods for the same `channel` + `channel_item_id`.
- Every `sku` exists in `dim_product`.

## fct_sales_daily

One row per channel item per day, summed across all stores. Only for sources that provide daily data.

| Column | Type | Null | Description |
|---|---|---|---|
| channel | text | no | Links to `dim_channel` |
| channel_item_id | text | no | Channel's item ID, as reported |
| date_day | date | no | Sales date |
| pos_units | integer | no | Units sold; may be negative |
| pos_sales_usd | decimal(12,2) | yes | Retail sales value. 0 when units are 0 and no price exists; empty when units were sold but the price is unknown |
| source_system | text | no | e.g. `m5` |
| source_file | text | no | Original file name |
| source_file_version | text | yes | S3 version ID of the bronze file; empty when loaded from local files |
| loaded_at | timestamp | no | Load time (UTC) |

Key: `channel` + `channel_item_id` + `date_day`.
Tests:
- Units sold with no known price (empty pos_sales_usd): warning, not failure.

## fct_sales_weekly

One row per channel item per fiscal week, summed across all stores.

| Column | Type | Null | Description |
|---|---|---|---|
| channel | text | no | Links to `dim_channel` |
| channel_item_id | text | no | Channel's item ID, as reported |
| fiscal_year | integer | no | Fiscal year in the channel's calendar |
| fiscal_week | integer | no | Fiscal week in the channel's calendar |
| week_start_date | date | no | First day of the fiscal week |
| pos_units | integer | no | Units sold at point of sale; may be negative when returns exceed sales |
| pos_sales_usd | decimal(12,2) | yes | Retail sales value. 0 when units are 0 and no price exists; empty when units were sold but the price is unknown |
| store_count | integer | yes | Stores with sales, if the source provides it |
| source_system | text | no | e.g. `m5` |
| source_file | text | no | Original file name |
| source_file_version | text | yes | S3 version ID of the bronze file; empty when loaded from local files |
| loaded_at | timestamp | no | Load time (UTC) |
| source_grain | text | no | `weekly` if loaded directly, `daily` if rolled up from fct_sales_daily |

Key: `channel` + `channel_item_id` + `week_start_date`.

Loading: each load replaces all rows for the fiscal week it contains, so reloading a corrected file never creates duplicates.

Tests:
- Key is unique.
- `week_start_date` matches the channel's fiscal calendar.
- Negative `pos_units`: warning, not failure.
- Items with no SKU mapping for that week: warning, not failure.
- For daily sources, each week's totals equal the sum of that week's rows in fct_sales_daily.

SKUs are not stored here. Gold joins `channel_item_id` to `map_channel_item` using the mapping valid in that week.

## Notes on sources

- M5: `pos_sales_usd` is calculated as units × weekly price, not reported, so it is an approximation.
- M5: product names, prime item IDs, and vendor stock IDs are synthetic.
- M5: wm_yr_wk names the Walmart year by the calendar year it starts in. Staging converts it to Walmart's official fiscal year, named by the year it ends in ('11101' = fiscal year 2012, week 1).
- Item master: synthetic, generated as full snapshots on three dates. dim_product keeps each SKU's last known values. A channel item removed from the item master entirely is not closed in map_channel_item; this is a known limitation.