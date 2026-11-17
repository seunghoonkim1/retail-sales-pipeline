# 7. Select incremental work by source partition

Date: 2026-11-04

## Status

Accepted. Supersedes in part [ADR 0006](0006-incremental-loading-by-day.md).

## Context

### The problem

fct_sales_daily is incremental (ADR 0006): a run can reprocess chosen weeks and replace them. But measured on M5, reprocessing one week took about as long as rebuilding all history (51 seconds for one week, warm cache). Incremental limited what was written, not what was read: every run still opened all ~277 bronze files.

### Why every file was read

Runs named fiscal weeks (e.g. 201552). The model turned them into dates by looking them up in the calendar, then filtered on the date column. Dates are values inside the files, so DuckDB had to open every file to find them.

### What a spike showed

Selecting one week of bronze sales (213,430 rows) in different ways, second run:

| Selecting by | Time |
|---|---|
| The partition folder key, wm_yr_wk = '11452' | ~0.23 s |
| Listing only that week's file | ~0.22 s |
| The date column inside the files | ~4.7 s |

DuckDB skips whole folders (partition pruning) when the filter is on the folder key with literal values. It cannot prune on values inside the files, or on values produced by another query.

### A second problem: fiscal weeks are ambiguous across sources

A fiscal week only has meaning within one calendar. Week 201552 covers different days for retailers on different calendars. Naming fiscal weeks would select the wrong dates once there is more than one source.

## Options considered

1. **Keep naming fiscal weeks, filter on dates.** Correct for one source, but reads all files, and is ambiguous across calendars.
2. **Hardcode file paths in the models.** Reads only the needed files, but couples the models to storage paths, which differ locally and in the cloud.
3. **Name source partitions; filter on the partition key taken from the folder name.** Reads only the needed files, needs no calendar translation, and keeps paths in the source definitions.

## Decision

Option 3.

- A run names the partitions to process, per source, in the source's own partition key:
  `dbt build --vars '{partitions: {m5: ["11452"]}}'`
  The key is the value in the bronze folder name (wm_yr_wk=11452). In the cloud, the trigger reads the source and key from the arriving file's path.
- The bronze sources declare hive partitioning explicitly, so the folder key becomes a column, kept as text.
- The partition key is carried into fct_sales_daily as the lineage column source_partition.
- Each source's branch in fct_sales_daily filters only on its own partitions, using literal values, so DuckDB reads only those folders.
- When no partitions are named, the lookback is turned into partitions too: the partitions covering the last 4 loaded weeks, plus any newer weeks in the calendar, are looked up while dbt builds the SQL (run_query), so the query still receives literal values and prunes.

The rest of ADR 0006 still applies: delete+insert on channel and date_day, the lookback when no partitions are named, and full refresh as the reference result.

## Consequences

Positive:
- A run for one partition reads only that partition's bronze files, so its cost does not grow with history.
- No calendar translation: a run can never select the wrong dates for another source.
- Paths stay in the source definitions, so local and cloud differ only in the bronze location.

Negative:
- To reprocess by fiscal week by hand, look up the source partition first (e.g. in stg_m5__calendar).
- The lookback relies on the calendar extending past the latest delivered week, so new weeks are known in advance.
- Each new source must expose its own partition key as source_partition.

## Results

Measured after the change, second runs (warm cache), fct_sales_daily model time:

| Run | Before | After |
|---|---|---|
| One named partition (11452) | 51 s | 4.5 s |
| Lookback, 4 partitions | n/a | 8.9 s |

Results remain identical to a full rebuild (assert_fct_sales_daily_matches_full_rebuild passes).