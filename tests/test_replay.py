"""Tests for the M5 replay script, using a tiny made-up dataset."""

import csv
from datetime import date, timedelta
from pathlib import Path

import pytest

from retail_pipeline.replay import replay

# 15 days: two complete Walmart weeks (11101, 11102) plus one day of 11103.
START = date(2011, 1, 29)  # a Saturday, like the real M5 start date
NUM_DAYS = 15


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    """Create a tiny M5-like raw dataset and return its folder."""
    raw = tmp_path / "raw"
    raw.mkdir()

    days = [f"d_{i}" for i in range(1, NUM_DAYS + 1)]
    weeks = ["11101"] * 7 + ["11102"] * 7 + ["11103"]

    write_csv(
        raw / "calendar.csv",
        ["date", "wm_yr_wk", "d"],
        [[str(START + timedelta(days=i)), weeks[i], days[i]] for i in range(NUM_DAYS)],
    )
    write_csv(
        raw / "sales_train_evaluation.csv",
        ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id", *days],
        [
            ["a", "0123", "D1", "C1", "CA_1", "CA", *[str(i) for i in range(NUM_DAYS)]],
            ["b", "0456", "D1", "C1", "CA_1", "CA", *["1"] * NUM_DAYS],
        ],
    )
    write_csv(
        raw / "sell_prices.csv",
        ["store_id", "item_id", "wm_yr_wk", "sell_price"],
        [
            ["CA_1", "0123", "11101", "2.50"],
            ["CA_1", "0456", "11101", "1.00"],
            ["CA_1", "0123", "11102", "2.75"],
        ],
    )
    return raw


def test_writes_only_complete_weeks(raw_dir: Path, tmp_path: Path) -> None:
    weeks = replay(raw_dir, tmp_path / "bronze")
    assert weeks == ["11101", "11102"]  # the partial week 11103 is skipped


def test_max_weeks_limits_output(raw_dir: Path, tmp_path: Path) -> None:
    bronze = tmp_path / "bronze"
    weeks = replay(raw_dir, bronze, max_weeks=1)
    assert weeks == ["11101"]
    assert not (bronze / "sales" / "wm_yr_wk=11102").exists()


def test_sales_file_has_one_row_per_item_and_day(raw_dir: Path, tmp_path: Path) -> None:
    bronze = tmp_path / "bronze"
    replay(raw_dir, bronze, max_weeks=1)
    rows = read_csv(bronze / "sales" / "wm_yr_wk=11101" / "sales.csv")

    assert len(rows) == 2 * 7  # 2 items x 7 days
    assert rows[0] == {
        "item_id": "0123",
        "dept_id": "D1",
        "cat_id": "C1",
        "store_id": "CA_1",
        "state_id": "CA",
        "date": "2011-01-29",
        "wm_yr_wk": "11101",
        "units": "0",
    }


def test_values_are_kept_as_text(raw_dir: Path, tmp_path: Path) -> None:
    bronze = tmp_path / "bronze"
    replay(raw_dir, bronze, max_weeks=1)
    sales = read_csv(bronze / "sales" / "wm_yr_wk=11101" / "sales.csv")
    prices = read_csv(bronze / "prices" / "wm_yr_wk=11101" / "prices.csv")

    assert {row["item_id"] for row in sales} == {"0123", "0456"}  # leading zero kept
    assert prices[0]["sell_price"] == "2.50"  # trailing zero kept


def test_rerun_produces_identical_files(raw_dir: Path, tmp_path: Path) -> None:
    bronze = tmp_path / "bronze"
    replay(raw_dir, bronze)
    first = {path: path.read_bytes() for path in bronze.rglob("*.csv")}

    replay(raw_dir, bronze)
    second = {path: path.read_bytes() for path in bronze.rglob("*.csv")}

    assert first == second
