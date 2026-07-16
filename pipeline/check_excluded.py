"""
Check products that would be excluded from snacks by the pasta/tortilla/pizza rule.
Helps verify the exclusion logic before applying it to bootstrap.py.

Usage: python pipeline/check_excluded.py
"""
import sqlite3
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"

conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

print("=" * 65)
print("PASTA products in snacks (sample)")
print("=" * 65)
rows = conn.execute("""
    SELECT primary_brand, product_name, off_categories
    FROM products
    WHERE query_category = 'snacks'
      AND (LOWER(off_categories) LIKE '%pasta%'
        OR LOWER(off_categories) LIKE '%tortellini%'
        OR LOWER(off_categories) LIKE '%ravioli%'
        OR LOWER(off_categories) LIKE '%gnocchi%'
        OR LOWER(off_categories) LIKE '%lasagne%')
    ORDER BY primary_brand
    LIMIT 20
""").fetchall()
print(f"Count: {len(rows)}")
for brand, name, cats in rows:
    print(f"  {brand:<20} {name[:35]:<35}")

print()
print("=" * 65)
print("TORTILLA products in snacks (sample)")
print("=" * 65)
rows = conn.execute("""
    SELECT primary_brand, product_name, off_categories
    FROM products
    WHERE query_category = 'snacks'
      AND (LOWER(off_categories) LIKE '%tortilla%'
        OR LOWER(off_categories) LIKE '%wrap%'
        OR LOWER(off_categories) LIKE '%mexican%')
    ORDER BY primary_brand
    LIMIT 20
""").fetchall()
print(f"Count: {len(rows)}")
for brand, name, cats in rows:
    print(f"  {brand:<20} {name[:35]:<35}")

print()
print("=" * 65)
print("PIZZA products in snacks (sample) — review before excluding")
print("=" * 65)
rows = conn.execute("""
    SELECT primary_brand, product_name, off_categories
    FROM products
    WHERE query_category = 'snacks'
      AND LOWER(off_categories) LIKE '%pizza%'
    ORDER BY primary_brand
    LIMIT 30
""").fetchall()
print(f"Count: {len(rows)}")
for brand, name, cats in rows:
    print(f"  {brand:<20} {name[:40]:<40}")

conn.close()
