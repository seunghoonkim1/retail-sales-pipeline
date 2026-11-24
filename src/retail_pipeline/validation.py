"""Validate a delivered weekly sales file before it enters bronze.

Each check either rejects the file (an error) or flags it for review (a warning).
A file with any error must not be loaded. Warnings are reported but don't block.
"""

import statistics  # NEW: for the median in check_total_vs_history
from dataclasses import dataclass, field
from pathlib import Path

import duckdb


@dataclass(frozen=True)
class SourceSpec:
    """What a valid weekly file from one source looks like."""

    name: str
    columns: list[str]  # the exact expected columns, in order
    week_column: str  # the column holding the week inside the file
    key_columns: list[str]  # the columns that identify one row
    item_column: str  # NEW: the column identifying an item
    units_column: str


M5_SALES = SourceSpec(
    name="m5_sales",
    columns=[
        "item_id",
        "dept_id",
        "cat_id",
        "store_id",
        "state_id",
        "date",
        "wm_yr_wk",
        "units",
    ],
    week_column="wm_yr_wk",
    key_columns=["item_id", "store_id", "date"],
    item_column="item_id",  # NEW
    units_column="units",
)


@dataclass
class ValidationResult:
    """The outcome of validating one file."""

    file: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


# NEW: history from earlier deliveries, used by two of the warning checks
@dataclass(frozen=True)
class DeliveryHistory:
    """What's known from earlier deliveries of the same source."""

    recent_weekly_units: list[int]  # total units in each recent week
    previous_items: frozenset[str]  # items that sold in the previous week


def read_as_text(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    """Load the file into a table called `delivery`, every column as text."""
    con.execute(
        f"CREATE OR REPLACE TABLE delivery AS "
        f"SELECT * FROM read_csv('{path}', all_varchar = true, hive_partitioning = false)"
    )


# ---------- Rejection checks (errors) ----------


def check_columns(con: duckdb.DuckDBPyConnection, spec: SourceSpec) -> str | None:
    """Reject a file whose columns differ from the spec (a different report, say)."""
    found = con.table("delivery").columns
    if found == spec.columns:
        return None
    missing = [c for c in spec.columns if c not in found]
    unexpected = [c for c in found if c not in spec.columns]
    if not missing and not unexpected:
        return f"columns: expected order {spec.columns}, found {found}"
    return f"columns: missing {missing}, unexpected {unexpected}"


def check_week(
    con: duckdb.DuckDBPyConnection, spec: SourceSpec, expected_week: str
) -> str | None:
    """Reject a file with more than one week, or a week other than expected."""
    weeks = [
        row[0]
        for row in con.execute(
            f"SELECT DISTINCT {spec.week_column} FROM delivery ORDER BY 1"
        ).fetchall()
    ]
    if len(weeks) != 1:
        return f"week: expected one week ({expected_week}), found {len(weeks)}: {weeks}"
    if weeks[0] != expected_week:
        return f"week: file is for {expected_week}, but the data contains {weeks[0]}"
    return None


def check_duplicates(con: duckdb.DuckDBPyConnection, spec: SourceSpec) -> str | None:
    """Reject a file where any row's key appears more than once."""
    keys = ", ".join(spec.key_columns)
    duplicate_keys = con.execute(
        f"SELECT count(*) FROM ("
        f"SELECT {keys} FROM delivery GROUP BY {keys} HAVING count(*) > 1)"
    ).fetchone()[0]
    if duplicate_keys:
        return f"duplicates: {duplicate_keys} keys appear more than once ({keys})"
    return None


# ---------- Warning checks ----------


def check_numeric_units(con: duckdb.DuckDBPyConnection, spec: SourceSpec) -> str | None:
    """Warn about blank or non-numeric unit values."""
    bad_rows = con.execute(
        f"SELECT count(*) FROM delivery "
        f"WHERE try_cast({spec.units_column} AS bigint) IS NULL"
    ).fetchone()[0]
    if bad_rows:
        return f"units: {bad_rows} rows have blank or non-numeric {spec.units_column}"
    return None


def check_total_vs_history(
    con: duckdb.DuckDBPyConnection,
    spec: SourceSpec,
    history: DeliveryHistory,
    low: float = 0.2,
    high: float = 5.0,
) -> str | None:
    """Warn when this week's total units are far from the recent typical week."""
    if not history.recent_weekly_units:
        return None
    total = con.execute(
        f"SELECT coalesce(sum(try_cast({spec.units_column} AS bigint)), 0) "
        f"FROM delivery"
    ).fetchone()[0]
    typical = statistics.median(history.recent_weekly_units)
    if typical > 0 and not (low * typical <= total <= high * typical):
        return (
            f"total units: {total:,} this week vs. a typical {typical:,.0f}; "
            f"outside {low}x to {high}x"
        )
    return None


def check_missing_items(
    con: duckdb.DuckDBPyConnection, spec: SourceSpec, history: DeliveryHistory
) -> str | None:
    """Warn about items that sold last week but have no rows this week."""
    current = {
        row[0]
        for row in con.execute(
            f"SELECT DISTINCT {spec.item_column} FROM delivery"
        ).fetchall()
    }
    missing = sorted(history.previous_items - current)
    if missing:
        return (
            f"missing items: {len(missing)} items sold last week have no rows "
            f"this week, e.g. {missing[:5]}"
        )
    return None


# ---------- Running everything ----------


def validate_file(
    path: Path,
    spec: SourceSpec,
    expected_week: str,
    history: DeliveryHistory | None = None,  # NEW: optional history
) -> ValidationResult:
    """Run every check on one delivered file."""
    result = ValidationResult(file=path)
    con = duckdb.connect()
    try:
        read_as_text(con, path)

        columns_error = check_columns(con, spec)
        if columns_error:
            # The other checks rely on the expected columns, so stop here.
            result.errors.append(columns_error)
            return result

        for error in (
            check_week(con, spec, expected_week),
            check_duplicates(con, spec),
        ):
            if error:
                result.errors.append(error)

        # NEW: warnings only matter for a file that will actually be loaded.
        if not result.errors:
            warnings = [check_numeric_units(con, spec)]
            if history:
                warnings += [
                    check_total_vs_history(con, spec, history),
                    check_missing_items(con, spec, history),
                ]
            result.warnings = [w for w in warnings if w]
    finally:
        con.close()
    return result
