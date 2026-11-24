"""Tests for file validation, using small made-up delivery files."""

import csv
from pathlib import Path

import pytest

from retail_pipeline.validation import M5_SALES, DeliveryHistory, validate_file

COLUMNS = M5_SALES.columns
WEEK = "11452"


def row(item: str, day: str, units: str = "1", week: str = WEEK) -> list[str]:
    return [item, "D1", "C1", "CA_1", "CA", day, week, units]


VALID_ROWS = [
    row("0123", "2015-01-24"),
    row("0123", "2015-01-25"),
    row("0456", "2015-01-24"),
    row("0456", "2015-01-25"),
]


def write_delivery(folder: Path, columns: list[str], rows: list[list[str]]) -> Path:
    path = folder / "sales.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    return path


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    return tmp_path


# ---------- Rejection checks ----------


def test_valid_file_passes(folder: Path) -> None:
    path = write_delivery(folder, COLUMNS, VALID_ROWS)
    result = validate_file(path, M5_SALES, WEEK)
    assert result.passed
    assert result.errors == []


def test_rejects_missing_column(folder: Path) -> None:
    columns = [c for c in COLUMNS if c != "units"]
    rows = [r[:-1] for r in VALID_ROWS]
    result = validate_file(write_delivery(folder, columns, rows), M5_SALES, WEEK)
    assert not result.passed
    assert "missing ['units']" in result.errors[0]


def test_rejects_unexpected_column(folder: Path) -> None:
    columns = [*COLUMNS, "usw"]
    rows = [[*r, "0.5"] for r in VALID_ROWS]
    result = validate_file(write_delivery(folder, columns, rows), M5_SALES, WEEK)
    assert not result.passed
    assert "unexpected ['usw']" in result.errors[0]


def test_rejects_wrong_week(folder: Path) -> None:
    rows = [row("0123", "2015-01-31", week="11501")]
    result = validate_file(write_delivery(folder, COLUMNS, rows), M5_SALES, WEEK)
    assert not result.passed
    assert "file is for 11452, but the data contains 11501" in result.errors[0]


def test_rejects_more_than_one_week(folder: Path) -> None:
    rows = [*VALID_ROWS, row("0123", "2015-01-31", week="11501")]
    result = validate_file(write_delivery(folder, COLUMNS, rows), M5_SALES, WEEK)
    assert not result.passed
    assert "found 2" in result.errors[0]


def test_rejects_duplicate_rows(folder: Path) -> None:
    rows = [*VALID_ROWS, row("0123", "2015-01-24")]
    result = validate_file(write_delivery(folder, COLUMNS, rows), M5_SALES, WEEK)
    assert not result.passed
    assert "duplicates: 1 keys" in result.errors[0]


def test_week_comes_from_the_data_not_the_folder(folder: Path) -> None:
    # A real bronze folder layout: the folder says 11452, the data says 11501.
    week_folder = folder / "wm_yr_wk=11452"
    week_folder.mkdir()
    rows = [row("0123", "2015-01-31", week="11501")]
    path = write_delivery(week_folder, COLUMNS, rows)

    result = validate_file(path, M5_SALES, "11452")
    assert not result.passed
    assert "file is for 11452, but the data contains 11501" in result.errors[0]


# ---------- Warning checks ----------

# A normal history: 4 units in each recent week, both items sold last week.
TYPICAL_HISTORY = DeliveryHistory(
    recent_weekly_units=[4, 4, 4],
    previous_items=frozenset({"0123", "0456"}),
)


def test_valid_file_with_history_has_no_warnings(folder: Path) -> None:
    path = write_delivery(folder, COLUMNS, VALID_ROWS)
    result = validate_file(path, M5_SALES, WEEK, TYPICAL_HISTORY)
    assert result.passed
    assert result.warnings == []


def test_warns_on_non_numeric_units(folder: Path) -> None:
    rows = [
        *VALID_ROWS,
        row("0789", "2015-01-24", units=""),
        row("0789", "2015-01-25", units="abc"),
    ]
    result = validate_file(write_delivery(folder, COLUMNS, rows), M5_SALES, WEEK)
    assert result.passed  # a warning, not a rejection
    assert "2 rows have blank or non-numeric units" in result.warnings[0]


def test_warns_on_total_far_above_history(folder: Path) -> None:
    rows = [row("0123", "2015-01-24", units="1000"), row("0456", "2015-01-24")]
    result = validate_file(
        write_delivery(folder, COLUMNS, rows), M5_SALES, WEEK, TYPICAL_HISTORY
    )
    assert result.passed
    assert any("total units: 1,001" in w for w in result.warnings)


def test_warns_on_missing_items(folder: Path) -> None:
    rows = [row("0123", "2015-01-24"), row("0123", "2015-01-25")]
    result = validate_file(
        write_delivery(folder, COLUMNS, rows), M5_SALES, WEEK, TYPICAL_HISTORY
    )
    assert result.passed
    assert any("['0456']" in w for w in result.warnings)


def test_no_history_skips_history_checks(folder: Path) -> None:
    rows = [row("0123", "2015-01-24", units="1000")]
    result = validate_file(write_delivery(folder, COLUMNS, rows), M5_SALES, WEEK)
    assert result.passed
    assert result.warnings == []
