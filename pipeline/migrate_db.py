"""
migrate_db.py
--------------
Adds the four columns required by the v4 vision pipeline to the
product_analysis table. Safe to run more than once — skips any column
that already exists.

Run this BEFORE merge_scores.py.

Usage:
    python pipeline/migrate_db.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "positioning_radar.db"

TO_ADD = {
    "image_context":           "TEXT",
    "claim_extraction_status": "TEXT",
    "detected_claim_phrases":  "TEXT",
    "claims_json":             "TEXT",
    # Release scoping. NULL means the row is not part of any published
    # release — e.g. a superseded pilot observation. The app must filter on
    # this column, never on claim_source='vision'.
    "release_run_id":          "TEXT",
    # Sampling frame. The sample was designed, quota'd and weighted on
    # sampling_region — NOT on products.primary_country, which reflects
    # where a product was tagged in OFF and spans 80+ values inside this
    # release. Any regional breakdown must group on sampling_region.
    "sampling_region":         "TEXT",
    "sampling_category":       "TEXT",
    "sample_component":        "TEXT",
    "primary_stratum_id":      "TEXT",
    "sampling_weight":         "REAL",
}

conn = sqlite3.connect(DB_PATH)
existing = [r[1] for r in conn.execute("PRAGMA table_info(product_analysis)")]

for col, dtype in TO_ADD.items():
    if col not in existing:
        conn.execute(f"ALTER TABLE product_analysis ADD COLUMN {col} {dtype}")
        print(f"  Added:          {col} ({dtype})")
    else:
        print(f"  Already exists: {col}")

conn.commit()
conn.close()
print("Done.")
