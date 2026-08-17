"""
Shows brand mapping coverage against company_brand_mapping.csv.
Scoped/manual-review mappings are reported separately from direct mappings.

Usage: python pipeline/check_unmapped.py
"""
import csv
import sqlite3
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent
DB_PATH      = ROOT / "database" / "positioning_radar.db"
MAPPING_PATH = ROOT / "data" / "reference" / "company_brand_mapping.csv"

def norm(b):
    return b.lower().replace("-", " ").strip()

# Load mapping statuses by primary_brand_db. Blank status means legacy/direct.
mapped_statuses = {}
with open(MAPPING_PATH, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        b = row.get("primary_brand_db", "").strip()
        if b:
            status = row.get("ownership_resolution_status", "").strip().lower() or "direct"
            mapped_statuses.setdefault(norm(b), set()).add(status)

conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
rows = conn.execute("""
    SELECT primary_brand, COUNT(*) as n
    FROM products
    WHERE primary_brand IS NOT NULL
      AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
    GROUP BY primary_brand
    ORDER BY n DESC
""").fetchall()
conn.close()

direct_mapped = []
scoped_or_review = []
unmapped = []

for brand, n in rows:
    statuses = mapped_statuses.get(norm(brand))
    if not statuses:
        unmapped.append((brand, n))
    elif statuses == {"direct"}:
        direct_mapped.append((brand, n))
    else:
        scoped_or_review.append((brand, n, statuses))

total_unmapped_products = sum(n for _, n in unmapped)
total_scoped_products    = sum(n for _, n, _ in scoped_or_review)
total_products          = sum(n for _, n in rows)
brands_under_10         = sum(1 for _, n in unmapped if n < 10)
manual_review_brands    = [
    (brand, n, statuses)
    for brand, n, statuses in scoped_or_review
    if "manual_review" in statuses
]

print(f"Total distinct brands in DB:    {len(rows):,}")
print(f"Total products with a brand:     {total_products:,}")
print(f"Resolved direct mappings:        {len(direct_mapped):,}")
print(f"Scoped/manual-review mappings:   {len(scoped_or_review):,}  ({total_scoped_products:,} products)")
print(f"  with manual-review fallback:   {len(manual_review_brands):,} brands")
print(f"Unmapped (Other):               {len(unmapped):,}  ({total_unmapped_products:,} products)")
print(f"  of which < 10 products:       {brands_under_10:,} brands")
print(f"  of which >= 10 products:      {len(unmapped) - brands_under_10:,} brands")
print(f"\nTop 40 unmapped brands (>= 10 products):")
print(f"{'Brand':<45} {'Products':>8}")
print("-" * 56)
shown = 0
for brand, n in unmapped:
    if n >= 10:
        print(f"{brand:<45} {n:>8}")
        shown += 1
        if shown >= 40:
            break

if scoped_or_review:
    print(f"\nTop scoped/manual-review mapped brands:")
    print(f"{'Brand':<45} {'Products':>8}  Statuses")
    print("-" * 75)
    for brand, n, statuses in scoped_or_review[:20]:
        status_text = ", ".join(sorted(statuses))
        print(f"{brand:<45} {n:>8}  {status_text}")
