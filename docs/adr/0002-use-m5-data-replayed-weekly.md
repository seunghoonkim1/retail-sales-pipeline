# 2. Use M5 data replayed as weekly files

Date: 2026-10-08

## Status

Accepted

## Context

The pipeline will use the public M5 dataset contains about five years of daily unit sales for roughly 3,000 Walmart products across 10 stores, with weekly prices and a calendar that includes Walmart's week numbering. This is important because we can't use real retailer sales data from the company but need to build the pipeline that can run when real data gets injected as a source. The correct structure will allow for real data to be used when provided.

Real retailer sales data for suppliers usually arrives as weekly reports, one file per retailer week, often downloaded manually rather than through an API. The pipeline should be built for that reality.

Options considered:
- Load M5 once: simple, but not a real pipeline; no incremental loads or reruns to handle.
- Replay M5 as daily files: exercises incremental loading, but does not match how real supplier data arrives.
- Replay M5 as weekly files: matches real delivery and the retailer week used in reporting.

## Decision

Use M5 as the v1 data source. A replay script delivers one file per Walmart week into the bronze layer, simulating weekly report deliveries. Silver stores sales at item × retailer week grain. The full daily M5 data is kept in bronze.

## Consequences

Positive:
- Real weekly retailer files can later be added through a new staging model without changing silver or gold.
- Weekly incremental loads, late files, and corrected re-sends can be tested realistically.

Negative:
- Daily patterns, such as weekday effects, are not available in silver or gold. They can be added later from the daily data kept in bronze.
- Product names, prime item numbers, and vendor stock IDs are not in M5 and must be generated as synthetic values.
- Week boundaries must follow Walmart's fiscal week exactly; this is verified against the M5 calendar.