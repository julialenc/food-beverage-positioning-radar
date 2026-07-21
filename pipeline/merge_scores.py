"""
merge_scores.py
----------------
Joins vision claim extraction output with product data and writes
pack-image results to the database.

The legacy gap metric has been retired. This script no longer
computes Component A/B/C scoring. Its sole responsibilities are:

  1. Build pack_claims_found from v4_* extraction columns for every
     valid front-of-pack observation (claim_extraction_status="completed").
  2. Write all attempt metadata and classification fields to
     product_analysis for every product submitted, regardless of outcome.
  3. Clear any stale pilot pack_claims_found and gap score when a product
     is reclassified as non-front in the new run.
  4. Carry sampling metadata through to the merged CSV for downstream
     weighting and modelling.

claim_source, claim_category_1, claim_category_2,
nutrition_benchmark_flags, and claim_benchmark_intersections are NOT
written here — they are populated by tag_claims.py.

Usage:
    python pipeline/merge_scores.py
    python pipeline/merge_scores.py --input data/sample/vision_results_<ts>.csv
"""

import argparse
import pandas as pd
import sqlite3
import os
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).parent.parent
SAMPLE_DIR = ROOT / "data" / "sample"
REF_DIR    = ROOT / "data" / "reference"
DB_PATH    = ROOT / "database" / "positioning_radar.db"


# ── Pack claim fields ─────────────────────────────────────────────────────────
# The full set of boolean claim fields produced by vision_extract.py's
# extraction schema, used to build pack_claims_found. This list
# explicitly EXCLUDES non-claim extraction metadata and non-boolean
# fields — no_claims_detected (an absence indicator, not a claim),
# ocr_quality, protein_amount_g, sugar_reduction_pct,
# comparative_reference, and the list fields fortification_nutrients /
# sustainability_certs / other_claims (handled separately, not booleans).
# These must never appear inside pack_claims_found itself.

PACK_CLAIM_FIELDS = [
    "protein_claim", "sugar_free_claim", "reduced_sugar",
    "no_palm_oil", "no_artificial", "natural_claim",
    "fortification_claim", "fibre_claim", "probiotic_claim",
    "immune_claim", "energy_claim", "vitalite_concept",
    "sustainability_halo", "reformulation_claim", "comparative_claim",
    "glp1_positioning", "origin_quality_claim", "clean_label_claim",
    "minimal_ingredients_claim", "artisan_claim", "vegan_claim",
    "organic_claim", "dairy_free_claim", "lactose_free_claim",
    "plant_based_claim", "heritage_claim", "gluten_free_claim",
    "gender_targeting_claim",
    # v4 additions — must be here or claims are silently lost from pack_claims_found
    "gut_health_claim", "prebiotic_claim", "sleep_claim", "brain_health_claim",
    "reduced_fat_claim", "whole_grain_claim",
]

def safe_text(val):
    """
    Convert a value to a clean string for SQLite storage, or None.

    Needed because the common `str(val or "")` pattern produces the
    literal string "nan" when val is a pandas/numpy NaN float — NaN is
    truthy in Python, so `nan or ""` evaluates to nan, not "".
    """
    if pd.isna(val):
        return None
    return str(val)


def find_latest_vision_results():
    """
    Find the most recent vision results CSV across reference and sample
    folders, excluding vision_results_checkpoint.csv — an in-progress
    checkpoint file should never be auto-selected as the final result
    set, even if it happens to have the latest modification time. Use
    --input to target a checkpoint file explicitly if ever needed.
    """
    files = list(REF_DIR.glob("vision_results_*.csv")) + \
            list(SAMPLE_DIR.glob("vision_results_*.csv"))
    files = [f for f in files if "checkpoint" not in f.name]
    if not files:
        raise FileNotFoundError(
            "No vision_results_*.csv found (excluding checkpoint files). "
            "Run vision_extract.py first."
        )
    return max(files, key=lambda f: f.stat().st_mtime)


NON_FRONT_STATUSES = {"not_applicable_non_front", "unreadable"}


