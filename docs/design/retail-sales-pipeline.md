# Retail Sales Pipeline on AWS — Design Doc

Oct 7, 2026 · @Seung

## Summary

A serverless data pipeline on AWS that ingests daily retail sales files, models them through bronze, silver and gold layers with DuckDB and dbt, and serves the gold marts to Power BI through Athena. Status: draft; no code yet.

It uses only public data (the M5 dataset) and is open source under the MIT license. Because each source plugs in through an adapter and all infrastructure is defined in Terraform, the same pipeline can be deployed into another AWS account with different data.

## Why this project

Retail sales data arrives as files from many sources (retailer portals, marketplaces, ERPs), each in its own shape, and small brands usually stitch it together in spreadsheets. A pipeline that lands each source as-is, standardizes it into one format, and serves clean marts removes that manual work and is the foundation any later analysis or planning needs.

The design targets small teams: serverless and low-cost, with no servers to maintain, and runnable locally with Docker when a cloud account is not available.

## Goals, non-goals, success criteria

**MVP goals**

- M5 data replayed as daily files (one store, about 50 SKUs).
- Bronze, silver and gold layers in dbt on DuckDB, loaded incrementally and safe to rerun.
- A silver layer in a fixed standard format, so a new source needs only its own adapter.
- Gold marts queryable through Athena and shown in a Power BI report.
- Runs on AWS in dev and prod stages, fully defined in Terraform.

**Non-goals for MVP**

- Purchase order calculation and forecasting (see Future work).
- A custom web UI; Power BI is the only front end.
- Real company data or live integrations with Shopify, Amazon, Walmart or NetSuite.
- Snowflake or another cloud warehouse.

**Success criteria**

- A new day's file lands in S3 and the gold marts update without manual steps.
- Reprocessing the same file, or a corrected one, gives correct results with no duplicates.
- Dev and prod can be rebuilt from scratch with Terraform alone.
- Measured monthly AWS cost and run times are recorded in the README.

## Data model

Three layers, each with one job. Silver is the contract: it is defined independently of M5, shaped with real retailer supplier reports in mind, so a new source only needs a new adapter from bronze to silver.

| Layer | Holds | Example tables |
| --- | --- | --- |
| Bronze | Raw files exactly as received, partitioned by arrival date | raw M5 sales, calendar and price files |
| Silver | Cleaned data in the standard format: one row per SKU, location, date | stg\_sales\_daily, dim\_sku, dim\_location, dim\_calendar, stg\_prices |
| Gold | Business-ready marts, written as Parquet | mart\_sales\_daily, mart\_product\_performance, mart\_store\_comparison, mart\_price\_and\_event\_effects |

Each source gets one adapter model (bronze to silver); M5 is the first. Every silver table carries a location id from day one.

## Architecture

&#91;embedded content: architecture · serverless pipeline from S3 to Power BI\]

Each new file in the bronze bucket triggers one Lambda run, which rebuilds only what changed and writes Parquet back to S3. The same container image also runs locally with Docker, reading a local folder instead of S3, so the pipeline works with or without AWS.

Idempotency: each run's id comes from the input file's S3 version id, outputs are written to paths keyed by that id, and silver models merge on their keys. Processing the same file twice, or a corrected version of it, never creates duplicates.

## Environments and delivery

Dev and prod exist from the first milestone, and every change ships through both. Nothing reaches prod without passing CI.

| Environment | Where | Purpose |
| --- | --- | --- |
| Local | Laptop: Docker, local folders instead of S3 | Write and test models fast, at no cost |
| Dev | AWS account, `dev` stage | Auto-deploy on merge; verify against real AWS services |
| Prod | Same account, `prod` stage | Manual approval to promote; feeds the Power BI report |

Both stages are built from the same Terraform modules with per-stage settings and separate state, in one AWS account to keep it simple and cheap. Every resource name and IAM role is scoped to its stage, so dev cannot touch prod data.

Work flow per ticket:

1. Ticket in GitHub Projects, small enough for one PR.
2. Feature branch, code and tests.
3. PR with a description and self-review checklist; CI runs lint, unit tests and `dbt build`.
4. Merge to main deploys to dev automatically.
5. Verify in dev, then approve promotion to prod.
6. Tag the release and update the changelog.

## Testing, monitoring, cost

**Testing.** dbt tests on every layer: unique and non-null keys, valid relationships, accepted values, and row-count checks between silver and gold. CI runs them against a sample in DuckDB on every PR. A failed test stops the run before gold is written.

**Monitoring.** Lambda logs to CloudWatch. Failed runs retry, then land in a dead-letter queue and send an alert. A runbook in the repo covers a missing file, a failed dbt test, and how to reprocess a day.

**Cost.** Paid account plan, so the account is not closed when credits run out. A budget alert before any other resource (it notifies; it does not cap spend). Serverless only, no always-on servers. Actual monthly cost is measured and recorded, not estimated.

## Milestones

v1 is milestones 1 to 4, time-boxed to a handful of weekends. Finished and documented beats bigger and half-built.

1. **Foundations.** Public GitHub repo with MIT license, issues backlog, AWS account with budget alert, Terraform state, CI skeleton. Silver contract defined.
2. **Local pipeline.** M5 replay script, bronze to silver adapter, silver and gold dbt models on DuckDB, all tests passing in Docker.
3. **On AWS.** S3 buckets, Lambda container, S3 trigger, IAM, dead-letter queue, all in Terraform; dev and prod stages; idempotent reruns proven.
4. **Serving and write-up.** Glue Catalog, Athena, Power BI report; README with architecture, decisions, measured cost and run times.

## Future work

Parked deliberately; each fits on the v1 structure without upstream changes:

- Purchase order recommendations as a gold mart (forecast, adjustments, safety stock, MOQ/case/pallet rounding).
- Simulated inventory and open POs alongside M5 sales.
- dbt snapshots for slowly changing data.
- Adapters for real sources such as Walmart supplier reports or Shopify exports.
- Additional dbt targets, such as Snowflake.

## Decision log

| # | Decision | Alternatives considered | Why |
| --- | --- | --- | --- |
| 1 | Pipeline only for v1; PO calculation parked | Full PO planner | Keeps scope finishable; PO logic fits later as a gold mart |
| 2 | Public M5 data, replayed as daily files | Company data; a one-time load | No ownership issues; daily replay makes it a real pipeline |
| 3 | Silver as a source-independent contract with adapters | Model M5's shape directly | Another source, or a company's data later, needs only a new adapter |
| 4 | Lambda container running DuckDB + dbt | Fargate; Postgres; Snowflake | Lowest cost, no servers; same image runs locally |
| 5 | Gold served through Glue Catalog + Athena to Power BI | Power BI on a local DuckDB file | AWS-native serving; pay only per query |
| 6 | Dev and prod as two Terraform stages in one account | Two AWS accounts | Same practice with less overhead for a solo project |
| 7 | Public repo, MIT license | Private repo | Anyone can reuse it; clear licensing for adoption elsewhere |

## Open questions

- [ ] Which silver fields should mirror real retailer supplier reports (item and store identifiers, on-hand)?
- [ ] Replay pace: one simulated day per real day, or a backfill command that replays many days at once?
- [ ] Is a Power BI Desktop report enough for v1, or does it need a published report?
- [ ] What is the target date for v1?
