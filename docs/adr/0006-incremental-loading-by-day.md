# 6. Load sales facts incrementally, replacing whole days

Date: 2026-10-22

## Status

Accepted

## Context

Rebuilding fct_sales_daily from all of bronze takes about two minutes for M5 and grows with history. New data arrives one week at a time, and past weeks can be corrected and re-delivered, so loading must handle both new weeks and replacements without creating duplicates.

## Decision

- fct_sales_daily is a dbt incremental model using the delete+insert strategy, keyed on channel and date_day.
- A run given fiscal_year_weeks reprocesses exactly those weeks, replacing every row for their dates. A run without it reprocesses the last 4 weeks already loaded plus any newer dates, so recent corrections are picked up automatically.
- A full refresh rebuilds the table from bronze at any time and defines the correct result.
- A test checks that the incrementally built table matches a full rebuild.

## Consequences

Positive:
- New and corrected weeks cost one week of processing, not the whole history.
- Reprocessing a week never duplicates rows, and rows missing from a corrected file are removed.

Negative:
- Incremental logic is more complex than a full rebuild, which is why its result is tested against one.
- Corrections older than the 4-week lookback are not picked up automatically: they need their weeks named, or a full refresh. In the cloud version, each delivery triggers processing of its own week, which covers corrections of any age.
- Reading still scans all bronze files; limiting reads to the requested weeks is a separate improvement.