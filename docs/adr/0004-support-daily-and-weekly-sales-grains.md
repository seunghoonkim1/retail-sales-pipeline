# 4. Support daily and weekly sales grains in silver

Date: 2026-10-12

## Status

Accepted. Supersedes in part [ADR 0002](0002-use-m5-data-replayed-weekly.md).

## Context

ADR 0002 decided that silver stores sales only at item × fiscal week grain, keeping M5's daily detail in bronze.

Sales sources differ in detail. Some channels report only weekly totals; others provide daily sales, often delivered in a weekly file. Daily detail supports analysis that weekly totals cannot, such as weekday patterns. Mixing daily and weekly rows in one table would make sums unreliable.

## Decision

- Silver has two sales facts: `fct_sales_daily` for sources that provide daily data, and `fct_sales_weekly` for every source.
- Weekly sources load directly into `fct_sales_weekly`. Daily sources load into `fct_sales_daily` and are rolled up into `fct_sales_weekly` using the channel's fiscal calendar.
- Weekly totals are never split into days.
- The M5 replay still delivers one file per Walmart week; each file contains daily rows.

The rest of ADR 0002 still applies: M5 is the v1 data source, delivered as weekly files.

## Consequences

Positive:
- Every channel can be reported together at weekly grain.
- Daily analysis is available for channels that provide daily data.
- A reconciliation test confirms that weekly totals for daily sources equal the sum of their daily rows.

Negative:
- Two sales tables to build and test instead of one.
- Cross-channel daily analysis is only possible for channels that provide daily data.