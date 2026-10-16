"""
Export retailer product detail CSVs from the current SQLite database.

The export preserves Open Food Facts source values for GTIN, image URL,
quantity, ingredients text, nutrition, NOVA, and Nutri-Score. The Positioning
column is a display field: pack-image claims are shown only when the product has
vision-derived claims; otherwise the product remains NOT_ANALYZED or
NO_CLAIM_IDENTIFIED according to the existing product_analysis state.

Usage:
    python pipeline/exports/export_retailer_product_details.py --retailer-set france_mainstream

    python pipeline/exports/export_retailer_product_details.py --retailer-set uk_ie_mainstream

    python pipeline/exports/export_retailer_product_details.py --retailer-set us_canada_top5
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "positioning_radar.db"
OUTPUT_ROOT = ROOT / "presentations" / "private_label_analysis"

RETAILER_SETS = {
    "france_mainstream": {
        "region": "FRANCE",
        "output_dir": OUTPUT_ROOT / "mainstream_france_retailers",
        "companies": [
            ("Carrefour", "carrefour"),
            ("E.Leclerc", "e_leclerc"),
            ("Intermarché", "intermarche"),
            ("Groupe Casino", "groupe_casino"),
            ("Groupe U", "groupe_u"),
            ("Auchan", "auchan"),
        ],
    },
    "uk_ie_mainstream": {
        "region": "UK_IE",
        "output_dir": OUTPUT_ROOT / "mainstream_uk_ie_retailers",
        "companies": [
            ("Tesco", "tesco"),
            ("Asda", "asda"),
            ("Sainsbury's", "sainsbury"),
            ("Morrisons", "morrisons"),
            ("Waitrose", "waitrose"),
        ],
    },
    "us_canada_top5": {
        "region": "US_CANADA",
        "output_dir": OUTPUT_ROOT / "mainstream_us_canada_retailers",
        "companies": [
            ("Walmart", "walmart"),
            ("Costco", "costco"),
            ("Kroger", "kroger"),
            ("Target", "target"),
            ("Walgreens", "walgreens"),
        ],
    },
}

REGION_ORDER = ["FRANCE", "UK_IE", "US_CANADA"]
REGION_SET = set(REGION_ORDER)
CATEGORY_ORDER = ["beverages", "cereals", "dairies", "snacks"]

OUTPUT_COLUMNS = [
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
        REGION_ORDER.index(region) if region in REGION_SET else 99,
        CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else 99,
        row.get("brand", "").lower(),
        row.get("product", "").lower(),
        row.get("GTIN", ""),
    )


def load_company_rows(
    conn: sqlite3.Connection,
    company: str,
    region: str,
) -> list[dict[str, str]]:
    brand_expr = (
        "COALESCE(NULLIF(TRIM(p.normalized_brand), ''), "
        "NULLIF(TRIM(p.primary_brand), ''), p.brands)"
    )
    query = f"""
        SELECT
            p.barcode,
            p.product_name,
            p.query_category,
            p.observed_market_region_codes,
            p.resolved_company,
            {brand_expr} AS brand,
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
          AND {brand_expr} IS NOT NULL
          AND TRIM(LOWER({brand_expr})) NOT IN ('unknown', '', 'nan')
    """
    rows: list[dict[str, str]] = []
    region_pattern = f"%|{region}|%"
    for r in conn.execute(query, (company, region_pattern)):
        rows.append(
            {
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
        )
    rows.sort(key=sort_key)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Export retailer product detail CSVs.")
    ap.add_argument(
        "--retailer-set",
        choices=sorted(RETAILER_SETS),
        default="uk_ie_mainstream",
    )
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args()

    config = RETAILER_SETS[args.retailer_set]
    region = str(config["region"])
    output_dir = Path(config["output_dir"])
    companies: list[tuple[str, str]] = config["companies"]  # type: ignore[assignment]

    print("\nFood & Beverage Positioning Radar - retailer product detail export")
    print(f"Retailer set: {args.retailer_set}")
    print(f"Region: {region}")
    print(f"Output directory: {output_dir}")

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    total_rows = 0
    for company, slug in companies:
        rows = load_company_rows(conn, company, region)
        region_slug = region.lower()
        output_path = output_dir / (
            f"{slug}_{region_slug}_products_full_macro_positioning_details.csv"
        )
        write_csv(output_path, rows)
        total_rows += len(rows)
        vision_rows = sum(1 for row in rows if row["Positioning"] != "NOT_ANALYZED")
        print(
            f"  {company}: {len(rows):,} rows, "
            f"{vision_rows:,} positioned -> {output_path}"
        )

    conn.close()
    print(f"\nDone. Wrote {len(companies)} files and {total_rows:,} rows.")


if __name__ == "__main__":
    main()
