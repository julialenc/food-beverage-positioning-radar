"""Refresh Aldi private-label analysis CSVs after company-mapping correction.

This script overwrites only the direct private_label_analysis files affected by
the Aldi / Trader Joe's correction:

* aldi_products_full_macro_positioning_details.csv
* aldi_products_macro_positioning.csv
* aldi_products_investigation_details.csv
* retailer_brand_protein_levels_by_region_category.csv

It reads current derived company/brand routing from SQLite and preserves raw
Open Food Facts fields in the output columns.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "positioning_radar.db"
OUTPUT_DIR = ROOT / "data" / "06_brand_governance_outputs" / "private_label_analysis"

FULL_PATH = OUTPUT_DIR / "aldi_products_full_macro_positioning_details.csv"
MACRO_PATH = OUTPUT_DIR / "aldi_products_macro_positioning.csv"
INVESTIGATION_PATH = OUTPUT_DIR / "aldi_products_investigation_details.csv"
PROTEIN_PATH = OUTPUT_DIR / "retailer_brand_protein_levels_by_region_category.csv"

REGION_ORDER = ["FRANCE", "UK_IE", "US_CANADA"]
CATEGORY_ORDER = ["beverages", "cereals", "dairies", "snacks"]

FULL_COLUMNS = [
    "region",
    "category",
    "company",
    "brand",
    "product",
    "GTIN",
    "image_url",
    "pack_size_off",
    "ingredients_text_off",
    "energy_kcal_per_100g",
    "protein_per_100g",
    "fat_per_100g",
    "saturated_fat_per_100g",
    "carbohydrates_per_100g",
    "sugars_per_100g",
    "fiber_per_100g",
    "NOVA",
    "Nutriscore",
    "Positioning",
]
MACRO_COLUMNS = [
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
    "Positioning",
]
INVESTIGATION_COLUMNS = FULL_COLUMNS + ["Investigate"]
PROTEIN_COLUMNS = [
    "region",
    "category",
    "company",
    "brand",
    "n_products_with_protein",
    "protein_min_gr_per_100g",
    "protein_median_gr_per_100g",
    "protein_max_gr_per_100g",
]

PROTEIN_COMPANY_SCOPE = {
    "FRANCE": [
        "Aldi",
        "Lidl",
        "Carrefour",
        "E.Leclerc",
        "Intermarche",
        "Auchan",
        "Groupe Casino",
        "Groupe U",
    ],
    "UK_IE": [
        "Aldi",
        "Lidl",
        "Tesco",
        "Asda",
        "Sainsbury's",
        "Morrisons",
        "Waitrose",
    ],
    "US_CANADA": [
        "Aldi",
        "Lidl",
        "Costco",
        "Kroger",
        "Target",
        "Walgreens",
        "Walmart",
    ],
}


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


def positioning(pack_claims_found: object, claim_source: object) -> str:
    if claim_source != "vision":
        return "NOT_ANALYZED"
    if pack_claims_found is None:
        return "NOT_ANALYZED"
    claims = str(pack_claims_found).strip()
    return claims if claims else "NO_CLAIM_IDENTIFIED"


def sort_key(row: dict[str, str]) -> tuple[object, ...]:
    region = row["region"]
    category = row["category"]
    return (
        REGION_ORDER.index(region) if region in REGION_ORDER else 99,
        CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else 99,
        row.get("brand", "").lower(),
        row.get("product", "").lower(),
        row.get("GTIN", ""),
    )


def brand_expr() -> str:
    return (
        "COALESCE(NULLIF(TRIM(p.normalized_brand), ''), "
        "NULLIF(TRIM(p.primary_brand), ''), p.brands)"
    )


def product_detail_query() -> str:
    display_brand = brand_expr()
    return f"""
        SELECT
            p.barcode,
            p.product_name,
            p.query_category,
            p.observed_market_region_codes,
            p.resolved_company,
            {display_brand} AS brand,
            p.image_url,
            p.quantity,
            p.ingredients_text,
            p.energy_kcal,
            p.protein_100g,
            p.fat_100g,
            p.saturated_fat_100g,
            p.carbs_100g,
            p.sugars_100g,
            p.fiber_100g,
            p.nova_group,
            p.nutriscore_grade,
            a.pack_claims_found,
            a.claim_source
        FROM products p
        LEFT JOIN product_analysis a ON a.barcode = p.barcode
        WHERE p.ingested_at = (SELECT MAX(ingested_at) FROM products)
          AND COALESCE(p.include_in_product_table, 1) = 1
          AND p.resolved_company = ?
          AND ('|' || COALESCE(p.observed_market_region_codes, '') || '|') LIKE ?
          AND {display_brand} IS NOT NULL
          AND TRIM(LOWER({display_brand})) NOT IN ('unknown', '', 'nan')
    """


def row_from_sql(region: str, r: sqlite3.Row) -> dict[str, str]:
    return {
        "region": region,
        "category": str(r["query_category"] or ""),
        "company": str(r["resolved_company"] or ""),
        "brand": str(r["brand"] or ""),
        "product": str(r["product_name"] or ""),
        "GTIN": str(r["barcode"] or ""),
        "image_url": str(r["image_url"] or ""),
        "pack_size_off": str(r["quantity"] or ""),
        "ingredients_text_off": str(r["ingredients_text"] or ""),
        "energy_kcal_per_100g": clean_num(r["energy_kcal"]),
        "protein_per_100g": clean_num(r["protein_100g"]),
        "fat_per_100g": clean_num(r["fat_100g"]),
        "saturated_fat_per_100g": clean_num(r["saturated_fat_100g"]),
        "carbohydrates_per_100g": clean_num(r["carbs_100g"]),
        "sugars_per_100g": clean_num(r["sugars_100g"]),
        "fiber_per_100g": clean_num(r["fiber_100g"]),
        "NOVA": clean_intish(r["nova_group"]),
        "Nutriscore": ""
        if r["nutriscore_grade"] is None
        else str(r["nutriscore_grade"]).upper(),
        "Positioning": positioning(r["pack_claims_found"], r["claim_source"]),
    }


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def export_aldi_products(conn: sqlite3.Connection) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    query = product_detail_query()
    for region in REGION_ORDER:
        region_pattern = f"%|{region}|%"
        for record in conn.execute(query, ("Aldi", region_pattern)):
            rows.append(row_from_sql(region, record))
    rows.sort(key=sort_key)
    write_csv(FULL_PATH, FULL_COLUMNS, rows)
    write_csv(MACRO_PATH, MACRO_COLUMNS, [{k: row[k] for k in MACRO_COLUMNS} for row in rows])
    return rows


def existing_investigation_gtins() -> set[str]:
    with INVESTIGATION_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return {
            (row.get("GTIN") or "").strip()
            for row in csv.DictReader(f)
            if (row.get("GTIN") or "").strip()
        }


def export_investigation(rows: list[dict[str, str]]) -> tuple[int, int]:
    gtins = existing_investigation_gtins()
    investigation_rows = [
        {**row, "Investigate": "yes"}
        for row in rows
        if row.get("GTIN", "") in gtins
    ]
    write_csv(INVESTIGATION_PATH, INVESTIGATION_COLUMNS, investigation_rows)
    return len(investigation_rows), len(gtins) - len(investigation_rows)


def export_protein_levels(conn: sqlite3.Connection) -> int:
    display_brand = brand_expr()
    query = f"""
        SELECT
            ? AS region,
            p.query_category AS category,
            p.resolved_company AS company,
            {display_brand} AS brand,
            COUNT(*) AS n_products_with_protein,
            MIN(CAST(p.protein_100g AS REAL)) AS protein_min,
            MEDIAN(CAST(p.protein_100g AS REAL)) AS protein_median,
            MAX(CAST(p.protein_100g AS REAL)) AS protein_max
        FROM products p
        WHERE p.ingested_at = (SELECT MAX(ingested_at) FROM products)
          AND COALESCE(p.include_in_product_table, 1) = 1
          AND p.query_category IN ({",".join("?" for _ in CATEGORY_ORDER)})
          AND p.resolved_company = ?
          AND ('|' || COALESCE(p.observed_market_region_codes, '') || '|') LIKE ?
          AND CAST(p.protein_100g AS REAL) > 0
          AND {display_brand} IS NOT NULL
          AND TRIM(LOWER({display_brand})) NOT IN ('unknown', '', 'nan')
        GROUP BY p.query_category, p.resolved_company, {display_brand}
    """
    rows: list[dict[str, str]] = []
    for region in REGION_ORDER:
        for company in PROTEIN_COMPANY_SCOPE[region]:
            params = [region, *CATEGORY_ORDER, company, f"%|{region}|%"]
            for r in conn.execute(query, params):
                rows.append(
                    {
                        "region": str(r["region"] or ""),
                        "category": str(r["category"] or ""),
                        "company": str(r["company"] or ""),
                        "brand": str(r["brand"] or ""),
                        "n_products_with_protein": str(r["n_products_with_protein"]),
                        "protein_min_gr_per_100g": clean_num(r["protein_min"]),
                        "protein_median_gr_per_100g": clean_num(r["protein_median"]),
                        "protein_max_gr_per_100g": clean_num(r["protein_max"]),
                    }
                )
    rows.sort(
        key=lambda row: (
            REGION_ORDER.index(row["region"]),
            CATEGORY_ORDER.index(row["category"]),
            row["company"].lower(),
            row["brand"].lower(),
        )
    )
    write_csv(PROTEIN_PATH, PROTEIN_COLUMNS, rows)
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh Aldi private-label CSV exports.")
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.create_aggregate("MEDIAN", 1, MedianAggregate)
        aldi_rows = export_aldi_products(conn)
        investigation_rows, investigation_removed = export_investigation(aldi_rows)
        protein_rows = export_protein_levels(conn)
    finally:
        conn.close()

    print("Refreshed Aldi private-label analysis exports:")
    print(f"  {FULL_PATH}: {len(aldi_rows):,} rows")
    print(f"  {MACRO_PATH}: {len(aldi_rows):,} rows")
    print(
        f"  {INVESTIGATION_PATH}: {investigation_rows:,} rows "
        f"({investigation_removed:,} previous investigated GTINs no longer Aldi)"
    )
    print(f"  {PROTEIN_PATH}: {protein_rows:,} rows")


class MedianAggregate:
    def __init__(self) -> None:
        self.values: list[float] = []

    def step(self, value: object) -> None:
        if value is None:
            return
        self.values.append(float(value))

    def finalize(self) -> float | None:
        if not self.values:
            return None
        values = sorted(self.values)
        mid = len(values) // 2
        if len(values) % 2:
            return values[mid]
        return (values[mid - 1] + values[mid]) / 2


if __name__ == "__main__":
    main()
