"""
load.py
-------
Loads analyzed product data into SQLite database.
Also writes a clean CSV for future Power BI connection.

Schema:
    products             — product identity + nutrition (UPSERT on barcode)
    product_analysis      — analysis fields: composition markers, claim
                            signals, positioning metrics, claim taxonomy,
                            benchmark flags, pack-image extraction metadata
                            (UPSERT on barcode)
    weekly_brand_summary — pre-aggregated composition summary for early
                            pipeline review (see note in compute_weekly_
                            brand_summary() on scope)
    ingestion_log        — one row per pipeline run

Design principles:
    - INSERT OR REPLACE on barcode — idempotent, safe to run multiple times
    - last_modified_t drives weekly diff logic in production
    - weekly_brand_summary pre-aggregated so Power BI never touches raw rows
    - ingestion_log records source (api / bulk_export) for auditability
    - product_analysis declares its full schema upfront, including columns
      not yet populated by analyze.py (claim taxonomy, benchmark flags,
      pack-image metadata) — these are written later by merge_scores.py
      and tag_claims.py via UPDATE, not ALTER TABLE. See docs/ADR.md.
    - load.py is an ingredient-stage loader: it only writes columns that
      are present in the current input CSV. It must never write later-
      stage fields (pack_claims_found, claim_category_1, nutrition_
      benchmark_flags, positioning_composition_gap, etc.) as NULL on a
      rerun, since that would silently erase enrichment already written
      by merge_scores.py or tag_claims.py.

Usage:
    python pipeline/load.py
    python pipeline/load.py --source bulk_export

Input:
    data/sample/analyzed_<timestamp>.csv   (latest file auto-detected)

Output:
    database/positioning_radar.db
    data/sample/powerbi_products_<timestamp>.csv
    data/sample/powerbi_analysis_<timestamp>.csv

Production note:
    Week 0: run on full OFF bulk export (~50,000-100,000 filtered products)
    Weekly: run on API diff (last_modified_t > 7 days) — same script,
    different input size, pass --source bulk_export or --source api
    accordingly. See docs/ADR.md and docs/OBSERVATIONS.md OBS-012 for
    full production strategy.

Known limitation:
    CREATE TABLE IF NOT EXISTS does not migrate an existing database with
    an older schema. If a positioning_radar.db from a prior schema version
    exists, drop it before running, or use the schema-verification logic
    in verify_schema.py once that script is updated to match this schema.
"""

import argparse
import pandas as pd
import sqlite3
import os
from datetime import datetime


# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(ROOT, "data", "sample")
DB_DIR     = os.path.join(ROOT, "database")
DB_PATH    = os.path.join(DB_DIR, "positioning_radar.db")


# ── Schema ────────────────────────────────────────────────────────────────────

