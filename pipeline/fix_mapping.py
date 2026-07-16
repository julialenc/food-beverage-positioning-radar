"""
Fix milbona (Aldi → Lidl) and add migros, nespresso, mondelez, tops.
Usage: python pipeline/fix_mapping.py
"""
from pathlib import Path

ROOT   = Path(__file__).resolve().parent.parent
TARGET = ROOT / "data" / "reference" / "company_brand_mapping.csv"

# Read full file
lines = TARGET.read_text(encoding="utf-8-sig").splitlines()

# Fix milbona: change parent_company from Aldi to Lidl
fixed = 0
new_lines = []
for line in lines:
    if line.startswith("Aldi,milbona,"):
        line = line.replace("Aldi,milbona,", "Lidl,milbona,", 1)
        fixed += 1
    new_lines.append(line)

print(f"Milbona fix: {fixed} line(s) updated (Aldi → Lidl)")

# Check what's already mapped to avoid duplicates
import csv, io
reader = csv.DictReader(io.StringIO("\n".join(new_lines)))
existing = {row.get("primary_brand_db","").strip().lower() for row in reader}

# New rows to add
new_rows = [
    "Migros,migros,migros,snacks,CH,Swiss cooperative retailer and own-label brand",
    "Nestlé,nespresso,nespresso,beverages,CH,Premium coffee system — Nestlé brand",
    "Mondelez,mondelez,mondelez,snacks,US,Parent company brand used directly on some products",
    "Tops Friendly Markets,tops,tops,snacks,US,US regional supermarket chain (Northeast)",
]

added = 0
for row in new_rows:
    brand_db = row.split(",")[2].strip().lower()
    if brand_db not in existing:
        new_lines.append(row)
        existing.add(brand_db)
        added += 1
        print(f"  Added: {row.split(',')[0]} / {brand_db}")
    else:
        print(f"  Skipped (already mapped): {brand_db}")

TARGET.write_text("\n".join(new_lines), encoding="utf-8")
print(f"\nDone. {added} rows added, file now has {len(new_lines)} lines.")
