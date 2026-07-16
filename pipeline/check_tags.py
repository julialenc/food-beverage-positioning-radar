"""Check the actual OFF category tags for pasta/tortilla/pizza products."""
import sqlite3
from pathlib import Path
from collections import Counter

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"
conn    = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

def top_tags(where_clause, label, limit=15):
    rows = conn.execute(f"""
        SELECT off_categories FROM products
        WHERE query_category = 'snacks' AND {where_clause}
    """).fetchall()
    tag_counter = Counter()
    for (cats,) in rows:
        if cats:
            for t in str(cats).split(","):
                t = t.strip().lower()
                if t.startswith("en:"):
                    tag_counter[t] += 1
    print(f"\n=== Top OFF tags — {label} (n={len(rows)}) ===")
    for tag, n in tag_counter.most_common(limit):
        print(f"  {tag:<50} {n:>5}")

top_tags("LOWER(off_categories) LIKE '%pasta%' OR LOWER(off_categories) LIKE '%tortellini%' OR LOWER(off_categories) LIKE '%ravioli%' OR LOWER(off_categories) LIKE '%gnocchi%'", "PASTA", 15)
top_tags("LOWER(off_categories) LIKE '%tortilla%' AND LOWER(product_name) NOT LIKE '%chip%'", "TORTILLAS (non-chip)", 15)
top_tags("LOWER(off_categories) LIKE '%pizza%'", "PIZZA", 15)
conn.close()