DDL_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    barcode                      TEXT PRIMARY KEY,
    product_name                 TEXT,
    brands                       TEXT,
    primary_brand                 TEXT,
    quantity                     TEXT,
    packaging                    TEXT,
    query_category                TEXT,
    off_categories                 TEXT,
    countries                    TEXT,
    primary_country                TEXT,
    labels                       TEXT,
    ingredients_text               TEXT,
    additives_tags                 TEXT,
    energy_kcal                  REAL,
    fat_100g                     REAL,
    saturated_fat_100g             REAL,
    carbs_100g                   REAL,
    sugars_100g                  REAL,
    fiber_100g                   REAL,
    protein_100g                  REAL,
    salt_100g                    REAL,
    nutriscore_grade               TEXT,
    nova_group                   REAL,
    completeness_score             INTEGER,
    ingredients_lang               TEXT,
    ingredient_analysis_eligible     INTEGER,   -- 1/0 boolean
    created_t                    TEXT,
    last_modified_t                TEXT,
    ingested_at                   TEXT,      -- when this row was loaded by us
    image_url                    TEXT       -- front-of-pack image URL, used
                                             -- for pack-image claim extraction
);
"""

DDL_PRODUCT_ANALYSIS = """
CREATE TABLE IF NOT EXISTS product_analysis (
    barcode                               TEXT PRIMARY KEY,

    -- Ingredient composition markers (analyze.py, Component A)
    processing_marker_count                 INTEGER,
    processing_markers_found                 TEXT,
    processing_marker_max_severity             INTEGER,
    has_processing_markers                  INTEGER,   -- 1/0 boolean
    e_number_count                        INTEGER,
    e_numbers_found                        TEXT,
    has_artificial_sweetener                 INTEGER,   -- 1/0 boolean
    composition_marker_score                 REAL,
    composition_marker_band                  TEXT,

    -- Ingredient/name-based claim signals (analyze.py)
    ingredient_based_claim_signal_count         INTEGER,
    ingredient_based_claim_signals_found         TEXT,
    absence_reduction_claim_count             INTEGER,
    absence_reduction_claims_found             TEXT,

    -- Named intersection patterns (analyze.py)
    sugar_positioning_intersection_flag          INTEGER,   -- 1/0
    protein_fat_intersection_flag              INTEGER,
    fibre_sugar_processing_intersection_flag       INTEGER,
    plant_based_nutrition_intersection_flag       INTEGER,

    -- Pack-image extraction metadata (populated by merge_scores.py)
    pack_analysis_attempted                 INTEGER,   -- 1/0, whether
                                                        -- this product was
                                                        -- submitted for
                                                        -- image extraction
    ocr_text                              TEXT,
    ocr_status                             TEXT,
    llm_status                             TEXT,
    vision_model                           TEXT,
    prompt_version                         TEXT,
    pack_analysis_timestamp                  TEXT,
    pack_claims_found                       TEXT,
    claim_source                           TEXT,      -- 'vision' or 'nlp_only'

    -- Claim taxonomy (populated by tag_claims.py)
    claim_category_1                        TEXT,
    claim_category_2                        TEXT,

    -- Benchmark flags and intersections (populated by tag_claims.py)
    nutrition_benchmark_flags                 TEXT,
    claim_benchmark_intersections              TEXT,

    -- Positioning-to-composition gap (populated by merge_scores.py)
    positioning_composition_gap               REAL,
    positioning_composition_gap_band            TEXT,

    -- Planned, not yet implemented
    product_segment_label                   TEXT,      -- null until v2 K-Means

    analyzed_at                           TEXT,      -- when this row was
                                                       -- last computed/updated

    FOREIGN KEY (barcode) REFERENCES products(barcode)
);
"""

DDL_WEEKLY_BRAND_SUMMARY = """
CREATE TABLE IF NOT EXISTS weekly_brand_summary (
    id                                  INTEGER PRIMARY KEY AUTOINCREMENT,
    week_ending                          TEXT,      -- ISO date of week end
    primary_brand                        TEXT,
    query_category                        TEXT,
    product_count                        INTEGER,
    avg_composition_marker_score             REAL,
    pct_nova4                           REAL,
    pct_with_ingredient_based_claim_signals     REAL,
    pct_with_artificial_sweetener            REAL,
    top_ingredient_based_claim_signal         TEXT,
    run_timestamp                         TEXT
);
"""

DDL_INGESTION_LOG = """
CREATE TABLE IF NOT EXISTS ingestion_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp     TEXT,
    source            TEXT,    -- 'api' or 'bulk_export'
    input_file        TEXT,
    category          TEXT,    -- 'all' or specific category
    rows_in_file      INTEGER,
    products_inserted INTEGER,
    products_updated  INTEGER,
    analysis_inserted INTEGER,
    analysis_updated  INTEGER,
    status            TEXT,    -- 'success' / 'partial' / 'failed'
    notes             TEXT
);
"""

DDL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brands);",
    "CREATE INDEX IF NOT EXISTS idx_products_primary_brand ON products(primary_brand);",
    "CREATE INDEX IF NOT EXISTS idx_products_category ON products(query_category);",
    "CREATE INDEX IF NOT EXISTS idx_products_country ON products(primary_country);",
    "CREATE INDEX IF NOT EXISTS idx_products_nova ON products(nova_group);",
    "CREATE INDEX IF NOT EXISTS idx_products_modified ON products(last_modified_t);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_score ON product_analysis(composition_marker_score);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_band ON product_analysis(composition_marker_band);",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_latest_analyzed(sample_dir):
    """Auto-detect the most recently created analyzed_*.csv file."""
    files = [
        f for f in os.listdir(sample_dir)
        if f.startswith("analyzed_") and f.endswith(".csv")
    ]
    if not files:
        raise FileNotFoundError(
            f"No analyzed_*.csv found in {sample_dir}. "
            "Run analyze.py first."
        )
    files.sort(reverse=True)
    return os.path.join(sample_dir, files[0])


def init_db(conn):
    """
    Create tables and indexes if they don't exist.

    Note: this does NOT migrate an existing database created under an
    older schema (CREATE TABLE IF NOT EXISTS is a no-op if the table
    already exists, even with different columns). See module docstring.
    """
    cursor = conn.cursor()
    cursor.execute(DDL_PRODUCTS)
    cursor.execute(DDL_PRODUCT_ANALYSIS)
    cursor.execute(DDL_WEEKLY_BRAND_SUMMARY)
    cursor.execute(DDL_INGESTION_LOG)
    for idx_sql in DDL_INDEXES:
        cursor.execute(idx_sql)
    conn.commit()
    print(f"  Database initialised: {DB_PATH}")


def safe_val(val):
    """
    Convert pandas NA/NaN/None to Python None for SQLite insertion.
    Converts booleans to 1/0 for SQLite INTEGER storage.
    """
    if pd.isna(val) if not isinstance(val, (list, dict)) else False:
        return None
    if isinstance(val, bool):
        return 1 if val else 0
    if hasattr(val, 'item'):
        val = val.item()
    # Convert large integers to string to avoid SQLite overflow
    if isinstance(val, int) and (val > 2**63 - 1 or val < -(2**63)):
        return str(val)
    return val


# ── Products table ────────────────────────────────────────────────────────────

PRODUCT_COLS = [
    "barcode", "product_name", "brands", "primary_brand", "quantity", "packaging",
    "query_category", "off_categories", "countries", "primary_country",
    "labels", "ingredients_text", "additives_tags",
    "energy_kcal", "fat_100g", "saturated_fat_100g", "carbs_100g",
    "sugars_100g", "fiber_100g", "protein_100g", "salt_100g",
    "nutriscore_grade", "nova_group", "completeness_score",
    "ingredients_lang", "ingredient_analysis_eligible", "created_t",
    "last_modified_t", "image_url",
]

def load_products(df, conn, timestamp):
    """
    UPSERT products into the products table.
    Returns (inserted, updated) counts.
    """
    cursor   = conn.cursor()
    inserted = 0
    updated  = 0

    for _, row in df.iterrows():
        # Check if barcode exists
        cursor.execute(
            "SELECT barcode FROM products WHERE barcode = ?",
            (str(row["barcode"]),)
        )
        exists = cursor.fetchone() is not None

        values = [safe_val(row.get(col)) for col in PRODUCT_COLS]
        values.append(timestamp)   # ingested_at

        if exists:
            # UPDATE existing row
            set_clause = ", ".join(
                f"{col} = ?" for col in PRODUCT_COLS
            ) + ", ingested_at = ?"
            cursor.execute(
                f"UPDATE products SET {set_clause} WHERE barcode = ?",
                values + [str(row["barcode"])]
            )
            updated += 1
        else:
            # INSERT new row
            cols_str = ", ".join(PRODUCT_COLS) + ", ingested_at"
            placeholders = ", ".join("?" * (len(PRODUCT_COLS) + 1))
            cursor.execute(
                f"INSERT INTO products ({cols_str}) VALUES ({placeholders})",
                values
            )
            inserted += 1

    conn.commit()
    return inserted, updated


# ── Product analysis table ────────────────────────────────────────────────────
# ANALYSIS_COLS is the full declared schema, including columns not yet
# produced by analyze.py (claim taxonomy, benchmark flags, pack-image
# metadata). load_product_analysis() only writes the subset of these
# columns actually present in the input CSV — see its docstring for why
# this matters on rerun.

ANALYSIS_COLS = [
    "barcode",
    "processing_marker_count", "processing_markers_found",
    "processing_marker_max_severity", "has_processing_markers",
    "e_number_count", "e_numbers_found", "has_artificial_sweetener",
    "composition_marker_score", "composition_marker_band",
    "ingredient_based_claim_signal_count",
    "ingredient_based_claim_signals_found",
    "absence_reduction_claim_count", "absence_reduction_claims_found",
    "sugar_positioning_intersection_flag", "protein_fat_intersection_flag",
    "fibre_sugar_processing_intersection_flag",
    "plant_based_nutrition_intersection_flag",
    "pack_analysis_attempted", "ocr_text", "ocr_status", "llm_status",
    "vision_model", "prompt_version", "pack_analysis_timestamp",
    "pack_claims_found", "claim_source",
    "claim_category_1", "claim_category_2",
    "nutrition_benchmark_flags", "claim_benchmark_intersections",
    "positioning_composition_gap", "positioning_composition_gap_band",
    "product_segment_label",
]

def load_product_analysis(df, conn, timestamp):
    """
    UPSERT analysis results into the product_analysis table.

    Only writes columns that are actually present in the input dataframe.
    This matters: product_analysis declares its full schema upfront (see
    DDL_PRODUCT_ANALYSIS), including fields populated later by
    merge_scores.py and tag_claims.py. If load.py is rerun after those
    steps — for example during a weekly API diff — naively writing every
    declared column would set later-stage fields (pack_claims_found,
    claim_category_1, positioning_composition_gap, etc.) to NULL,
    silently erasing prior enrichment. Restricting writes to columns
    present in the current CSV avoids this. See module docstring.

    Returns (inserted, updated) counts.
    """
    cursor   = conn.cursor()
    inserted = 0
    updated  = 0

    analysis_cols_to_load = [c for c in ANALYSIS_COLS if c in df.columns]

    for _, row in df.iterrows():
        cursor.execute(
            "SELECT barcode FROM product_analysis WHERE barcode = ?",
            (str(row["barcode"]),)
        )
        exists = cursor.fetchone() is not None

        values = [safe_val(row.get(col)) for col in analysis_cols_to_load]
        values.append(timestamp)   # analyzed_at

        if exists:
            set_clause = ", ".join(
                f"{col} = ?" for col in analysis_cols_to_load
            ) + ", analyzed_at = ?"
            cursor.execute(
                f"UPDATE product_analysis SET {set_clause} WHERE barcode = ?",
                values + [str(row["barcode"])]
            )
            updated += 1
        else:
            cols_str = ", ".join(analysis_cols_to_load) + ", analyzed_at"
            placeholders = ", ".join("?" * (len(analysis_cols_to_load) + 1))
            cursor.execute(
                f"INSERT INTO product_analysis ({cols_str}) VALUES ({placeholders})",
                values
            )
            inserted += 1

    conn.commit()
    return inserted, updated


# ── Weekly brand summary ──────────────────────────────────────────────────────

def compute_weekly_brand_summary(df, conn, timestamp):
    """
    Compute brand-level aggregations and insert into weekly_brand_summary.
    This pre-aggregation means Power BI never touches raw product rows
    for trend charts. Grouped by primary_brand (normalized), not the raw
    brands field, for consistency with every other aggregation in the
    pipeline.

    Scope note: this runs at load.py time, before merge_scores.py and
    tag_claims.py have populated pack claims, claim taxonomy, benchmark
    flags, or positioning_composition_gap — so this summary necessarily
    reflects ingredient-analysis-stage signals only. A full
    market-intelligence summary (pack claim distribution, claim taxonomy
    shares, benchmark intersection rates, average positioning gap) needs
    a separate aggregation step that runs after the full pipeline
    completes and queries product_analysis directly. See docs/ADR.md.

    Deletes existing rows for today's week_ending before inserting, so
    re-running this script on the same day does not create duplicate
    trend rows.
    """
    cursor = conn.cursor()

    # Only use ingredient-analysis-eligible rows with scores
    eligible = df[df["ingredient_analysis_eligible"] == True].copy()
    eligible["composition_marker_score"] = pd.to_numeric(
        eligible["composition_marker_score"], errors="coerce"
    )
    eligible["nova_group"] = pd.to_numeric(
        eligible["nova_group"], errors="coerce"
    )

    # Week ending = today
    week_ending = datetime.now().strftime("%Y-%m-%d")

    # Avoid duplicate rows if this script runs more than once on the same day
    cursor.execute(
        "DELETE FROM weekly_brand_summary WHERE week_ending = ?",
        (week_ending,)
    )

    # Group by primary_brand + category
    grouped = eligible.groupby(["primary_brand", "query_category"])

    rows_inserted = 0
    for (primary_brand, category), group in grouped:
        if len(group) == 0:
            continue

        product_count    = len(group)
        avg_score        = group["composition_marker_score"].mean()
        pct_nova4        = (
            (group["nova_group"] == 4.0).sum() / product_count * 100
        )
        pct_claims       = (
            (group["ingredient_based_claim_signal_count"].fillna(0) > 0).sum() /
            product_count * 100
        )
        pct_sweetener    = (
            group["has_artificial_sweetener"]
            .apply(lambda x: 1 if x == True or x == 1 else 0)
            .sum() / product_count * 100
        )

        # Top ingredient-based claim signal for this brand/category
        # (not a pack claim — see scope note above)
        all_claims = []
        for claims in group["ingredient_based_claim_signals_found"].dropna():
            all_claims.extend(str(claims).split("|"))
        top_claim = (
            max(set(all_claims), key=all_claims.count)
            if all_claims else None
        )

        cursor.execute("""
            INSERT INTO weekly_brand_summary (
                week_ending, primary_brand, query_category,
                product_count, avg_composition_marker_score,
                pct_nova4, pct_with_ingredient_based_claim_signals,
                pct_with_artificial_sweetener,
                top_ingredient_based_claim_signal, run_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            week_ending, primary_brand, category,
            int(product_count), round(float(avg_score), 1) if pd.notna(avg_score) else None,
            round(float(pct_nova4), 1),
            round(float(pct_claims), 1),
            round(float(pct_sweetener), 1),
            top_claim, timestamp
        ))
        rows_inserted += 1

    conn.commit()
    print(f"  Weekly brand summary: {rows_inserted} brand/category rows inserted")


