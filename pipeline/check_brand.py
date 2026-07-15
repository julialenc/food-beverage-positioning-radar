"""
Check all brand variants starting with a given prefix.
Usage: python pipeline/check_brand.py carrefour
"""
import sqlite3
import sys
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"

prefix = sys.argv[1].lower() if len(sys.argv) > 1 else "carrefour"

conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
rows = conn.execute("""
    SELECT primary_brand, COUNT(*) as n
    FROM products
    WHERE LOWER(primary_brand) LIKE ?
      AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
    GROUP BY primary_brand
    ORDER BY n DESC
""", (f"{prefix}%",)).fetchall()
conn.close()

total = sum(n for _, n in rows)
main  = rows[0][1] if rows else 0
pct   = main / total * 100 if total else 0

print(f"\nBrands starting with '{prefix}': {len(rows)} variants, {total:,} total products")
print(f"Largest variant: '{rows[0][0]}' ({main:,} products = {pct:.1f}% of group)\n")
print(f"{'Brand':<50} {'Products':>8}  {'% of group':>10}")
print("-" * 73)
for brand, n in rows:
    bar = "█" * min(int(n / total * 40), 40)
    print(f"{brand:<50} {n:>8}  {n/total*100:>9.1f}%  {bar}")

print(f"\n{'TOTAL':<50} {total:>8}")
print(f"\n95% threshold: {total * 0.95:.0f} products")
print(f"Already unified under '{rows[0][0]}': {main:,} ({pct:.1f}%)")
if pct >= 95:
    print("✓ Above 95% — done, no further action needed.")
else:
    print(f"△ Below 95% — {total - main:,} products in {len(rows)-1} variants still unmatched.")
