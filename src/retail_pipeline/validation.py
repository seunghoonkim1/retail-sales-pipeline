"""Validate a delivered weekly sales file before it enters bronze.

Each check either rejects the file (an error) or flags it for review (a warning).
A file with any error must not be loaded. Warnings are reported but don't block.
"""

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


def read_as_text(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    """Load the file into a table called `delivery`, every column as text."""
    con.execute(
        f"CREATE OR REPLACE TABLE delivery AS "
        f"SELECT * FROM read_csv('{path}', all_varchar = true)"
    )


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


def validate_file(path: Path, spec: SourceSpec, expected_week: str) -> ValidationResult:
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
    finally:
        con.close()
    return result
