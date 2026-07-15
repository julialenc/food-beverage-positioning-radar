"""
Brand counts — shows how many products each brand has, by category.
Run this to identify brands that may need manual unification review.
Output: data/reference/brand_counts.csv (open in Excel to review)

Usage: python pipeline/brand_counts.py
"""
import csv
import sqlite3
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"
OUT     = ROOT / "data" / "reference" / "brand_counts.csv"

conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

# Total count per brand across all categories
rows = conn.execute("""
    SELECT
        primary_brand,
        COUNT(*) as total_products,
        GROUP_CONCAT(DISTINCT query_category) as categories
    FROM products
    WHERE primary_brand IS NOT NULL
      AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
    GROUP BY primary_brand
    ORDER BY total_products DESC
""").fetchall()
conn.close()

with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["primary_brand", "total_products", "categories", "action"])
    for brand, n, cats in rows:
        writer.writerow([brand, n, cats, ""])

print(f"Saved {len(rows):,} brands → {OUT}")
print(f"\nTop 30 brands by product count:")
print(f"{'Brand':<40} {'Products':>8}  Categories")
print("-" * 75)
for brand, n, cats in rows[:30]:
    print(f"{brand:<40} {n:>8}  {cats}")
