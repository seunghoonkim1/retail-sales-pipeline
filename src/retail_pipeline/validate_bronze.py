"""Validate every bronze M5 sales file, each against the weeks before it.

A calibration run: on real data, rejections should never happen, and warnings
should be rare. Frequent warnings would mean the thresholds need adjusting.
"""

import argparse
from pathlib import Path

import duckdb

from retail_pipeline.validation import M5_SALES, DeliveryHistory, validate_file

HISTORY_WEEKS = 4  # how many recent weeks count as "typical"


def week_summary(path: Path) -> tuple[int, frozenset[str]]:
    """Total units in a file, and the items that sold at least one unit."""
    rows = duckdb.sql(
        f"SELECT item_id, sum(try_cast(units AS bigint)) AS units "
        f"FROM read_csv('{path}', all_varchar = true) GROUP BY item_id"
    ).fetchall()
    total = sum(units or 0 for _, units in rows)
    sold = frozenset(item for item, units in rows if units and units > 0)
    return total, sold


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate all bronze M5 sales files.")
    parser.add_argument("--bronze-dir", type=Path, default=Path("data/bronze/m5"))
    args = parser.parse_args()

    files = sorted((args.bronze_dir / "sales").glob("wm_yr_wk=*/sales.csv"))
    totals: list[int] = []
    previous_items: frozenset[str] | None = None
    rejected = warned = 0

    for path in files:
        week = path.parent.name.split("=", 1)[1]  # "wm_yr_wk=11452" -> "11452"

        history = None
        if previous_items is not None:  # the first week has no history
            history = DeliveryHistory(
                recent_weekly_units=totals[-HISTORY_WEEKS:],
                previous_items=previous_items,
            )

        result = validate_file(path, M5_SALES, week, history)
        if len(totals) % 50 == 0:
            print(f"checked {len(totals)} of {len(files)} files...")
        if result.errors:
            rejected += 1
            print(f"REJECTED {week}: {result.errors}")
        if result.warnings:
            warned += 1
            print(f"WARNING  {week}: {result.warnings}")

        # This week becomes history for the next one.
        total, previous_items = week_summary(path)
        totals.append(total)

    print(f"\n{len(files)} files: {rejected} rejected, {warned} with warnings")


if __name__ == "__main__":
    main()