def get_pack_claims_found(row):
    """
    Build the pipe-separated pack_claims_found string from PACK_CLAIM_FIELDS.

    NON-FRONT GUARD (v3+): if claim_extraction_status is not "completed",
    the image was an ingredient sticker, nutrition label or price sticker.
    In that case the LLM set all claim fields to false not because the product
    has no claims, but because it was the wrong panel. Return None (not "")
    so this row is excluded from claim_source="vision" entirely and cannot
    create a false negative in prevalence calculations or logistic regression.
    """
    extraction_status = str(row.get("v3_claim_extraction_status", "completed") or "completed")
    if extraction_status in NON_FRONT_STATUSES:
        return None  # non-front image: not a valid claim observation

    claims = []
    for key in PACK_CLAIM_FIELDS:
        col = f"v3_{key}"
        if col in row.index and row[col] == True:
            claims.append(key)
    return "|".join(claims) if claims else ""


def load_db_data(conn, barcodes):
    """
    Load product context for only the barcodes in the current vision file.
    Uses a SQLite temp table so SQLite does the filtering.
    """
    selected = (
        pd.Series(barcodes, dtype="string").dropna().astype(str)
        .drop_duplicates().tolist()
    )
    conn.execute("DROP TABLE IF EXISTS temp.selected_barcodes")
    conn.execute("""
        CREATE TEMP TABLE selected_barcodes (barcode TEXT PRIMARY KEY)
    """)
    conn.executemany(
        "INSERT OR IGNORE INTO selected_barcodes (barcode) VALUES (?)",
        ((b,) for b in selected),
    )
    return pd.read_sql_query("""
        SELECT
            p.barcode, p.product_name, p.brands, p.primary_brand,
            p.query_category, p.primary_country,
            p.nova_group, p.nutriscore_grade,
            p.energy_kcal, p.sugars_100g, p.protein_100g,
            p.saturated_fat_100g, p.image_url
        FROM selected_barcodes s
        INNER JOIN products p ON p.barcode = s.barcode
    """, conn, dtype={"barcode": str})


def update_db_positioning_scores(conn, merged_df, timestamp):
    """
    Write pack-image extraction results back to the product_analysis table.

    Path 1 — attempt metadata: written for every row attempted this run,
    regardless of OCR/LLM outcome. Includes image_context,
    claim_extraction_status, detected_claim_phrases, claims_json — always
    stored, not just for scored front-of-pack images. A legal panel or
    price sticker is a valid classification result that must be persisted.

    Path 2 — result fields: two sub-paths depending on extraction outcome.
        2a. Successful non-front classification: clears any stale pilot
            pack_claims_found and score so old pilot claims cannot persist
            as though they were the clean-run result.
        2b. Valid front-of-pack with a score: writes the new composite score
            and pack_claims_found.
    Rows attempted but failed (Path 1 only) preserve any prior result.

    claim_source, claim_category_1, claim_category_2,
    nutrition_benchmark_flags, and claim_benchmark_intersections are NOT
    written here — see module docstring.
    """
    cursor = conn.cursor()
    updated = 0

    attempted = merged_df[merged_df["llm_status"].notna()]

    for _, row in attempted.iterrows():
        # Path 1: attempt metadata + classification fields, always written.
        cursor.execute("""
            UPDATE product_analysis
            SET pack_analysis_attempted   = 1,
                vision_model              = ?,
                prompt_version            = ?,
                pack_analysis_timestamp   = ?,
                ocr_text                  = ?,
                ocr_status                = ?,
                llm_status                = ?,
                image_context             = ?,
                claim_extraction_status   = ?,
                detected_claim_phrases    = ?,
                claims_json               = ?,
                analyzed_at               = ?
            WHERE barcode = ?
        """, (
            safe_text(row.get("vision_model")),
            safe_text(row.get("prompt_version")),
            safe_text(row.get("pack_analysis_timestamp")),
            safe_text(row.get("ocr_text")),
            safe_text(row.get("ocr_status")),
            safe_text(row.get("llm_status")),
            safe_text(row.get("v3_image_context")),
            safe_text(row.get("v3_claim_extraction_status")),
            safe_text(row.get("v3_detected_claim_phrases")),
            safe_text(row.get("claims_json")),
            timestamp,
            str(row["barcode"])
        ))

        llm_ok = row.get("llm_status") == "success"
        extraction_status = str(row.get("v3_claim_extraction_status") or "")

        # Path 2a: successful non-front classification — clear stale pilot claims.
        if llm_ok and extraction_status in NON_FRONT_STATUSES:
            cursor.execute("""
                UPDATE product_analysis
                SET positioning_composition_gap      = NULL,
                    positioning_composition_gap_band = NULL,
                    pack_claims_found                = NULL
                WHERE barcode = ?
            """, (str(row["barcode"]),))

        # Path 2b: valid front-of-pack — write pack_claims_found.
        elif extraction_status == "completed":
            pcf = row.get("pack_claims_found")
            cursor.execute("""
                UPDATE product_analysis
                SET pack_claims_found = ?
                WHERE barcode = ?
            """, (
                safe_text(pcf) if pcf is not None else None,
                str(row["barcode"])
            ))

        updated += 1

    conn.commit()
    return updated


