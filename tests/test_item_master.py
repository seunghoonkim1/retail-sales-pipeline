"""Tests for the item master generator, using a tiny made-up item list."""

import csv
from pathlib import Path

import pytest

from retail_pipeline.item_master import generate

SNAPSHOTS = ["2011-01-29", "2013-02-02", "2015-01-31"]
ITEMS = [
    ("FOODS_1_001", "FOODS_1", "FOODS"),
    ("FOODS_1_002", "FOODS_1", "FOODS"),
    ("FOODS_2_001", "FOODS_2", "FOODS"),
    ("HOBBIES_1_001", "HOBBIES_1", "HOBBIES"),
    ("HOBBIES_1_002", "HOBBIES_1", "HOBBIES"),
    ("HOUSEHOLD_1_001", "HOUSEHOLD_1", "HOUSEHOLD"),
    ("HOUSEHOLD_1_002", "HOUSEHOLD_1", "HOUSEHOLD"),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    """A tiny M5-like sales file: 7 items, one sold in two stores."""
    raw = tmp_path / "raw"
    raw.mkdir()
    rows = [[item, dept, cat, "CA_1", "CA", "1"] for item, dept, cat in ITEMS]
    rows.append(["FOODS_1_001", "FOODS_1", "FOODS", "TX_1", "TX", "2"])
    with (raw / "sales_train_evaluation.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "dept_id", "cat_id", "store_id", "state_id", "d_1"])
        writer.writerows(rows)
    return raw


def snapshot(bronze: Path, date: str, name: str) -> list[dict[str, str]]:
    return read_csv(bronze / "item_master" / f"snapshot_date={date}" / f"{name}.csv")


def test_writes_three_snapshots(raw_dir: Path, tmp_path: Path) -> None:
    assert generate(raw_dir, tmp_path / "bronze") == SNAPSHOTS


def test_starting_version_has_one_product_per_item(
    raw_dir: Path, tmp_path: Path
) -> None:
    bronze = tmp_path / "bronze"
    generate(raw_dir, bronze)
    products = snapshot(bronze, "2011-01-29", "products")
    items = snapshot(bronze, "2011-01-29", "channel_items")

    assert len(products) == 7  # the item sold in two stores appears once
    assert products[0] == {
        "sku": "P00001",
        "product_name": "Foods 1 Item 001",
        "brand": "Harvest Table",
        "category": "FOODS",
        "upc": "000000000001",  # leading zeros kept
        "status": "active",
    }
    assert items[0]["channel_item_id"] == "FOODS_1_001"
    assert items[0]["sku"] == "P00001"


def test_second_version_renames_and_discontinues(raw_dir: Path, tmp_path: Path) -> None:
    bronze = tmp_path / "bronze"
    generate(raw_dir, bronze)
    products = {p["sku"]: p for p in snapshot(bronze, "2013-02-02", "products")}

    for sku in ["P00002", "P00003", "P00004"]:
        assert products[sku]["product_name"].endswith("(New Formula)")
    for sku in ["P00005", "P00006"]:
        assert products[sku]["status"] == "discontinued"
    # mappings are unchanged
    assert snapshot(bronze, "2013-02-02", "channel_items") == snapshot(
        bronze, "2011-01-29", "channel_items"
    )


def test_third_version_remaps_first_item(raw_dir: Path, tmp_path: Path) -> None:
    bronze = tmp_path / "bronze"
    generate(raw_dir, bronze)
    products = {p["sku"]: p for p in snapshot(bronze, "2015-01-31", "products")}
    items = snapshot(bronze, "2015-01-31", "channel_items")

    assert products["P00008"]["status"] == "active"  # the new SKU
    assert products["P00001"]["status"] == "discontinued"
    assert items[0]["channel_item_id"] == "FOODS_1_001"
    assert items[0]["sku"] == "P00008"
    assert items[0]["effective_date"] == "2015-01-24"
    # every other mapping is unchanged
    assert items[1:] == snapshot(bronze, "2013-02-02", "channel_items")[1:]


def test_rerun_produces_identical_files(raw_dir: Path, tmp_path: Path) -> None:
    bronze = tmp_path / "bronze"
    generate(raw_dir, bronze)
    first = {path: path.read_bytes() for path in bronze.rglob("*.csv")}
    generate(raw_dir, bronze)
    second = {path: path.read_bytes() for path in bronze.rglob("*.csv")}
    assert first == second
