"""
reset_release_sample.py
-----------------------
Clears all vision-pipeline and claim-tagging fields for a locked
regional sample before the clean production run. Only touches the
barcodes in the input file — the other ~506,000 rows are not affected.

Fields cleared
  Vision extraction:
    pack_analysis_attempted, ocr_text, ocr_status, llm_status,
    vision_model, prompt_version, pack_analysis_timestamp,
    image_context, claim_extraction_status, detected_claim_phrases,
    claims_json, pack_claims_found
  Optional (cleared only if the column exists in product_analysis):
    ocr_quality, no_claims_detected
  Claim tagging:
    claim_source, claim_category_1, claim_category_2,
    claim_benchmark_intersections

Fields NOT cleared (preserved in every case):
  Ingredient-stage signals (processing_markers_*, e_number_*,
    ingredient_based_claim_*, absence_reduction_*, intersection flags,
    composition_marker_*)
  Nutrition values and nutrition_benchmark_flags
  Formulation families and sampling metadata
  analyzed_at (shared with earlier pipeline stages)
  positioning_composition_gap / _band (legacy; cleared per-row by
    merge_scores.py Path 2a when a non-front reclassification occurs)

Release-run order (per region):
  1. python pipeline/reset_release_sample.py --input <regional_sample.csv>
  2. Remove or rename any existing vision_results_checkpoint.csv
  3. python pipeline/vision_extract.py            (full run, no --test)
  4. Review run-level QA output
  5. python pipeline/merge_scores.py --input data/sample/vision_results_<ts>.csv
  After both US and UK are merged:
  6. python pipeline/tag_claims.py

Usage:
    python pipeline/reset_release_sample.py --input data/sample/us_release_sample.csv
    python pipeline/reset_release_sample.py --input data/sample/us_release_sample.csv --dry-run
"""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH   = REPO_ROOT / "database" / "positioning_radar.db"

# ── Fields to clear ───────────────────────────────────────────────────────────
# Core fields — always cleared (must already exist after migrate_db.py).
CORE_RESET_FIELDS = [
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
    "claim_source            = NULL",
    "claim_category_1        = NULL",
    "claim_category_2        = NULL",
    "claim_benchmark_intersections = NULL",
]

# Optional fields — cleared only if the column exists in product_analysis.
OPTIONAL_RESET_FIELDS = [
    "ocr_quality",
    "no_claims_detected",
]


def get_existing_columns(conn: sqlite3.Connection) -> set:
    rows = conn.execute("PRAGMA table_info(product_analysis)").fetchall()
    return {row[1] for row in rows}


def reset_release_sample(
    conn: sqlite3.Connection,
    barcodes,
    dry_run: bool = False,
) -> int:
    """
    Reset vision and claim fields for the given barcodes.
    Returns the number of rows affected.
    """
    selected = (
        pd.Series(barcodes, dtype="string")
        .dropna()
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    # ── Temp table ────────────────────────────────────────────────────────────
    conn.execute("DROP TABLE IF EXISTS temp.release_barcodes")
    conn.execute("""
        CREATE TEMP TABLE release_barcodes (
            barcode TEXT PRIMARY KEY
        )
    """)
    conn.executemany(
        "INSERT OR IGNORE INTO release_barcodes (barcode) VALUES (?)",
        ((b,) for b in selected),
    )

    # How many rows are actually present in the DB?
    (matched,) = conn.execute("""
        SELECT COUNT(*)
        FROM product_analysis
        WHERE barcode IN (SELECT barcode FROM release_barcodes)
    """).fetchone()

    if dry_run:
        return matched

    # ── Build SET clause ──────────────────────────────────────────────────────
    existing_cols = get_existing_columns(conn)
    set_parts = list(CORE_RESET_FIELDS)
    for col in OPTIONAL_RESET_FIELDS:
        if col in existing_cols:
            set_parts.append(f"{col} = NULL")
        else:
            print(f"  [skip] {col} — column not in product_analysis")

    set_clause = ",\n            ".join(set_parts)

    conn.execute(f"""
        UPDATE product_analysis
        SET
            {set_clause}
        WHERE barcode IN (
            SELECT barcode FROM release_barcodes
        )
    """)
    conn.commit()
    return matched


def main():
    parser = argparse.ArgumentParser(
        description="Reset vision and claim fields for a locked regional sample."
    )
    parser.add_argument(
        "--input", required=True,
        help="CSV file containing the locked regional sample (must have a 'barcode' column)."
    )
    parser.add_argument(
        "--db", default=str(DB_PATH),
        help=f"Path to the SQLite database (default: {DB_PATH})"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be reset without making any changes."
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"\nFood & Beverage Positioning Radar - reset_release_sample.py")
    print(f"{'DRY RUN — no changes will be written' if args.dry_run else 'LIVE RUN'}")
    print(f"\n  Input sample: {input_path.name}")

    # ── Load barcodes ─────────────────────────────────────────────────────────
    # Read only the barcode column — the regional sample files carry many
    # sampling metadata columns that cause memory errors if loaded in full.
    try:
        sample = pd.read_csv(input_path, usecols=["barcode"], dtype={"barcode": str})
    except ValueError:
        raise ValueError(f"'barcode' column not found in {input_path.name}.")
    n_barcodes = sample["barcode"].nunique()
    print(f"  Barcodes in sample: {n_barcodes:,}")

    # ── Connect and reset ─────────────────────────────────────────────────────
    conn = sqlite3.connect(args.db)

    matched = reset_release_sample(conn, sample["barcode"], dry_run=args.dry_run)
    conn.close()

    if args.dry_run:
        print(f"\n  DRY RUN: would reset {matched:,} rows in product_analysis.")
        print(f"  Run without --dry-run to apply.")
    else:
        print(f"\n  Reset complete: {matched:,} rows cleared in product_analysis.")
        print(f"\n  Next steps:")
        print(f"    1. Remove or rename any existing vision_results_checkpoint.csv")
        print(f"       in data/sample/ before starting the vision run.")
        print(f"    2. python pipeline/vision_extract.py")
        print(f"    3. Review QA output, then:")
        print(f"       python pipeline/merge_scores.py --input data/sample/vision_results_<ts>.csv")
        print(f"    4. After all regions are merged: python pipeline/tag_claims.py")

    print()


if __name__ == "__main__":
    main()
