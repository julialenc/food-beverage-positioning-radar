"""
validate_tags.py
-----------------
Quick QA sampler for manual review of claim taxonomy and benchmark
flags. Prints a random sample of products per claim_category_1, with
their underlying claim evidence, tags, benchmark flags, and image URL
— so a human can spot-check whether tag_claims.py's output looks
reasonable on real data.

This is a manual review tool, not a pipeline step — it does not write
anything to the database and produces no file output, only console
output for visual inspection. Run it after tag_claims.py whenever the
taxonomy mapping changes, or periodically as a sanity check.

By default this samples across BOTH evidence layers (claim_source
'vision' and 'ingredient_text_only') — use --source to restrict to one.
This matters in practice: during development, before any pack-image
analysis has run, every product's claim_source is 'ingredient_text_only',
so the default --source all is what makes this script useful at that
stage rather than printing nothing.

Usage:
    python pipeline/validate_tags.py
    python pipeline/validate_tags.py --n 10
    python pipeline/validate_tags.py --source vision
    python pipeline/validate_tags.py --source ingredient_text_only

Input:
    database/positioning_radar.db (products + product_analysis, after
    tag_claims.py has run)
"""

import sqlite3
import pandas as pd
import argparse
from pathlib import Path

ROOT    = Path(__file__).parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"

CATEGORIES = ["FUNCTIONAL", "FREE_OF", "NATURAL_ORGANIC", "OTHER"]


def get_evidence_string(row):
    """
    Reconstruct the claim evidence that actually fed this product's
    taxonomy assignment — pack_claims_found if claim_source is
    'vision', otherwise the same combined ingredient-evidence fallback
    used in tag_claims.py's get_ingredient_fallback_claims().
    """
    if row["claim_source"] == "vision":
        return row["pack_claims_found"]
    return "|".join(filter(None, [
        str(row["ingredient_based_claim_signals_found"] or ""),
        str(row["absence_reduction_claims_found"] or "")
    ]))


def main():
    parser = argparse.ArgumentParser(description="Manual QA sampler for claim taxonomy")
    parser.add_argument("--n", type=int, default=5,
                        help="Number of products to sample per category (default: 5)")
    parser.add_argument("--source", choices=["vision", "ingredient_text_only", "all"],
                        default="all",
                        help="Restrict sample to a specific claim_source (default: all)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT p.product_name, p.brands, p.image_url,
               a.claim_source, a.pack_claims_found,
               a.ingredient_based_claim_signals_found,
               a.absence_reduction_claims_found,
               a.claim_category_1, a.claim_category_2,
               a.nutrition_benchmark_flags, a.claim_benchmark_intersections
        FROM products p JOIN product_analysis a ON p.barcode = a.barcode
        WHERE a.claim_category_1 IS NOT NULL
          AND a.claim_category_1 != 'NO_CLAIM'
    """, conn, dtype={"product_name": str, "brands": str})
    conn.close()

    if args.source != "all":
        df = df[df["claim_source"] == args.source]

    print(f"\nvalidate_tags.py — sampling up to {args.n} products per category "
          f"(source filter: {args.source})")

    if df.empty:
        print("\nNo products match this filter.")
        if args.source == "vision":
            print("This likely means no pack-image analysis has been run yet "
                  "— see pipeline/vision_extract.py and merge_scores.py.")
        return

    for cat in CATEGORIES:
        cat_df = df[df["claim_category_1"] == cat]
        if cat_df.empty:
            print(f"\n=== {cat} (0 products) ===")
            continue
        sample = cat_df.sample(min(args.n, len(cat_df)), random_state=42)
        print(f"\n=== {cat} ({len(cat_df)} total, showing {len(sample)}) ===")
        for _, row in sample.iterrows():
            evidence = get_evidence_string(row)
            print(f"  {str(row['brands'])[:30]:<30} | {str(row['product_name'])[:40]:<40}")
            print(f"  claim_source: {row['claim_source']}")
            print(f"  evidence: {evidence}")
            print(f"  tag1: {row['claim_category_1']} | tag2: {row['claim_category_2']}")
            print(f"  benchmark_flags: {row['nutrition_benchmark_flags']}")
            print(f"  benchmark_intersections: {row['claim_benchmark_intersections']}")
            print(f"  image: {row['image_url']}")
            print()


if __name__ == "__main__":
    main()
