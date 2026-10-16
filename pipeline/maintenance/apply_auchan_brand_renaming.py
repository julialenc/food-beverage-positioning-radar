"""Apply reviewed Auchan France GTIN-level brand renaming decisions.

The source review file is expected to contain:
region, category, company, brand (as it is now), GTIN, product name, new brand.

Only rows where new brand differs from the current brand are written as exact
reviewed product overrides and applied to derived brand fields in SQLite.
Raw Open Food Facts values are not changed.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "positioning_radar.db"
OVERRIDE_PATH = (
    ROOT / "data" / "01_reference_inputs" / "05_reviewed_product_mapping_overrides.csv"
)
DEFAULT_REVIEW_PATH = (
    Path.home()
    / "OneDrive"
    / "Desktop"
    / "Downloads_temp"
    / "auchan_france_brand_renaming.csv"
)
DEFAULT_SOURCE = "auchan_france_brand_renaming_20260916"
DEFAULT_AUDIT_SOURCE = (
    "Auchan brand governance update.md; auchan_france_brand_renaming.csv"
)


def norm(value: object) -> str:
    return str(value or "").strip()


def load_review_changes(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    changes: list[dict[str, str]] = []
    seen: dict[str, str] = {}
    for row in rows:
        old_brand = norm(row.get("brand (as it is now)"))
        new_brand = norm(row.get("new brand"))
        gtin = norm(row.get("GTIN"))
        if not gtin or not new_brand or new_brand == old_brand:
            continue
        if gtin in seen and seen[gtin] != new_brand:
            raise ValueError(f"Conflicting new brand decisions for GTIN {gtin}")
        seen[gtin] = new_brand
        changes.append(
            {
                "gtin": gtin,
                "region": norm(row.get("region")),
                "category": norm(row.get("category")),
                "company": norm(row.get("company")) or "Auchan",
                "old_brand": old_brand,
                "new_brand": new_brand,
                "product_name": norm(row.get("product name")),
            }
        )
    return changes


def append_overrides(
    changes: list[dict[str, str]],
    source: str,
    audit_source: str,
) -> tuple[int, list[str]]:
    with OVERRIDE_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        existing_rows = list(csv.DictReader(f))
        fieldnames = list(existing_rows[0].keys())

    active_by_gtin = {
        norm(row.get("gtin")): row
        for row in existing_rows
        if norm(row.get("status")).lower() == "active"
    }

    appended = 0
    skipped: list[str] = []
    reviewed_at = date.today().isoformat()
    for change in changes:
        gtin = change["gtin"]
        existing = active_by_gtin.get(gtin)
        if existing:
            if (
                norm(existing.get("reviewed_brand")) == change["new_brand"]
                and norm(existing.get("reviewed_company")) in {"", change["company"]}
            ):
                skipped.append(gtin)
                continue
            raise ValueError(
                "Active override already exists for GTIN "
                f"{gtin}: reviewed_brand={existing.get('reviewed_brand')!r}, "
                f"reviewed_company={existing.get('reviewed_company')!r}"
            )

        existing_rows.append(
            {
                "gtin": gtin,
                "region": change["region"],
                "reviewed_brand": change["new_brand"],
                "reviewed_company": change["company"],
                "reviewed_category": "",
                "source": source,
                "status": "active",
                "audit_note": (
                    "Auchan France reviewed brand correction: "
                    f"{change['old_brand']} -> {change['new_brand']}; "
                    f"product={change['product_name']}"
                ),
                "audit_basis": "exact_gtin_reviewed_brand_renaming",
                "audit_source": audit_source,
                "reviewed_at": reviewed_at,
            }
        )
        active_by_gtin[gtin] = existing_rows[-1]
        appended += 1

    with OVERRIDE_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(existing_rows)

    return appended, skipped


def apply_to_database(
    changes: list[dict[str, str]],
    db_path: Path,
    source: str,
) -> tuple[int, list[str]]:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        updated = 0
        missing: list[str] = []
        with conn:
            for change in changes:
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
                    (
                        change["new_brand"],
                        change["new_brand"],
                        source,
                        change["company"],
                        source,
                        change["gtin"],
                    ),
                )
                if cur.rowcount:
                    updated += cur.rowcount
                else:
                    missing.append(change["gtin"])
        return updated, missing
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Auchan France brand renaming.")
    parser.add_argument("--review-csv", default=str(DEFAULT_REVIEW_PATH))
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--audit-source", default=DEFAULT_AUDIT_SOURCE)
    args = parser.parse_args()

    changes = load_review_changes(Path(args.review_csv))
    appended, skipped = append_overrides(changes, args.source, args.audit_source)
    updated, missing = apply_to_database(changes, Path(args.db), args.source)

    print(f"review_changes={len(changes)}")
    print(f"overrides_appended={appended}")
    print(f"overrides_already_present={len(skipped)}")
    print(f"database_rows_updated={updated}")
    print(f"database_missing_gtins={len(missing)}")
    if missing:
        for gtin in missing:
            print(f"missing_gtin={gtin}")


if __name__ == "__main__":
    main()
