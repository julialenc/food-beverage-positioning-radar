"""
release_summary.py
------------------
Release-scoped claim prevalence. Every figure is restricted to rows
carrying a release_run_id — never to claim_source='vision', which also
matches superseded observations, and never to the whole products table,
which mixes front-of-pack evidence with ingredient-text inference.

Two modes:

  Default — release claim prevalence by country and category, plus a
  measurement-basis breakdown showing which countries have front-of-pack
  evidence and which only have ingredient-text inference.

  --brand NAME — inspect one brand: every release product, what was
  classified, what was extracted, and the OCR text behind it. Use this to
  diagnose misses.

Usage:
    python pipeline/release_summary.py
    python pipeline/release_summary.py --release-id release_2026_01_us_uk
    python pipeline/release_summary.py --brand kind --misses-only
    python pipeline/release_summary.py --brand kind --misses-only --full-ocr
"""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH   = REPO_ROOT / "database" / "positioning_radar.db"


def load_release(conn, release_id):
    return pd.read_sql_query("""
        SELECT
            p.barcode, p.product_name, p.brands, p.primary_brand,
            p.query_category, p.primary_country,
            a.release_run_id, a.claim_source,
            a.sampling_region, a.sampling_category, a.sample_component,
            a.claim_category_1, a.claim_category_2,
            a.pack_claims_found, a.image_context,
            a.claim_extraction_status, a.detected_claim_phrases,
            a.ocr_text
        FROM product_analysis a
        INNER JOIN products p ON p.barcode = a.barcode
        WHERE a.release_run_id = ?
    """, conn, params=(release_id,), dtype={"barcode": str})


def summarise(df):
    completed = df["claim_extraction_status"] == "completed"
    sub = df[completed].copy()
    sub["has_claim"] = (sub["pack_claims_found"].notna()
                        & (sub["pack_claims_found"].astype(str).str.strip() != ""))

    print(f"\n  -- Release claim prevalence ---------------------------------")
    print(f"  Assessed front-of-pack observations: {len(sub):,}")
    n = int(sub["has_claim"].sum())
    print(f"  Carrying at least one taxonomy claim: {n:,} "
          f"({100*n/max(len(sub),1):.1f}%)")

    dims = [("sampling_region", "region")]
    # sampling_category and query_category carry the same values; show one.
    if "sampling_category" in sub.columns and not sub["sampling_category"].isna().all():
        dims.append(("sampling_category", "category"))
    else:
        dims.append(("query_category", "category"))

    for dim, label in dims:
        if dim not in sub.columns or sub[dim].isna().all():
            continue
        g = sub.groupby(dim)["has_claim"].agg(["sum", "count"])
        g["pct"] = 100 * g["sum"] / g["count"]
        print(f"\n  By {label}:")
        for idx, row in g.sort_values("pct", ascending=False).iterrows():
            print(f"    {str(idx)[:26]:<28} {int(row['sum']):>5,}/{int(row['count']):>5,}"
                  f"   {row['pct']:>5.1f}%")

    if "sampling_region" in sub.columns and sub["sampling_region"].isna().all():
        print(f"\n  NOTE: sampling_region is empty — re-run merge_scores.py after")
        print(f"  migrate_db.py to persist the sampling frame. Country-level")
        print(f"  breakdowns are not a valid substitute.")

    print(f"\n  Cut 1 distribution:")
    for val, k in sub["claim_category_1"].value_counts(dropna=False).items():
        print(f"    {str(val):<20} {k:>6,}  ({100*k/max(len(sub),1):.1f}%)")


