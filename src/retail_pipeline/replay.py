"""Replay the M5 dataset as weekly bronze files.

Simulates a retailer delivering one file per Walmart week. It reads the raw
M5 files and writes, for each complete week:

    <bronze>/sales/wm_yr_wk=<week>/sales.csv    daily rows for that week
    <bronze>/prices/wm_yr_wk=<week>/prices.csv  that week's prices

plus the calendar once:

    <bronze>/calendar/calendar.csv

Every value is read and written as text, exactly as in the source.
Output is deterministic: rerunning replaces the same files with identical content.
"""

import argparse
from pathlib import Path

import duckdb

ID_COLUMNS = ["item_id", "dept_id", "cat_id", "store_id", "state_id"]

RAW_FILES = {
    "calendar": "calendar.csv",
    "sales": "sales_train_evaluation.csv",
    "prices": "sell_prices.csv",
}


def load_raw(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    """Load the raw M5 files into DuckDB, reading every column as text."""
    for table, file_name in RAW_FILES.items():
        path = raw_dir / file_name
        con.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            f"SELECT * FROM read_csv('{path}', all_varchar = true)"
        )


def complete_weeks(con: duckdb.DuckDBPyConnection) -> dict[str, list[str]]:
    """Map each Walmart week to its seven day columns (d_1, d_2, ...).

    Only weeks whose seven days all exist in the sales file are included,
    so a partial week at the end of the data is skipped.
    """
    sales_columns = set(con.table("sales").columns)
    rows = con.execute(
        """
        SELECT wm_yr_wk, list(d ORDER BY date) AS days
        FROM calendar
        GROUP BY wm_yr_wk
        ORDER BY wm_yr_wk
        """
    ).fetchall()
    return {
        week: days
        for week, days in rows
        if len(days) == 7 and all(day in sales_columns for day in days)
    }


def copy_to_csv(con: duckdb.DuckDBPyConnection, query: str, path: Path) -> None:
    """Write a query's result to a CSV file, replacing any existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    con.execute(f"COPY ({query}) TO '{path}' (HEADER, DELIMITER ',')")


def write_week(
    con: duckdb.DuckDBPyConnection, bronze_dir: Path, week: str, days: list[str]
) -> None:
    """Write one week's sales file (daily rows) and prices file."""
    id_list = ", ".join(ID_COLUMNS)
    day_list = ", ".join(f'"{day}"' for day in days)

    # Keep only this week's seven day columns, then reshape wide to long:
    # one row per item, store, and day instead of one column per day.
    con.execute(
        f"CREATE OR REPLACE TEMP VIEW week_wide AS "
        f"SELECT {id_list}, {day_list} FROM sales"
    )
    sales_query = f"""
        WITH week_long AS (
            UNPIVOT week_wide ON {day_list} INTO NAME d VALUE units
        )
        SELECT {id_list}, calendar.date, calendar.wm_yr_wk, week_long.units
        FROM week_long
        JOIN calendar USING (d)
        ORDER BY store_id, item_id, calendar.date
    """
    copy_to_csv(
        con, sales_query, bronze_dir / "sales" / f"wm_yr_wk={week}" / "sales.csv"
    )

    prices_query = f"""
        SELECT store_id, item_id, wm_yr_wk, sell_price
        FROM prices
        WHERE wm_yr_wk = '{week}'
        ORDER BY store_id, item_id
    """
    copy_to_csv(
        con, prices_query, bronze_dir / "prices" / f"wm_yr_wk={week}" / "prices.csv"
    )


def replay(raw_dir: Path, bronze_dir: Path, max_weeks: int | None = None) -> list[str]:
    """Replay M5 into weekly bronze files. Returns the weeks written."""
    con = duckdb.connect()
    try:
        load_raw(con, raw_dir)
        weeks = list(complete_weeks(con).items())[:max_weeks]

        copy_to_csv(
            con,
            "SELECT * FROM calendar ORDER BY date",
            bronze_dir / "calendar" / "calendar.csv",
        )
        for week, days in weeks:
            write_week(con, bronze_dir, week, days)
            print(f"Wrote week {week}")
    finally:
        con.close()

    return [week for week, _ in weeks]


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay M5 as weekly bronze files.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/m5"))
    parser.add_argument("--bronze-dir", type=Path, default=Path("data/bronze/m5"))
    parser.add_argument(
        "--max-weeks", type=int, default=None, help="Replay only the first N weeks."
    )
    args = parser.parse_args()
    replay(args.raw_dir, args.bronze_dir, args.max_weeks)


if __name__ == "__main__":
    main()
