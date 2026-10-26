"""Generate a synthetic item master as dated snapshots in bronze.

M5 has no product names, SKUs, prime item IDs, or vendor stock IDs, so this script
creates them from M5's item list. It writes three full snapshots, each the whole
item master as of its date, with deliberate changes between them:

    2011-01-29  starting version: one SKU per M5 item
    2013-02-02  3 products renamed, 2 discontinued; no mapping changes
    2015-01-31  a new SKU added and the first item remapped to it, with an
                effective date one week before the snapshot

Output, under the bronze folder:

    item_master/snapshot_date=<date>/products.csv
    item_master/snapshot_date=<date>/channel_items.csv

Output is deterministic: rerunning writes identical files.
"""

import argparse
import copy
import csv
from pathlib import Path

import duckdb

CHANNEL = "walmart"
BRANDS = {"FOODS": "Harvest Table", "HOBBIES": "Playwell", "HOUSEHOLD": "Homestead"}
PRODUCT_FIELDS = ["sku", "product_name", "brand", "category", "upc", "status"]
CHANNEL_ITEM_FIELDS = [
    "channel",
    "channel_item_id",
    "sku",
    "prime_item_id",
    "vendor_stock_id",
    "effective_date",
]

Rows = list[dict[str, str]]


def load_items(raw_dir: Path) -> Rows:
    """Read M5's distinct items, sorted by item ID."""
    path = raw_dir / "sales_train_evaluation.csv"
    rows = duckdb.sql(
        f"""
        SELECT DISTINCT item_id, dept_id, cat_id
        FROM read_csv('{path}', all_varchar = true)
        ORDER BY item_id
        """
    ).fetchall()
    return [{"item_id": i, "dept_id": d, "cat_id": c} for i, d, c in rows]


def sku_for(position: int) -> str:
    return f"P{position:05d}"


def starting_version(items: Rows) -> tuple[Rows, Rows]:
    """The first snapshot: one product and one channel mapping per M5 item."""
    products, channel_items = [], []
    for position, item in enumerate(items, start=1):
        dept_name = item["dept_id"].replace("_", " ").title()  # FOODS_1 -> Foods 1
        item_number = item["item_id"].rsplit("_", 1)[-1]  # FOODS_1_001 -> 001
        products.append(
            {
                "sku": sku_for(position),
                "product_name": f"{dept_name} Item {item_number}",
                "brand": BRANDS[item["cat_id"]],
                "category": item["cat_id"],
                "upc": f"{position:012d}",  # 12 digits, leading zeros
                "status": "active",
            }
        )
        channel_items.append(
            {
                "channel": CHANNEL,
                "channel_item_id": item["item_id"],
                "sku": sku_for(position),
                "prime_item_id": f"PR{(position - 1) // 3 + 1:05d}",  # groups of 3
                "vendor_stock_id": f"VS{position:05d}",
                "effective_date": "",
            }
        )
    return products, channel_items


def build_versions(items: Rows) -> dict[str, tuple[Rows, Rows]]:
    """Build all three snapshots. Each is a full copy of the previous, then changed."""
    v1_products, v1_items = starting_version(items)

    v2_products, v2_items = copy.deepcopy(v1_products), copy.deepcopy(v1_items)
    for product in v2_products[1:4]:
        product["product_name"] += " (New Formula)"
    for product in v2_products[4:6]:
        product["status"] = "discontinued"

    v3_products, v3_items = copy.deepcopy(v2_products), copy.deepcopy(v2_items)
    new_sku = sku_for(len(items) + 1)
    original = v3_products[0]
    v3_products.append(
        {
            "sku": new_sku,
            "product_name": f"{original['product_name']} v2",
            "brand": original["brand"],
            "category": original["category"],
            "upc": f"{len(items) + 1:012d}",
            "status": "active",
        }
    )
    original["status"] = "discontinued"
    remapped = v3_items[0]
    remapped["sku"] = new_sku
    remapped["effective_date"] = "2015-01-24"  # took effect before it was recorded

    return {
        "2011-01-29": (v1_products, v1_items),
        "2013-02-02": (v2_products, v2_items),
        "2015-01-31": (v3_products, v3_items),
    }


def write_csv(path: Path, fields: list[str], rows: Rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def generate(raw_dir: Path, bronze_dir: Path) -> list[str]:
    """Write every snapshot into bronze. Returns the snapshot dates written."""
    versions = build_versions(load_items(raw_dir))
    for snapshot_date, (products, channel_items) in versions.items():
        folder = bronze_dir / "item_master" / f"snapshot_date={snapshot_date}"
        write_csv(folder / "products.csv", PRODUCT_FIELDS, products)
        write_csv(folder / "channel_items.csv", CHANNEL_ITEM_FIELDS, channel_items)
        print(f"Wrote item master snapshot {snapshot_date}")
    return list(versions)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic item master.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/m5"))
    parser.add_argument("--bronze-dir", type=Path, default=Path("data/bronze/m5"))
    args = parser.parse_args()
    generate(args.raw_dir, args.bronze_dir)


if __name__ == "__main__":
    main()