def measurement_basis(conn, release_id):
    """
    Show how primary_country scatters across the release.

    primary_country reflects where a product was tagged in Open Food Facts,
    not the market it was sampled for. A product sampled under US_CANADA can
    carry primary_country = France. Breaking the release down by country
    therefore produces unweighted fragments with no sampling validity — this
    output exists to make that visible, not to be used as a regional view.
    """
    df = pd.read_sql_query("""
        SELECT p.primary_country,
               COUNT(*) AS products,
               SUM(CASE WHEN a.release_run_id = ? THEN 1 ELSE 0 END) AS in_release,
               SUM(CASE WHEN a.claim_source = 'vision' THEN 1 ELSE 0 END) AS vision_tagged
        FROM products p
        LEFT JOIN product_analysis a ON a.barcode = p.barcode
        GROUP BY p.primary_country
        HAVING products > 500
        ORDER BY products DESC
    """, conn, params=(release_id,))

    print(f"\n  -- primary_country spread (NOT the sampling frame) -----------")
    print(f"  {'country':<26} {'products':>10} {'in release':>12} {'basis'}")
    warned = []
    for _, r in df.iterrows():
        basis = ("front-of-pack" if r["in_release"] > 0
                 else "INGREDIENT TEXT ONLY")
        if r["in_release"] == 0:
            warned.append(str(r["primary_country"]))
        print(f"  {str(r['primary_country'])[:24]:<26} {int(r['products']):>10,}"
              f" {int(r['in_release']):>12,}  {basis}")

    print(f"\n  These countries are Open Food Facts tags. We did not sample any")
    print(f"  of them — the products above are simply whatever turned up in the")
    print(f"  US/Canada and UK/Ireland draw. A rate calculated for one of them")
    print(f"  describes only those products, not that country's market.")
    print(f"  Report regions using sampling_region, and show only rows where")
    print(f"  release_run_id matches the current release.")


def inspect_brand(df, brand, misses_only, full_ocr):
    # Word-boundary match — a plain substring for "kind" also catches
    # "Kinder" and "KINDLING", which are unrelated brands.
    pattern = rf"\b{brand.lower()}\b"
    mask = (df["brands"].fillna("").str.lower().str.contains(pattern, regex=True)
            | df["primary_brand"].fillna("").str.lower().str.contains(pattern, regex=True))
    sub = df[mask].copy()
    if sub.empty:
        print(f"\n  No release products found for brand '{brand}'.")
        return

    sub["has_claim"] = (sub["pack_claims_found"].notna()
                        & (sub["pack_claims_found"].astype(str).str.strip() != ""))
    completed = sub["claim_extraction_status"] == "completed"

    print(f"\n  -- Brand: {brand} --------------------------------------------")
    print(f"  In release:            {len(sub):,}")
    print(f"  Assessed front packs:  {int(completed.sum()):,}")
    print(f"  With a claim:          {int((completed & sub['has_claim']).sum()):,}")
    print(f"  Assessed, no claim:    {int((completed & ~sub['has_claim']).sum()):,}")
    print(f"  Not assessed:          {int((~completed).sum()):,}")

    show = sub[completed & ~sub["has_claim"]] if misses_only else sub
    if misses_only:
        print(f"\n  Assessed front packs with NO claim detected "
              f"({len(show):,}):")

    for _, r in show.iterrows():
        ocr = str(r["ocr_text"] or "")
        if not full_ocr and len(ocr) > 300:
            ocr = ocr[:300] + " ..."
        print(f"\n  {'-' * 68}")
        print(f"  barcode      {r['barcode']}")
        print(f"  product      {str(r['product_name'])[:60]}")
        print(f"  context      {r['image_context']}  /  {r['claim_extraction_status']}")
        print(f"  claims       {r['pack_claims_found'] if str(r['pack_claims_found']).strip() else '(none)'}")
        print(f"  phrases      {str(r['detected_claim_phrases'])[:120]}")
        print(f"  ocr_words    {len(ocr.split())}")
        print(f"  ocr_text     {ocr}")


def main():
    ap = argparse.ArgumentParser(description="Release-scoped claim summary.")
    ap.add_argument("--release-id", default="release_2026_01_us_uk")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--brand", default=None,
                    help="Inspect one brand instead of printing the summary")
    ap.add_argument("--misses-only", action="store_true",
                    help="With --brand, show only assessed packs where no claim was found")
    ap.add_argument("--full-ocr", action="store_true",
                    help="With --brand, print the full OCR text rather than truncating")
    args = ap.parse_args()

    print(f"\nFood & Beverage Positioning Radar - release_summary.py")
    print(f"Release: {args.release_id}")

    conn = sqlite3.connect(args.db)
    df = load_release(conn, args.release_id)

    if df.empty:
        print(f"\n  No rows found for release_run_id = {args.release_id}.")
        print(f"  Check the ID, or re-run merge_scores.py with --release-id.\n")
        conn.close()
        return

    print(f"  Release rows: {len(df):,}")

    if args.brand:
        inspect_brand(df, args.brand, args.misses_only, args.full_ocr)
    else:
        summarise(df)
        measurement_basis(conn, args.release_id)

    conn.close()
    print()


if __name__ == "__main__":
    main()