# ── Power BI CSV export ───────────────────────────────────────────────────────

def export_powerbi_csvs(df, timestamp):
    """
    Write two clean CSVs for Power BI connection:
    - powerbi_products_<timestamp>.csv  — products + nutrition
    - powerbi_analysis_<timestamp>.csv  — analysis fields + flags

    These are flat, clean, Power BI-ready. No processing needed in DAX.
    utf-8-sig encoding for Excel/Power BI Windows compatibility.
    """
    # Products CSV — PRODUCT_COLS already includes primary_country, no
    # need to append it again
    product_cols_csv = [c for c in PRODUCT_COLS if c in df.columns]
    df_products = df[product_cols_csv].copy()
    products_path = os.path.join(
        SAMPLE_DIR, f"powerbi_products_{timestamp}.csv"
    )
    df_products.to_csv(products_path, index=False, encoding="utf-8-sig")
    print(f"  Power BI products CSV → powerbi_products_{timestamp}.csv "
          f"({len(df_products)} rows)")

    # Analysis CSV
    analysis_cols_csv = [c for c in ANALYSIS_COLS if c in df.columns]
    df_analysis = df[analysis_cols_csv].copy()
    analysis_path = os.path.join(
        SAMPLE_DIR, f"powerbi_analysis_{timestamp}.csv"
    )
    df_analysis.to_csv(analysis_path, index=False, encoding="utf-8-sig")
    print(f"  Power BI analysis CSV → powerbi_analysis_{timestamp}.csv "
          f"({len(df_analysis)} rows)")


