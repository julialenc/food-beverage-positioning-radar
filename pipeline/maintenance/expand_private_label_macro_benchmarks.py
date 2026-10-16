"""Expand private-label macro benchmarks with retailer company scopes.

The existing benchmark CSV contains total region-category medians. This script
preserves those rows as scope="total region" and appends company-level rows for
Aldi, Lidl, and selected mainstream retailers using the same output schema. The retained baseline is read-only; an explicit
new output path outside private_label_analysis is required.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "positioning_radar.db"
INPUT_PATH = (
    ROOT
    / "presentations"
    / "private_label_analysis"
    / "nutrition_values_vs_market_median_all_retailers.csv"
)

REGION_ORDER = ["FRANCE", "UK_IE", "US_CANADA"]
CATEGORY_ORDER = ["beverages", "cereals", "dairies", "snacks"]
COMPANY_SCOPES = [
    ("aldi", "Aldi", REGION_ORDER),
    ("lidl", "Lidl", REGION_ORDER),
    ("carrefour", "Carrefour", ["FRANCE"]),
    ("e_leclerc", "E.Leclerc", ["FRANCE"]),
    ("intermarche", "Intermarché", ["FRANCE"]),
    ("groupe_casino", "Groupe Casino", ["FRANCE"]),
    ("groupe_u", "Groupe U", ["FRANCE"]),
    ("auchan", "Auchan", ["FRANCE"]),
    ("tesco", "Tesco", ["UK_IE"]),
    ("asda", "Asda", ["UK_IE"]),
    ("sainsbury", "Sainsbury's", ["UK_IE"]),
    ("morrisons", "Morrisons", ["UK_IE"]),
    ("waitrose", "Waitrose", ["UK_IE"]),
    ("walmart", "Walmart", ["US_CANADA"]),
    ("costco", "Costco", ["US_CANADA"]),
    ("kroger", "Kroger", ["US_CANADA"]),
    ("target", "Target", ["US_CANADA"]),
    ("walgreens", "Walgreens", ["US_CANADA"]),
]

BASE_COLUMNS = [
    "region",
    "category",
    "company",
    "brand",
    "product",
    "energy_kcal_per_100g",
    "protein_per_100g",
    "fat_per_100g",
    "saturated_fat_per_100g",
    "carbohydrates_per_100g",
    "sugars_per_100g",
    "fiber_per_100g",
    "NOVA",
    "Nutriscore",
]
OUTPUT_COLUMNS = ["scope", *BASE_COLUMNS]

NUMERIC_FIELDS = {
    "energy_kcal_per_100g": "energy_kcal",
    "protein_per_100g": "protein_100g",
    "fat_per_100g": "fat_100g",
    "saturated_fat_per_100g": "saturated_fat_100g",
    "carbohydrates_per_100g": "carbs_100g",
    "sugars_per_100g": "sugars_100g",
    "fiber_per_100g": "fiber_100g",
}


class MedianAggregate:
    def __init__(self) -> None:
        self.values: list[float] = []

    def step(self, value: object) -> None:
        if value is None:
            return
        try:
            self.values.append(float(value))
        except (TypeError, ValueError):
            return

    def finalize(self) -> float | None:
        if not self.values:
            return None
        values = sorted(self.values)
        mid = len(values) // 2
        if len(values) % 2:
            return values[mid]
        return (values[mid - 1] + values[mid]) / 2


def clean_num(value: object) -> str:
    if value is None:
        return ""
    try:
        return str(round(float(value), 4))
    except (TypeError, ValueError):
        return str(value)


def clean_intish(value: object) -> str:
    if value is None:
        return ""
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value)


def percent_split(rows: list[sqlite3.Row], field: str, order: list[str]) -> str:
    values = [clean_intish(row[field]) if field == "nova_group" else str(row[field]).upper() for row in rows]
    values = [value for value in values if value and value != "NONE"]
    total = len(values)
    if total == 0:
        return ""
    counts = {value: values.count(value) for value in set(values)}
    parts = []
    for value in order:
        if value in counts:
            parts.append(f"{value}: {counts[value] / total * 100:.1f}%")
    return " | ".join(parts)


def load_existing_total_rows(path: Path = INPUT_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)

    rows: list[dict[str, str]] = []
    for row in existing_rows:
        existing_scope = row.get("scope", "").strip()
        if existing_scope and existing_scope != "total region":
            continue
        normalized = {column: row.get(column, "") for column in BASE_COLUMNS}
        normalized["scope"] = "total region"
        rows.append({column: normalized.get(column, "") for column in OUTPUT_COLUMNS})
    return rows


def load_company_scope_rows(conn: sqlite3.Connection) -> list[dict[str, str]]:
    metric_select = ",\n            ".join(
        f"MEDIAN(CAST({source_col} AS REAL)) AS {out_col}"
        for out_col, source_col in NUMERIC_FIELDS.items()
    )
    metric_where = " OR ".join(
        f"{source_col} IS NOT NULL" for source_col in NUMERIC_FIELDS.values()
    )
    query = f"""
        SELECT
            {metric_select}
        FROM products
        WHERE ingested_at = (SELECT MAX(ingested_at) FROM products)
          AND COALESCE(include_in_product_table, 1) = 1
          AND resolved_company = ?
          AND query_category = ?
          AND ('|' || COALESCE(observed_market_region_codes, '') || '|') LIKE ?
          AND ({metric_where})
    """
    detail_query = """
        SELECT nova_group, nutriscore_grade
        FROM products
        WHERE ingested_at = (SELECT MAX(ingested_at) FROM products)
          AND COALESCE(include_in_product_table, 1) = 1
          AND resolved_company = ?
          AND query_category = ?
          AND ('|' || COALESCE(observed_market_region_codes, '') || '|') LIKE ?
    """

    rows: list[dict[str, str]] = []
    for scope, company, regions in COMPANY_SCOPES:
        for region in regions:
            region_pattern = f"%|{region}|%"
            for category in CATEGORY_ORDER:
                metric_row = conn.execute(
                    query, (company, category, region_pattern)
                ).fetchone()
                detail_rows = list(
                    conn.execute(detail_query, (company, category, region_pattern))
                )
                if not metric_row or not detail_rows:
                    continue

                row = {
                    "scope": scope,
                    "region": region,
                    "category": category,
                    "company": company,
                    "brand": "ALL_BRANDS",
                    "product": "CATEGORY_MEDIAN",
                    "NOVA": percent_split(
                        detail_rows, "nova_group", ["1", "2", "3", "4"]
                    ),
                    "Nutriscore": percent_split(
                        detail_rows, "nutriscore_grade", ["A", "B", "C", "D", "E"]
                    ),
                }
                for out_col in NUMERIC_FIELDS:
                    row[out_col] = clean_num(metric_row[out_col])
                rows.append({column: row.get(column, "") for column in OUTPUT_COLUMNS})
    return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_PATH)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    args = ap.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(INPUT_PATH.parent.resolve()):
        ap.error("Output must be outside the retained private_label_analysis evidence tree")
    if output.exists() or output == args.input.resolve():
        ap.error("Choose a new output file; existing evidence is never overwritten")
    total_rows = load_existing_total_rows(args.input)
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.create_aggregate("MEDIAN", 1, MedianAggregate)
    try:
        company_rows = load_company_scope_rows(conn)
    finally:
        conn.close()

    write_rows(output, total_rows + company_rows)
    print(f"Wrote {output}; retained input unchanged")
    print(f"total region rows: {len(total_rows)}")
    print(f"company rows: {len(company_rows)}")
    print(f"total rows: {len(total_rows) + len(company_rows)}")


if __name__ == "__main__":
    main()
