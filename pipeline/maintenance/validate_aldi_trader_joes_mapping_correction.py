"""Validate the Aldi / Trader Joe's exact-GTIN correction in local DB outputs."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OVERRIDE_PATH = (
    ROOT / "data" / "01_reference_inputs" / "05_reviewed_product_mapping_overrides.csv"
)
DB_PATHS = [
    ROOT / "database" / "positioning_radar.db",
    ROOT / "database" / "positioning_radar_public_mvp.db",
]
SOURCE = "aldi_trader_joes_mapping_correction_20260914"
EXCEPTION_GTINS = ["35835066", "72326565", "29022618"]


def load_gtins() -> list[str]:
    gtins: list[str] = []
    with OVERRIDE_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (
                (row.get("status") or "").strip().lower() == "active"
                and (row.get("source") or "").strip() == SOURCE
            ):
                gtins.append((row.get("gtin") or "").strip())
    return sorted(set(gtins))


def main() -> None:
    gtins = load_gtins()
    placeholders = ",".join("?" for _ in gtins)
    print(f"Override GTINs: {len(gtins)}")

    for db_path in DB_PATHS:
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            found = cur.execute(
                f"SELECT COUNT(*) FROM products WHERE barcode IN ({placeholders})",
                gtins,
            ).fetchone()[0]
            print(f"\n{db_path.relative_to(ROOT)}")
            print(f"Matched products: {found}")
            print(f"Missing products: {len(gtins) - found}")

            cur.execute(
                f"""
                SELECT resolved_company, COUNT(*)
                FROM products
                WHERE barcode IN ({placeholders})
                GROUP BY resolved_company
                ORDER BY resolved_company
                """,
                gtins,
            )
            print("Resolved-company split:")
            for company, count in cur.fetchall():
                print(f"  {company}: {count}")

            print("Exception GTIN checks:")
            product_columns = {
                row[1] for row in cur.execute("PRAGMA table_info(products)").fetchall()
            }
            source_expr = (
                "company_mapping_source"
                if "company_mapping_source" in product_columns
                else "NULL AS company_mapping_source"
            )
            for gtin in EXCEPTION_GTINS:
                row = cur.execute(
                    f"""
                    SELECT normalized_brand, resolved_company, {source_expr}
                    FROM products
                    WHERE barcode = ?
                    """,
                    (gtin,),
                ).fetchone()
                print(f"  {gtin}: {row}")

            vision_count = cur.execute(
                "SELECT COUNT(*) FROM product_analysis WHERE claim_source = 'vision'"
            ).fetchone()[0]
            print(f"Vision claim_source rows: {vision_count}")
        finally:
            conn.close()


if __name__ == "__main__":
    main()
