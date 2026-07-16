"""
Shows the top unmapped brands (not in company_brand_mapping.csv).
These appear under "Other / not mapped to a company" in the app filter.

Usage: python pipeline/check_unmapped.py
"""
import csv
import sqlite3
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent
DB_PATH      = ROOT / "database" / "positioning_radar.db"
MAPPING_PATH = ROOT / "data" / "reference" / "company_brand_mapping.csv"

# Load all mapped primary_brand_db values
mapped = set()
with open(MAPPING_PATH, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        b = row.get("primary_brand_db", "").strip().lower()
        if b:
            mapped.add(b)

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

# Filter to unmapped brands — normalise same way as db.py
def norm(b):
    return b.lower().replace("-", " ")

unmapped = [(b, n) for b, n in rows if norm(b) not in {norm(m) for m in mapped}]

total_unmapped_products = sum(n for _, n in unmapped)
total_products          = sum(n for _, n in rows)
brands_under_10         = sum(1 for _, n in unmapped if n < 10)

print(f"Total distinct brands in DB:    {len(rows):,}")
print(f"Mapped to a company:            {len(rows) - len(unmapped):,}")
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