def main():
    parser = argparse.ArgumentParser(
        description="Merge ingredient-stage analysis with vision results"
    )
    parser.add_argument(
        "--input", type=str, default=None,
        help="Path to a specific vision_results CSV (default: auto-detect "
             "latest, excluding checkpoint files)"
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\nFood & Beverage Positioning Radar - merge_scores.py")
    print(f"Run timestamp: {timestamp}")
    print(f"Merging vision results and writing pack_claims_found to database\n")

    # ── Load vision results ───────────────────────────────────────────────────
    vision_path = Path(args.input) if args.input else find_latest_vision_results()
    print(f"  Vision results: {vision_path.name}")
    vision = pd.read_csv(vision_path, dtype={"barcode": str}, low_memory=False)
    print(f"  Vision rows: {len(vision):,}")

    ocr_ok  = (vision["ocr_status"] == "success").sum()
    llm_ok  = (vision["llm_status"] == "success").sum()
    print(f"  OCR success: {ocr_ok:,} | LLM success: {llm_ok:,}")

    # ── Load DB data ──────────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    n_barcodes = vision["barcode"].nunique()
    print(f"\n  Loading product data for {n_barcodes:,} barcodes from DB...")
    db_df = load_db_data(conn, vision["barcode"])
    print(f"  DB rows: {len(db_df):,}")

    # ── Merge on barcode ──────────────────────────────────────────────────────
    print(f"\n  Merging on barcode...")

    # Keep v3_ raw claim columns plus any available extraction metadata.
    # Metadata columns (vision_model, prompt_version,
    # pack_analysis_timestamp) are present for any run using the current
    # vision_extract.py; may be absent if reusing an older archived
    # vision_results CSV — handled gracefully via row.get()/safe_text().
    v3_cols = [c for c in vision.columns if c.startswith("v3_")]
    metadata_cols = [c for c in [
        "vision_model", "prompt_version", "pack_analysis_timestamp",
    ] if c in vision.columns]
    # Sampling metadata: carries stratification context through to merged output
    # for later weighting and modelling. Not written to product_analysis DB.
    sampling_cols = [
        c for c in vision.columns
        if c.startswith("sampling_")
        or c.startswith("stratum_")
        or c in {
            "sample_component", "primary_stratum_id",
            "inclusion_probability", "sampling_weight", "weight_status",
            "formulation_family", "pre_llm_positioning_signal",
            "pre_llm_positioning_territories", "formulation_likelihood_signal",
            "formulation_territories", "energy_band", "protein_band",
            "fibre_band", "satfat_band", "sugars_band",
            "metric_basis", "random_seed",
        }
    ]

    result_cols = ["barcode", "ocr_text", "ocr_status", "llm_status", "claims_json"]
    vision_slim = vision[
        [c for c in result_cols if c in vision.columns] +
        metadata_cols + sampling_cols + v3_cols
    ].copy()

    # vision_slim is the left table so the result has only as many rows as
    # the vision CSV (100 for test, ~6K for full run) — not 512K.
    # db_df.merge(vision_slim, how="left") would produce 512K rows and
    # fail with a memory error when pandas materialises the join array.
    merged = vision_slim.merge(db_df, on="barcode", how="left",
                               validate="one_to_one")
    matched = merged["product_name"].notna().sum()
    print(f"  Matched to DB product data: {matched:,} / {len(merged):,}")

    # ── Compute pack_claims_found ────────────────────────────────────────────
    has_vision = merged["llm_status"] == "success"
    v3_status  = merged.get("v3_claim_extraction_status",
                             pd.Series("", index=merged.index)).fillna("")
    valid_claim_observation = has_vision & (v3_status == "completed")

    # pack_claims_found semantics:
    #   None  — not a valid observation (not attempted, failed, or non-front)
    #   ""    — front-of-pack confirmed, no claims found
    #   "x|y" — pipe-separated list of detected claim keys
    # Apply only on the vision-analyzed subset — running apply() on the full
    # 512K-row merged dataframe causes pandas to materialise a (36 × 512K)
    # numpy object array (~141 MB) before iterating, which fails on most
    # machines. The vision subset is at most a few hundred rows.
    merged["pack_claims_found"] = None
    if valid_claim_observation.any():
        merged.loc[valid_claim_observation, "pack_claims_found"] = (
            merged.loc[valid_claim_observation].apply(get_pack_claims_found, axis=1)
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    completed   = valid_claim_observation.sum()
    with_claims = (merged["pack_claims_found"].notna() & (merged["pack_claims_found"] != "")).sum()
    no_claims   = (merged["pack_claims_found"] == "").sum()
    non_front   = (has_vision & v3_status.isin(NON_FRONT_STATUSES)).sum()
    print(f"\n  -- Pack-image extraction summary ----------------------------")
    print(f"  Valid front-of-pack observations: {completed:,}")
    print(f"    With claims:    {with_claims:,}")
    print(f"    No claims:      {no_claims:,}")
    print(f"  Non-front / unreadable:           {non_front:,}")
    print(f"  Failed / not attempted:           {(~has_vision).sum():,}")

        # ── Write results to DB ───────────────────────────────────────────────────
    print(f"\n  Writing pack-image results to database...")
    updated = update_db_positioning_scores(conn, merged, timestamp)
    print(f"  Updated {updated:,} rows in product_analysis")
    conn.close()

    # ── Save merged CSV ───────────────────────────────────────────────────────
    output_path = SAMPLE_DIR / f"merged_results_{timestamp}.csv"
    merged.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n  Saved -> merged_results_{timestamp}.csv")
    print(f"  ({len(merged):,} rows)")

    # Power BI QA export — vision-analyzed products only.
    # Final reporting comes from db_summary.py after tag_claims.py has run.
    pbi_cols = [
        "barcode", "product_name", "brands", "primary_brand",
        "query_category", "primary_country", "nova_group", "nutriscore_grade",
        "energy_kcal", "sugars_100g", "protein_100g", "saturated_fat_100g",
        "image_url", "pack_claims_found",
        # Audit fields — image classification and extraction traceability
        "image_context", "claim_extraction_status",
        "detected_claim_phrases", "prompt_version",
    ] + [c for c in v3_cols if c in merged.columns]

    vision_scored = merged[merged["pack_claims_found"].notna()].copy()
    pbi_cols = [c for c in pbi_cols if c in vision_scored.columns]
    pbi_df = vision_scored[pbi_cols].copy()
    pbi_path = SAMPLE_DIR / f"powerbi_merged_{timestamp}.csv"
    pbi_df.to_csv(pbi_path, index=False, encoding="utf-8-sig")
    print(f"  Power BI export (intermediate QA) -> powerbi_merged_{timestamp}.csv")
    print(f"  ({len(pbi_df):,} rows)\n")
    print(f"  Done. pack_claims_found is now in the database.\n")


if __name__ == "__main__":
    main()
