"""
Export regional-category orphan candidates from the current products snapshot.

An orphan candidate is a normalized consumer-facing brand whose resolved
company is `Other / not mapped to a company` and whose product count reaches
the threshold within one region x category bucket.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "positioning_radar.db"
OUT_DIR = ROOT / "data" / "test"
OTHER = "Other / not mapped to a company"
DEFAULT_REGIONS = ("FRANCE", "UK_IE", "US_CANADA")
NON_REVIEWABLE_BRAND_KEYS = {
    "",
    "nan",
    "unknown",
    "le fromager des halles",
    "sans marque",
}

REVIEWED_OTHER_GTINS = {
    # US_CANADA reviewed conservative false negatives from the 2026-09-03
    # regional-category orphan audit. These remain Other intentionally.
    "33876863",
    "76721206434",
    "37578617163",
    "850668000757",
    "3003409974",
    "75450128994",
    "720495121768",
    "728036000152",
    "77890407936",
    "780993330130",
    "86854060254",
    "82666400301",
    "21130299492",
    "73416000421",
    "98487300089",
    "52548550363",
    "708615006140",
    "92825093206",
    "41780271631",
    "799665050436",
    "652729104134",
    "14000006382",
}


def clean_key(value: str) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = text.replace("&", " and ")
    for char in "'`´’":
        text = text.replace(char, "")
    out = []
    last_space = True
    for char in text:
        if char.isalnum():
            out.append(char)
            last_space = False
        elif not last_space:
            out.append(" ")
            last_space = True
    return "".join(out).strip()


def export_orphans(regions: tuple[str, ...], threshold: int, output: Path) -> tuple[int, int]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    latest = conn.execute("SELECT MAX(ingested_at) FROM products").fetchone()[0]
    rows = conn.execute(
        """
        SELECT
            barcode,
            product_name,
            query_category AS category,
            COALESCE(NULLIF(TRIM(normalized_brand), ''), primary_brand) AS brand,
            observed_market_region_codes
        FROM products
        WHERE ingested_at = ?
          AND TRIM(COALESCE(resolved_company, '')) = ?
          AND query_category IS NOT NULL
          AND TRIM(query_category) <> ''
        """,
        (latest, OTHER),
    ).fetchall()
    conn.close()

    expanded = []
    seen = set()
    for row in rows:
        brand = str(row["brand"] or "").strip()
        if clean_key(brand) in NON_REVIEWABLE_BRAND_KEYS:
            continue
        category = str(row["category"] or "").strip()
        gtin = str(row["barcode"] or "").strip()
        if gtin in REVIEWED_OTHER_GTINS:
            continue
        product = str(row["product_name"] or "").strip()
        row_regions = set(str(row["observed_market_region_codes"] or "").split("|"))
        for region in regions:
            if region not in row_regions:
                continue
            key = (region, category, brand, gtin)
            if key in seen:
                continue
            seen.add(key)
            expanded.append({
                "region": region,
                "category": category,
                "brand": brand,
                "GTIN": gtin,
                "product": product,
            })

    counts = Counter((r["region"], r["category"], r["brand"]) for r in expanded)
    qualifying = {bucket for bucket, count in counts.items() if count >= threshold}
    out_rows = [
        row for row in expanded
        if (row["region"], row["category"], row["brand"]) in qualifying
    ]
    out_rows.sort(
        key=lambda r: (
            r["region"],
            r["category"],
            r["brand"].casefold(),
            r["product"].casefold(),
            r["GTIN"],
        )
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["region", "category", "brand", "GTIN", "product"])
        writer.writeheader()
        writer.writerows(out_rows)
    return len(qualifying), len(out_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", action="append", choices=DEFAULT_REGIONS)
    parser.add_argument("--threshold", type=int, default=100)
    parser.add_argument(
        "--output",
        default=str(OUT_DIR / "orphan_candidates_100_region_category.csv"),
    )
    args = parser.parse_args()

    regions = tuple(args.region) if args.region else DEFAULT_REGIONS
    bucket_count, row_count = export_orphans(regions, args.threshold, Path(args.output))
    print(f"qualifying_buckets={bucket_count}")
    print(f"export_rows={row_count}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
