# 5. Use Walmart's official fiscal calendar conventions

Date: 2026-10-19

## Status

Accepted

## Context

Walmart's official fiscal year is named for the year it ends in: the week starting 2021-01-30 is fiscal year 2022, week 1, written 202201 in Walmart's reports. M5's wm_yr_wk names the year by the calendar year it starts in, one year earlier. M5's calendar also has no fiscal months.

Reports group weekly data into calendar months, and a week can span two months.

## Decision

- Convert M5 week codes to Walmart's official fiscal year in staging.
- Derive fiscal months for M5 from Walmart's 4-5-4 pattern, confirmed against Walmart's official calendar. Week 53 is assumed to belong to fiscal month 12.
- Assign each week to the calendar month containing its end date, matching existing reports.

## Consequences

Positive:
- M5 and real Walmart data use the same fiscal year labels, so year-over-year comparisons line up.
- Monthly reporting matches the conventions already used in existing reports.

Negative:
- Fiscal months for M5 are derived rather than read from an official calendar. The week 53 assumption is unverified.