"""
Build a compact SQLite database for the public Streamlit MVP.

The full local database keeps pipeline history, backups, and audit-heavy
material. The public app only needs the current MVP product universe and the
tables queried by Streamlit.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import gzip
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DB = REPO_ROOT / "database" / "positioning_radar.db"
PUBLIC_DB = REPO_ROOT / "database" / "positioning_radar_public_mvp.db"
PUBLIC_DB_GZ = PUBLIC_DB.with_suffix(PUBLIC_DB.suffix + ".gz")

MVP_REGIONS = ("FRANCE", "UK_IE", "US_CANADA")
MVP_CATEGORIES = ("snacks", "cereals", "dairies", "beverages")

APP_TABLES = {
    "products",
    "product_analysis",
    "region_category_benchmarks",
    "profile_intersections",
    "category_region_averages",
}

PUBLIC_PRODUCT_COLUMNS = (
    "barcode",
    "product_name",
    "brands",
    "primary_brand",
    "normalized_brand",
    "brand_entity_raw",
    "brand_entity_source",
    "resolved_company",
    "quantity",
    "query_category",
    "off_categories",
    "countries",
    "primary_country",
    "observed_market_region_codes",
    "image_url",
    "ingredients_text",
    "energy_kcal",
    "fat_100g",
    "saturated_fat_100g",
    "carbs_100g",
    "sugars_100g",
    "fiber_100g",
    "protein_100g",
    "salt_100g",
    "nutriscore_grade",
    "nova_group",
    "completeness_score",
    "ingested_at",
)


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone() is not None


def get_create_sql(cur: sqlite3.Cursor, table: str) -> str:
    row = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    if row is None or not row[0]:
        raise RuntimeError(f"Missing CREATE TABLE SQL for {table}")
    return row[0]


def copy_schema(src: sqlite3.Connection, dst: sqlite3.Connection, table: str) -> None:
    src_cur = src.cursor()
    if table == "products":
        dst.execute("""
            CREATE TABLE products (
                barcode TEXT PRIMARY KEY,
                product_name TEXT,
                brands TEXT,
                primary_brand TEXT,
                normalized_brand TEXT,
                brand_entity_raw TEXT,
                brand_entity_source TEXT,
                resolved_company TEXT,
                quantity TEXT,
                query_category TEXT,
                off_categories TEXT,
                countries TEXT,
                primary_country TEXT,
                observed_market_region_codes TEXT,
                image_url TEXT,
                ingredients_text TEXT,
                energy_kcal REAL,
                fat_100g REAL,
                saturated_fat_100g REAL,
                carbs_100g REAL,
                sugars_100g REAL,
                fiber_100g REAL,
                protein_100g REAL,
                salt_100g REAL,
                nutriscore_grade TEXT,
                nova_group REAL,
                completeness_score INTEGER,
                ingested_at TEXT
            )
        """)
        return
    if table == "product_analysis":
        dst.execute("""
            CREATE TABLE product_analysis (
                barcode TEXT PRIMARY KEY,
                pack_claims_found TEXT,
                claim_source TEXT
            )
        """)
        return
    dst.execute(get_create_sql(src_cur, table))


def copy_products(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    placeholders_regions = ",".join("?" for _ in MVP_REGIONS)
    placeholders_categories = ",".join("?" for _ in MVP_CATEGORIES)
    columns = ", ".join(quote_ident(col) for col in PUBLIC_PRODUCT_COLUMNS)
    sql = f"""
        INSERT INTO products ({columns})
        SELECT {columns}
        FROM src.products
        WHERE ingested_at = (SELECT MAX(ingested_at) FROM src.products)
          AND query_category IN ({placeholders_categories})
          AND (
              observed_market_region_codes IN ({placeholders_regions})
              OR observed_market_region_codes LIKE '%FRANCE%'
              OR observed_market_region_codes LIKE '%UK_IE%'
              OR observed_market_region_codes LIKE '%US_CANADA%'
          )
    """
    dst.execute(sql, (*MVP_CATEGORIES, *MVP_REGIONS))


def copy_product_analysis(dst: sqlite3.Connection) -> None:
    dst.execute("""
        INSERT INTO product_analysis (barcode, pack_claims_found, claim_source)
        SELECT a.barcode, a.pack_claims_found, a.claim_source
        FROM src.product_analysis a
        INNER JOIN products p ON p.barcode = a.barcode
    """)


def copy_latest_snapshot_table(dst: sqlite3.Connection, table: str) -> None:
    dst.execute(f"""
        INSERT INTO {quote_ident(table)}
        SELECT *
        FROM src.{quote_ident(table)}
        WHERE snapshot = (SELECT MAX(snapshot) FROM src.{quote_ident(table)})
    """)


def copy_category_region_averages(dst: sqlite3.Connection) -> None:
    dst.execute("""
        INSERT INTO category_region_averages
        SELECT *
        FROM src.category_region_averages
        WHERE snapshot = (
            SELECT MAX(snapshot) FROM src.category_region_averages
        )
    """)


def create_indexes(dst: sqlite3.Connection) -> None:
    index_sql = [
        "CREATE INDEX IF NOT EXISTS idx_products_current_scope "
        "ON products(ingested_at, query_category, observed_market_region_codes)",
        "CREATE INDEX IF NOT EXISTS idx_products_brand "
        "ON products(normalized_brand, primary_brand)",
        "CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode)",
        "CREATE INDEX IF NOT EXISTS idx_product_analysis_barcode "
        "ON product_analysis(barcode)",
        "CREATE INDEX IF NOT EXISTS idx_benchmarks_snapshot "
        "ON region_category_benchmarks(snapshot, region_code, category)",
        "CREATE INDEX IF NOT EXISTS idx_profile_snapshot "
        "ON profile_intersections(snapshot, region_code, category)",
        "CREATE INDEX IF NOT EXISTS idx_category_avg_snapshot "
        "ON category_region_averages(snapshot, region, query_category)",
    ]
    for sql in index_sql:
        dst.execute(sql)


def count(cur: sqlite3.Cursor, table: str) -> int:
    return int(cur.execute(f"SELECT COUNT(*) FROM {quote_ident(table)}").fetchone()[0])


def main() -> None:
    if not SOURCE_DB.exists():
        raise FileNotFoundError(f"Source database not found: {SOURCE_DB}")

    if PUBLIC_DB.exists():
        PUBLIC_DB.unlink()
    if PUBLIC_DB_GZ.exists():
        PUBLIC_DB_GZ.unlink()

    src = sqlite3.connect(SOURCE_DB)
    dst = sqlite3.connect(PUBLIC_DB)
    dst.execute(f"ATTACH DATABASE {str(SOURCE_DB)!r} AS src")

    try:
        for table in sorted(APP_TABLES):
            if table_exists(src.cursor(), table):
                copy_schema(src, dst, table)

        copy_products(src, dst)
        copy_product_analysis(dst)

        if table_exists(src.cursor(), "region_category_benchmarks"):
            copy_latest_snapshot_table(dst, "region_category_benchmarks")
        if table_exists(src.cursor(), "profile_intersections"):
            copy_latest_snapshot_table(dst, "profile_intersections")
        if table_exists(src.cursor(), "category_region_averages"):
            copy_category_region_averages(dst)

        create_indexes(dst)
        dst.commit()
        dst.execute("VACUUM")
    finally:
        dst.close()
        src.close()

    size_mb = os.path.getsize(PUBLIC_DB) / 1024 / 1024
    with open(PUBLIC_DB, "rb") as src, gzip.open(PUBLIC_DB_GZ, "wb", compresslevel=9) as dst:
        shutil.copyfileobj(src, dst)
    gz_size_mb = os.path.getsize(PUBLIC_DB_GZ) / 1024 / 1024

    print(f"Created {PUBLIC_DB}")
    print(f"Size: {size_mb:.1f} MB")
    print(f"Created {PUBLIC_DB_GZ}")
    print(f"Compressed size: {gz_size_mb:.1f} MB")

    con = sqlite3.connect(PUBLIC_DB)
    cur = con.cursor()
    for table in sorted(APP_TABLES):
        if table_exists(cur, table):
            print(f"{table}: {count(cur, table):,}")
    con.close()


if __name__ == "__main__":
    main()
