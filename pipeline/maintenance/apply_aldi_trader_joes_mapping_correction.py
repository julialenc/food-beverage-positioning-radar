"""Apply the reviewed Aldi / Trader Joe's exact-GTIN mapping correction.

This maintenance step updates only derived brand/company routing fields in the
local products table. It does not touch raw Open Food Facts values, product
nutrition, or OCR/LLM claim-enrichment tables.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "positioning_radar.db"
OVERRIDE_PATH = (
    ROOT / "data" / "01_reference_inputs" / "05_reviewed_product_mapping_overrides.csv"
)
SOURCE = "aldi_trader_joes_mapping_correction_20260914"


def load_correction_rows() -> list[dict[str, str]]:
    with OVERRIDE_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        rows = [
            row
            for row in csv.DictReader(f)
            if (row.get("status") or "").strip().lower() == "active"
            and (row.get("source") or "").strip() == SOURCE
            and (row.get("gtin") or "").strip()
        ]

    seen: dict[str, dict[str, str]] = {}
    for row in rows:
        gtin = (row.get("gtin") or "").strip()
        if gtin in seen:
            prior = seen[gtin]
            if (
                (prior.get("reviewed_brand") or "").strip()
                != (row.get("reviewed_brand") or "").strip()
                or (prior.get("reviewed_company") or "").strip()
                != (row.get("reviewed_company") or "").strip()
            ):
                raise ValueError(f"Conflicting reviewed decisions for GTIN {gtin}")
            continue
        seen[gtin] = row

    return list(seen.values())


def main() -> None:
    rows = load_correction_rows()
    if not rows:
        raise SystemExit(f"No active {SOURCE} rows found in {OVERRIDE_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        matched = 0
        missing: list[str] = []

        with conn:
            for row in rows:
                gtin = (row.get("gtin") or "").strip()
                brand = (row.get("reviewed_brand") or "").strip()
                company = (row.get("reviewed_company") or "").strip()
                if not brand or not company:
                    raise ValueError(f"Missing reviewed brand/company for GTIN {gtin}")

                cur.execute(
                    """
                    UPDATE products
                    SET normalized_brand = ?,
                        brand_family = ?,
                        brand_alias_source = ?,
                        brand_alias_review_status = 'reviewed_product_override',
                        resolved_company = ?,
                        company_ownership_resolution_status = 'reviewed_product_override',
                        company_mapping_source = ?
                    WHERE barcode = ?
                    """,
                    (brand, brand, SOURCE, company, SOURCE, gtin),
                )
                if cur.rowcount:
                    matched += cur.rowcount
                else:
                    missing.append(gtin)

        print(f"Source: {SOURCE}")
        print(f"Override rows: {len(rows)}")
        print(f"Products updated: {matched}")
        print(f"Products not found: {len(missing)}")
        if missing:
            print("Missing GTINs:")
            for gtin in missing:
                print(f"  {gtin}")

        cur.execute(
            """
            SELECT resolved_company, COUNT(*)
            FROM products
            WHERE company_mapping_source = ?
            GROUP BY resolved_company
            ORDER BY resolved_company
            """,
            (SOURCE,),
        )
        print("Resolved-company split:")
        for company, count in cur.fetchall():
            print(f"  {company}: {count}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