# ── Ingestion log ─────────────────────────────────────────────────────────────

def log_run(conn, timestamp, source, input_file, rows_in,
            p_ins, p_upd, a_ins, a_upd, status, notes=""):
    """Write a run record to ingestion_log."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ingestion_log (
            run_timestamp, source, input_file, category,
            rows_in_file, products_inserted, products_updated,
            analysis_inserted, analysis_updated, status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, source, os.path.basename(input_file), "all",
        rows_in, p_ins, p_upd, a_ins, a_upd, status, notes
    ))
    conn.commit()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Load analyzed data into SQLite.")
    parser.add_argument(
        "--source", choices=["api", "bulk_export"], default="api",
        help="Data source for this run, recorded in ingestion_log "
             "(default: api). Use bulk_export for full OFF bulk-export runs."
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\nFood & Beverage Positioning Radar — load.py")
    print(f"Run timestamp: {timestamp}")
    print(f"Source: {args.source}")

    # ── Load analyzed CSV ─────────────────────────────────────────────────────
    input_path = find_latest_analyzed(SAMPLE_DIR)
    print(f"\n  Input file: {os.path.basename(input_path)}")
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    print(f"  Rows: {len(df)}")

    # ── Connect to SQLite ─────────────────────────────────────────────────────
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")   # safer concurrent writes
    conn.execute("PRAGMA foreign_keys=ON;")

    try:
        # ── Initialise schema ─────────────────────────────────────────────────
        init_db(conn)

        # ── Load products ─────────────────────────────────────────────────────
        print(f"\n  Loading products table...")
        p_ins, p_upd = load_products(df, conn, timestamp)
        print(f"  Products: {p_ins} inserted, {p_upd} updated")

        # ── Load product analysis ─────────────────────────────────────────────
        print(f"\n  Loading product_analysis table...")
        a_ins, a_upd = load_product_analysis(df, conn, timestamp)
        print(f"  Product analysis: {a_ins} inserted, {a_upd} updated")

        # ── Compute weekly brand summary ──────────────────────────────────────
        print(f"\n  Computing weekly brand summary...")
        compute_weekly_brand_summary(df, conn, timestamp)

        # ── Export Power BI CSVs ──────────────────────────────────────────────
        print(f"\n  Exporting Power BI CSVs...")
        export_powerbi_csvs(df, timestamp)

        # ── Log the run ───────────────────────────────────────────────────────
        log_run(
            conn, timestamp, args.source, input_path, len(df),
            p_ins, p_upd, a_ins, a_upd, "success"
        )

        # ── Summary ───────────────────────────────────────────────────────────
        print(f"\n  -- Summary --------------------------------------------------")
        print(f"  Database: {DB_PATH}")

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM product_analysis WHERE composition_marker_score IS NOT NULL")
        total_analyzed = cursor.fetchone()[0]

        cursor.execute("""
            SELECT composition_marker_band, COUNT(*) as cnt
            FROM product_analysis
            WHERE composition_marker_band IS NOT NULL
            GROUP BY composition_marker_band
            ORDER BY cnt DESC
        """)
        bands = cursor.fetchall()

        cursor.execute("""
            SELECT primary_brand, AVG(composition_marker_score) as avg_score, COUNT(*) as cnt
            FROM products p
            JOIN product_analysis a ON p.barcode = a.barcode
            WHERE a.composition_marker_score IS NOT NULL
            GROUP BY primary_brand
            HAVING cnt >= 3
            ORDER BY avg_score DESC
            LIMIT 15
        """)
        top_brands = cursor.fetchall()

        print(f"  Total products in DB:       {total_products}")
        print(f"  Total ingredient-analyzed:  {total_analyzed}")
        print(f"\n  Composition marker band distribution:")
        for band, cnt in bands:
            print(f"    {band:<25} {cnt}")
        print(f"\n  Brands with highest average composition marker score (min 3 products):")
        for brand, avg, cnt in top_brands:
            print(f"    {str(brand):<35} avg={avg:.1f}  n={cnt}")

        cursor.execute("SELECT * FROM ingestion_log ORDER BY id DESC LIMIT 3")
        logs = cursor.fetchall()
        print(f"\n  Recent ingestion log:")
        for log in logs:
            print(f"    {log}")

    except Exception as e:
        log_run(
            conn, timestamp, args.source, input_path, len(df),
            0, 0, 0, 0, "failed", str(e)
        )
        raise

    finally:
        conn.close()

    print(f"\n  Done.\n")


if __name__ == "__main__":
    main()