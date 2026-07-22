"""
clear_stale_vision.py
---------------------
Clears vision and claim-tagging fields for every product that carries a
vision observation but is NOT part of the current release.

Why this exists
  tag_claims.py recalculates all 512,937 products, so every product that
  ever received a successful vision observation is tagged
  claim_source='vision' — including prompt v1/v2 pilot runs that the
  release supersedes. That inflates the vision population (15,106) well
  above the true release denominator (11,408).

  This script resets those superseded rows so claim_source='vision'
  becomes trustworthy, and release_run_id scoping becomes redundant
  rather than load-bearing. Run both; belt and braces.

What is cleared (only for products OUTSIDE the release):
    pack_analysis_attempted, ocr_text, ocr_status, llm_status,
    vision_model, prompt_version, pack_analysis_timestamp,
    image_context, claim_extraction_status, detected_claim_phrases,
    claims_json, pack_claims_found, release_run_id,
    claim_source, claim_category_1, claim_category_2,
    claim_benchmark_intersections

What is never touched:
    ingredient-stage signals, nutrition values, nutrition_benchmark_flags,
    formulation families, sampling metadata, analyzed_at, and every
    product inside the release.

The pilot results remain available in the archived run CSVs — nothing
irrecoverable is lost.

Usage:
    python pipeline/clear_stale_vision.py --release data/sample/us_release_sample.csv ^
                                          --release data/sample/uk_release_sample.csv --dry-run
    python pipeline/clear_stale_vision.py --release data/sample/us_release_sample.csv ^
                                          --release data/sample/uk_release_sample.csv
"""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH   = REPO_ROOT / "database" / "positioning_radar.db"

RESET_FIELDS = [
    "pack_analysis_attempted = 0",
    "pack_claims_found       = NULL",
    "image_context           = NULL",
    "claim_extraction_status = NULL",
    "detected_claim_phrases  = NULL",
    "claims_json             = NULL",
    "ocr_text                = NULL",
    "ocr_status              = NULL",
    "llm_status              = NULL",
    "vision_model            = NULL",
    "prompt_version          = NULL",
    "pack_analysis_timestamp = NULL",
    "release_run_id          = NULL",
    "claim_source            = NULL",
    "claim_category_1        = NULL",
    "claim_category_2        = NULL",
    "claim_benchmark_intersections = NULL",
]


def main():
    ap = argparse.ArgumentParser(
        description="Clear vision observations outside the current release."
    )
    ap.add_argument("--release", action="append", required=True,
                    help="Release sample CSV (repeat for each region)")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print(f"\nFood & Beverage Positioning Radar - clear_stale_vision.py")
    print(f"{'DRY RUN — no changes will be written' if args.dry_run else 'LIVE RUN'}")

    # ── Collect release barcodes ──────────────────────────────────────────────
    barcodes = set()
    for path in args.release:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        df = pd.read_csv(p, usecols=["barcode"], dtype={"barcode": str})
        barcodes |= set(df["barcode"].dropna().astype(str))
        print(f"  {p.name}: {len(df):,} barcodes")
    print(f"  Release population: {len(barcodes):,} unique barcodes")

    conn = sqlite3.connect(args.db)

    conn.execute("DROP TABLE IF EXISTS temp.release_scope")
    conn.execute("CREATE TEMP TABLE release_scope (barcode TEXT PRIMARY KEY)")
    conn.executemany(
        "INSERT OR IGNORE INTO release_scope (barcode) VALUES (?)",
        ((b,) for b in barcodes),
    )

    (attempted,) = conn.execute("""
        SELECT COUNT(*) FROM product_analysis
        WHERE pack_analysis_attempted = 1
    """).fetchone()

    (stale,) = conn.execute("""
        SELECT COUNT(*) FROM product_analysis
        WHERE pack_analysis_attempted = 1
          AND barcode NOT IN (SELECT barcode FROM release_scope)
    """).fetchone()

    print(f"\n  Products with a vision observation: {attempted:,}")
    print(f"  Inside the release:                 {attempted - stale:,}")
    print(f"  Superseded (to clear):              {stale:,}")

    if stale:
        print(f"\n  Sample of superseded rows:")
        rows = conn.execute("""
            SELECT a.barcode, p.product_name, a.prompt_version
            FROM product_analysis a
            LEFT JOIN products p ON p.barcode = a.barcode
            WHERE a.pack_analysis_attempted = 1
              AND a.barcode NOT IN (SELECT barcode FROM release_scope)
            LIMIT 10
        """).fetchall()
        for bc, name, pv in rows:
            print(f"    {bc:<16} {str(name)[:44]:<46} prompt={pv}")

        print(f"\n  prompt_version breakdown of superseded rows:")
        for pv, n in conn.execute("""
            SELECT COALESCE(prompt_version, '(null)'), COUNT(*)
            FROM product_analysis
            WHERE pack_analysis_attempted = 1
              AND barcode NOT IN (SELECT barcode FROM release_scope)
            GROUP BY 1 ORDER BY 2 DESC
        """).fetchall():
            print(f"    {pv:<16} {n:>7,}")

    if args.dry_run:
        print(f"\n  DRY RUN: would clear {stale:,} rows. "
              f"Run without --dry-run to apply.\n")
        conn.close()
        return

    set_clause = ",\n            ".join(RESET_FIELDS)
    conn.execute(f"""
        UPDATE product_analysis
        SET {set_clause}
        WHERE pack_analysis_attempted = 1
          AND barcode NOT IN (SELECT barcode FROM release_scope)
    """)
    conn.commit()

    (remaining,) = conn.execute("""
        SELECT COUNT(*) FROM product_analysis
        WHERE pack_analysis_attempted = 1
    """).fetchone()
    conn.close()

    print(f"\n  Cleared {stale:,} superseded rows.")
    print(f"  Products with a vision observation now: {remaining:,}")
    print(f"\n  Next:")
    print(f"    python pipeline/merge_scores.py --input <us_normalised.csv> "
          f"--release-id release_2026_01_us_uk")
    print(f"    python pipeline/merge_scores.py --input <uk_normalised.csv> "
          f"--release-id release_2026_01_us_uk")
    print(f"    python pipeline/tag_claims.py\n")


if __name__ == "__main__":
    main()
