"""
db_summary.py
--------------
Final reporting aggregation layer. Runs at the end of the full pipeline:

    load.py -> merge_scores.py -> tag_claims.py -> db_summary.py

Queries the fully populated SQLite database directly (products JOIN
product_analysis) — not intermediate CSVs, since the fully enriched
fields (claim taxonomy, benchmark flags, positioning_composition_gap)
only exist in the database after merge_scores.py and tag_claims.py have
run. This is a different job from those two scripts: they do
product-level classification; this script does reporting aggregation.

IMPORTANT — full snapshot, not weekly diff:
    Every run of this script recomputes the summary from the CURRENT
    FULL database snapshot, regardless of whether that snapshot was
    built via a one-time bulk load or updated incrementally via a
    weekly API diff. This avoids reporting "products changed this week"
    as if it were "the market this week" — see docs/ADR.md ADR-001 for
    the bulk-export-then-diff production strategy this assumes.

    SOURCE_SCOPE is always "full_database_snapshot" for this reason; it
    exists as an explicit field (not just a comment) so a future partial
    or experimental aggregation mode would be visibly distinguishable
    from the standard one.

Tables created (DDL owned by this script, not load.py):

    weekly_brand_positioning_summary
        Grain: week_ending + run_timestamp + source_scope + primary_brand
        + query_category. One row per period per brand/category. Existing
        rows for the same week_ending + source_scope are deleted before
        inserting a fresh snapshot, so reruns on the same day don't
        duplicate trend rows — but rows from PRIOR week_ending values are
        preserved, which is what makes monthly/weekly trend queries (e.g.
        "% of products with a protein claim over time") possible.

        Coverage denominators: averages (avg_composition_marker_score,
        avg_positioning_composition_gap) are computed over however many
        products in the group actually have that score — pandas .mean()
        silently skips missing values. positioning_gap_scored_count /
        pct_positioning_gap_scored and claim_tagged_count /
        pct_claim_tagged make that real denominator explicit, so a
        group with low scoring coverage isn't misread as if its average
        reflected the full product_count.

        Two pack-claim percentages are reported for the same reason:
        pct_with_pack_claims is over the full group (total observed
        coverage), pct_with_pack_claims_among_analyzed is over only the
        subset that actually underwent pack-image analysis (claim
        prevalence given analysis happened). The first answers "what
        share of everything we've observed has extracted claims?"; the
        second answers "among products we actually analyzed, how many
        had claims?"

        top_claim_category_1/2 are the mathematically most common
        category including NO_CLAIM/none. top_detected_claim_category_1/2
        exclude NO_CLAIM/none, surfacing the most common ACTUAL
        positioning territory even in a group dominated by untagged or
        no-claim products.

        pct_no_claim interpretation: NO_CLAIM means no claim was
        identified from whichever evidence layer was available for that
        product (pack-image claims if analyzed, otherwise ingredient/
        name-derived signals only) — not necessarily that the product
        carries no claim at all on its actual packaging. This matches
        docs/UI_LABELS.md's "No claim identified" wording, chosen over
        "No claim exists" for the same reason.

    positioning_example_products
        A small, neutral set of product-level examples for Streamlit /
        Power BI overview pages — NOT a time series. Fully replaced
        (truncate + reinsert) on every run; run_timestamp is recorded
        for provenance only, not for historical accumulation.
        selection_reason values are deliberately neutral — see
        select_positioning_examples() — and avoid any verdict language
        (no "worst", "bad", "red_flag", "offender").

Possible future extension (not implemented in this version):
    Additional per-claim-type percentage fields in
    weekly_brand_positioning_summary — pct_protein_claim, pct_fibre_claim,
    pct_vegan_or_plant_based, pct_organic_or_natural, pct_no_added_sugar,
    pct_sustainability_positioning, pct_heritage_positioning. These are
    straightforward to add (substring/membership checks against
    pack_claims_found, same pattern as the existing pct_* fields) but are
    deferred to keep this first version's scope contained.

Usage:
    python pipeline/db_summary.py

Input:
    database/positioning_radar.db (products + product_analysis, fully
    enriched by load.py + merge_scores.py + tag_claims.py)

Output:
    database/positioning_radar.db (new rows in weekly_brand_positioning_summary
                                    and positioning_example_products)
    data/sample/powerbi_final_products_<timestamp>.csv
    data/sample/powerbi_final_analysis_<timestamp>.csv
    data/sample/powerbi_weekly_brand_positioning_summary_<timestamp>.csv
    data/sample/powerbi_positioning_examples_<timestamp>.csv
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).parent.parent
DB_PATH    = ROOT / "database" / "positioning_radar.db"
SAMPLE_DIR = ROOT / "data" / "sample"

SOURCE_SCOPE = "full_database_snapshot"

# Minimum number of products in a brand/category grouping for it to be
# included in weekly_brand_positioning_summary — avoids noisy percentages
# from groupings with only one or two products.
MIN_GROUP_SIZE = 3

# Cap on examples selected per selection_reason in positioning_example_products,
# EXCEPT functional_claim_portfolio_example, which selects up to 2 examples
# per FUNCTIONAL subcategory (protein, fibre, gut_health, etc.) regardless
# of this cap, to show claim-territory coverage rather than a flat top-N.
PER_REASON_CAP = 5


# ── Schema ────────────────────────────────────────────────────────────────────

DDL_WEEKLY_BRAND_POSITIONING_SUMMARY = """
CREATE TABLE IF NOT EXISTS weekly_brand_positioning_summary (
    id                                      INTEGER PRIMARY KEY AUTOINCREMENT,
    week_ending                             TEXT,
    run_timestamp                           TEXT,
    source_scope                            TEXT,
    primary_brand                           TEXT,
    query_category                          TEXT,
    product_count                           INTEGER,
    pack_analyzed_count                     INTEGER,
    pct_pack_analyzed                       REAL,
    pct_with_pack_claims                    REAL,
    pct_with_pack_claims_among_analyzed     REAL,
    positioning_gap_scored_count            INTEGER,
    pct_positioning_gap_scored              REAL,
    claim_tagged_count                      INTEGER,
    pct_claim_tagged                        REAL,
    pct_functional                          REAL,
    pct_free_of                             REAL,
    pct_natural_organic                     REAL,
    pct_other_claim                         REAL,
    pct_no_claim                            REAL,
    top_claim_category_1                    TEXT,
    top_claim_category_2                    TEXT,
    top_detected_claim_category_1           TEXT,
    top_detected_claim_category_2           TEXT,
    avg_composition_marker_score            REAL,
    avg_positioning_composition_gap         REAL,
    pct_nova4                               REAL,
    pct_with_nutrition_benchmark_flags      REAL,
    pct_with_claim_benchmark_intersections  REAL,
    pct_with_artificial_sweetener           REAL,
    pct_sugar_above_reference               REAL,
    pct_saturated_fat_above_reference       REAL,
    pct_fat_above_reference                 REAL,
    pct_salt_above_reference                REAL
);
"""

DDL_POSITIONING_EXAMPLE_PRODUCTS = """
CREATE TABLE IF NOT EXISTS positioning_example_products (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode                         TEXT,
    product_name                    TEXT,
    primary_brand                   TEXT,
    query_category                  TEXT,
    claim_category_1                TEXT,
    claim_category_2                TEXT,
    pack_claims_found               TEXT,
    nutrition_benchmark_flags       TEXT,
    claim_benchmark_intersections   TEXT,
    positioning_composition_gap     REAL,
    composition_marker_score        REAL,
    nova_group                      REAL,
    nutriscore_grade                TEXT,
    image_url                       TEXT,
    selection_reason                TEXT,
    run_timestamp                   TEXT
);
"""

DDL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_wbps_week ON weekly_brand_positioning_summary(week_ending);",
    "CREATE INDEX IF NOT EXISTS idx_wbps_brand ON weekly_brand_positioning_summary(primary_brand);",
    "CREATE INDEX IF NOT EXISTS idx_pep_reason ON positioning_example_products(selection_reason);",
]


def init_db(conn):
    """Create the reporting tables and indexes if they don't exist."""
    cursor = conn.cursor()
    cursor.execute(DDL_WEEKLY_BRAND_POSITIONING_SUMMARY)
    cursor.execute(DDL_POSITIONING_EXAMPLE_PRODUCTS)
    for idx_sql in DDL_INDEXES:
        cursor.execute(idx_sql)
    conn.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def has_flag(flags_str, code):
    """
    Check whether a specific code is present in a pipe-separated flags
    string, using exact membership rather than substring search.
    Substring search would incorrectly match "fat_above_reference"
    inside "saturated_fat_above_reference" — this avoids that.
    """
    if pd.isna(flags_str) or not str(flags_str).strip():
        return False
    return code in str(flags_str).split("|")


def is_nonempty(val):
    """True if val is a non-null, non-empty string."""
    return pd.notna(val) and str(val).strip() != ""


def load_full_snapshot(conn):
    """Load the full current products + product_analysis snapshot."""
    df = pd.read_sql("""
        SELECT
            p.barcode, p.product_name, p.primary_brand, p.query_category,
            p.primary_country, p.nova_group, p.nutriscore_grade, p.image_url,
            a.composition_marker_score, a.positioning_composition_gap,
            a.positioning_composition_gap_band,
            a.pack_claims_found, a.pack_analysis_attempted, a.claim_source,
            a.claim_category_1, a.claim_category_2,
            a.nutrition_benchmark_flags, a.claim_benchmark_intersections,
            a.has_artificial_sweetener
        FROM products p
        LEFT JOIN product_analysis a ON p.barcode = a.barcode
    """, conn, dtype={"barcode": str})
    return df


# ── Weekly brand positioning summary ──────────────────────────────────────────

def compute_weekly_brand_positioning_summary(df, week_ending, run_timestamp):
    """
    Compute one row per (primary_brand, query_category) grouping,
    reflecting the full current database snapshot. Groupings smaller
    than MIN_GROUP_SIZE are skipped to avoid noisy percentages.

    Coverage denominators: avg_composition_marker_score and
    avg_positioning_composition_gap are computed with pandas .mean(),
    which silently skips missing values — so the average is implicitly
    based on however many products in the group actually have a score,
    not product_count. positioning_gap_scored_count / pct_positioning_gap_scored
    and claim_tagged_count / pct_claim_tagged make that denominator
    explicit, so a low-coverage group's average isn't read as if it
    were based on the full group.

    pct_no_claim interpretation: claim_category_1 == "NO_CLAIM" means
    no claim was identified from whichever evidence layer was
    available for that product (pack-image claims if analyzed,
    otherwise ingredient/name-derived signals only) — not necessarily
    that the product carries no claim at all on its actual packaging.
    See docs/UI_LABELS.md, which uses "No claim identified" rather than
    "No claim exists" for exactly this reason.
    """
    rows = []
    grouped = df.groupby(["primary_brand", "query_category"])

    for (brand, category), group in grouped:
        n = len(group)
        if n < MIN_GROUP_SIZE:
            continue

        pack_analyzed = (group["pack_analysis_attempted"] == 1).sum()
        with_pack_claims = group["pack_claims_found"].apply(is_nonempty).sum()
        pct_with_pack_claims_among_analyzed = (
            float(with_pack_claims) / pack_analyzed * 100 if pack_analyzed > 0 else None
        )

        gap_scored = group["positioning_composition_gap"].notna().sum()
        claim_tagged = group["claim_category_1"].notna().sum()

        cat1_counts = group["claim_category_1"].value_counts()
        pct_functional      = cat1_counts.get("FUNCTIONAL", 0) / n * 100
        pct_free_of         = cat1_counts.get("FREE_OF", 0) / n * 100
        pct_natural_organic = cat1_counts.get("NATURAL_ORGANIC", 0) / n * 100
        pct_other_claim     = cat1_counts.get("OTHER", 0) / n * 100
        pct_no_claim        = cat1_counts.get("NO_CLAIM", 0) / n * 100

        top_cat1 = cat1_counts.idxmax() if len(cat1_counts) else None
        cat2_counts = group["claim_category_2"].value_counts()
        top_cat2 = cat2_counts.idxmax() if len(cat2_counts) else None

        # Top DETECTED category — excludes NO_CLAIM/none, so a group
        # dominated by untagged or no-claim products still surfaces its
        # most common actual positioning territory, if any.
        detected1 = group[
            group["claim_category_1"].notna() & (group["claim_category_1"] != "NO_CLAIM")
        ]
        detected1_counts = detected1["claim_category_1"].value_counts()
        top_detected_cat1 = detected1_counts.idxmax() if len(detected1_counts) else None

        detected2 = group[
            group["claim_category_2"].notna() & (group["claim_category_2"] != "none")
        ]
        detected2_counts = detected2["claim_category_2"].value_counts()
        top_detected_cat2 = detected2_counts.idxmax() if len(detected2_counts) else None

        avg_composition = group["composition_marker_score"].mean()
        avg_gap = group["positioning_composition_gap"].mean()
        pct_nova4 = (group["nova_group"] == 4.0).mean() * 100

        pct_with_benchmark_flags = group["nutrition_benchmark_flags"].apply(is_nonempty).mean() * 100
        pct_with_intersections = group["claim_benchmark_intersections"].apply(is_nonempty).mean() * 100
        pct_sweetener = (group["has_artificial_sweetener"] == 1).mean() * 100

        pct_sugar_ref = group["nutrition_benchmark_flags"].apply(
            lambda x: has_flag(x, "sugar_above_reference")).mean() * 100
        pct_satfat_ref = group["nutrition_benchmark_flags"].apply(
            lambda x: has_flag(x, "saturated_fat_above_reference")).mean() * 100
        pct_fat_ref = group["nutrition_benchmark_flags"].apply(
            lambda x: has_flag(x, "fat_above_reference")).mean() * 100
        pct_salt_ref = group["nutrition_benchmark_flags"].apply(
            lambda x: has_flag(x, "salt_above_reference")).mean() * 100

        rows.append((
            week_ending, run_timestamp, SOURCE_SCOPE, brand, category,
            int(n), int(pack_analyzed),
            round(float(pack_analyzed / n * 100), 1),
            round(float(with_pack_claims / n * 100), 1),
            round(float(pct_with_pack_claims_among_analyzed), 1)
                if pct_with_pack_claims_among_analyzed is not None else None,
            int(gap_scored),
            round(float(gap_scored / n * 100), 1),
            int(claim_tagged),
            round(float(claim_tagged / n * 100), 1),
            round(float(pct_functional), 1), round(float(pct_free_of), 1),
            round(float(pct_natural_organic), 1), round(float(pct_other_claim), 1),
            round(float(pct_no_claim), 1),
            top_cat1, top_cat2,
            top_detected_cat1, top_detected_cat2,
            round(float(avg_composition), 1) if pd.notna(avg_composition) else None,
            round(float(avg_gap), 1) if pd.notna(avg_gap) else None,
            round(float(pct_nova4), 1),
            round(float(pct_with_benchmark_flags), 1),
            round(float(pct_with_intersections), 1),
            round(float(pct_sweetener), 1),
            round(float(pct_sugar_ref), 1), round(float(pct_satfat_ref), 1),
            round(float(pct_fat_ref), 1), round(float(pct_salt_ref), 1),
        ))

    return rows


def write_weekly_brand_positioning_summary(conn, rows, week_ending):
    """
    Delete existing rows for this week_ending + SOURCE_SCOPE before
    inserting, so reruns on the same day don't duplicate trend rows.
    Rows from prior week_ending values are NOT touched — this is what
    makes weekly/monthly trend queries possible.
    """
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM weekly_brand_positioning_summary "
        "WHERE week_ending = ? AND source_scope = ?",
        (week_ending, SOURCE_SCOPE)
    )
    cursor.executemany("""
        INSERT INTO weekly_brand_positioning_summary (
            week_ending, run_timestamp, source_scope, primary_brand, query_category,
            product_count, pack_analyzed_count, pct_pack_analyzed, pct_with_pack_claims,
            pct_with_pack_claims_among_analyzed,
            positioning_gap_scored_count, pct_positioning_gap_scored,
            claim_tagged_count, pct_claim_tagged,
            pct_functional, pct_free_of, pct_natural_organic, pct_other_claim, pct_no_claim,
            top_claim_category_1, top_claim_category_2,
            top_detected_claim_category_1, top_detected_claim_category_2,
            avg_composition_marker_score, avg_positioning_composition_gap,
            pct_nova4, pct_with_nutrition_benchmark_flags, pct_with_claim_benchmark_intersections,
            pct_with_artificial_sweetener,
            pct_sugar_above_reference, pct_saturated_fat_above_reference,
            pct_fat_above_reference, pct_salt_above_reference
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    return len(rows)


# ── Positioning example products ──────────────────────────────────────────────

def select_positioning_examples(df, per_reason_cap=PER_REASON_CAP):
    """
    Select a small, neutral set of product-level examples for overview
    pages. Selection is deterministic (sorted by barcode, or by claim
    count where relevant) for reproducibility — not based on highest/
    lowest score, since ranking by score would read as a "worst/best"
    list. Four selection_reason categories:

    - functional_claim_portfolio_example: up to 2 vision-sourced
      examples per claim_category_2 within FUNCTIONAL, covering the
      range of functional sub-claims (protein, fibre, gut_health, etc).
    - plant_based_positioning_example: products with a vegan or
      plant-based pack claim.
    - protein_positioning_with_benchmark_intersection: products where a
      protein-positioning claim co-occurs with a benchmark signal (see
      tag_claims.py compute_claim_benchmark_intersections()).
    - high_claim_density_example: products with 4 or more distinct pack
      claims, illustrating dense multi-claim positioning architecture.

    A product may appear under more than one selection_reason — this is
    intentional, each row documents a distinct reason that product is a
    useful example, not a unique product registry.
    """
    examples = []

    # Functional claim portfolio examples
    functional = df[
        (df["claim_category_1"] == "FUNCTIONAL") &
        (df["claim_source"] == "vision")
    ]
    for cat2 in sorted(functional["claim_category_2"].dropna().unique()):
        subset = functional[functional["claim_category_2"] == cat2].sort_values("barcode")
        for _, row in subset.head(2).iterrows():
            examples.append((row, "functional_claim_portfolio_example"))

    # Plant-based positioning examples
    plant_based = df[
        df["pack_claims_found"].apply(
            lambda x: is_nonempty(x) and (
                "vegan_claim" in str(x).split("|") or
                "plant_based_claim" in str(x).split("|")
            )
        )
    ].sort_values("barcode")
    for _, row in plant_based.head(per_reason_cap).iterrows():
        examples.append((row, "plant_based_positioning_example"))

    # Protein positioning with benchmark intersection
    protein_intersect = df[
        df["claim_benchmark_intersections"].apply(
            lambda x: is_nonempty(x) and "Protein positioning with" in str(x)
        )
    ].sort_values("barcode")
    for _, row in protein_intersect.head(per_reason_cap).iterrows():
        examples.append((row, "protein_positioning_with_benchmark_intersection"))

    # High claim density examples
    df = df.copy()
    df["_claim_count"] = df["pack_claims_found"].apply(
        lambda x: len(str(x).split("|")) if is_nonempty(x) else 0
    )
    high_density = df[df["_claim_count"] >= 4].sort_values(
        ["_claim_count", "barcode"], ascending=[False, True]
    )
    for _, row in high_density.head(per_reason_cap).iterrows():
        examples.append((row, "high_claim_density_example"))

    return examples


def write_positioning_examples(conn, examples, run_timestamp):
    """
    Full replace: truncate and reinsert on every run. This table is a
    current-state showcase, not a time series — see module docstring.
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM positioning_example_products")

    rows = []
    for row, reason in examples:
        rows.append((
            row["barcode"], row["product_name"], row["primary_brand"],
            row["query_category"], row.get("claim_category_1"),
            row.get("claim_category_2"), row.get("pack_claims_found"),
            row.get("nutrition_benchmark_flags"),
            row.get("claim_benchmark_intersections"),
            float(row["positioning_composition_gap"]) if pd.notna(row.get("positioning_composition_gap")) else None,
            float(row["composition_marker_score"]) if pd.notna(row.get("composition_marker_score")) else None,
            float(row["nova_group"]) if pd.notna(row.get("nova_group")) else None,
            row.get("nutriscore_grade"), row.get("image_url"),
            reason, run_timestamp
        ))

    cursor.executemany("""
        INSERT INTO positioning_example_products (
            barcode, product_name, primary_brand, query_category,
            claim_category_1, claim_category_2, pack_claims_found,
            nutrition_benchmark_flags, claim_benchmark_intersections,
            positioning_composition_gap, composition_marker_score,
            nova_group, nutriscore_grade, image_url,
            selection_reason, run_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    return len(rows)


# ── Power BI exports ───────────────────────────────────────────────────────────

def export_powerbi_csvs(df, summary_rows, examples, timestamp):
    """Write final, reporting-stage Power BI CSVs — distinct from the
    ingredient-stage exports from load.py and the product-level tagged
    export from tag_claims.py."""

    products_path = SAMPLE_DIR / f"powerbi_final_products_{timestamp}.csv"
    product_cols = [
        "barcode", "product_name", "primary_brand", "query_category",
        "primary_country", "nova_group", "nutriscore_grade", "image_url",
    ]
    df[product_cols].to_csv(products_path, index=False, encoding="utf-8-sig")

    analysis_path = SAMPLE_DIR / f"powerbi_final_analysis_{timestamp}.csv"
    analysis_cols = [c for c in df.columns if c not in product_cols]
    df[["barcode"] + analysis_cols].to_csv(analysis_path, index=False, encoding="utf-8-sig")

    summary_cols = [
        "week_ending", "run_timestamp", "source_scope", "primary_brand", "query_category",
        "product_count", "pack_analyzed_count", "pct_pack_analyzed", "pct_with_pack_claims",
        "pct_with_pack_claims_among_analyzed",
        "positioning_gap_scored_count", "pct_positioning_gap_scored",
        "claim_tagged_count", "pct_claim_tagged",
        "pct_functional", "pct_free_of", "pct_natural_organic", "pct_other_claim", "pct_no_claim",
        "top_claim_category_1", "top_claim_category_2",
        "top_detected_claim_category_1", "top_detected_claim_category_2",
        "avg_composition_marker_score", "avg_positioning_composition_gap",
        "pct_nova4", "pct_with_nutrition_benchmark_flags", "pct_with_claim_benchmark_intersections",
        "pct_with_artificial_sweetener",
        "pct_sugar_above_reference", "pct_saturated_fat_above_reference",
        "pct_fat_above_reference", "pct_salt_above_reference",
    ]
    summary_path = SAMPLE_DIR / f"powerbi_weekly_brand_positioning_summary_{timestamp}.csv"
    pd.DataFrame(summary_rows, columns=summary_cols).to_csv(
        summary_path, index=False, encoding="utf-8-sig"
    )

    examples_rows = []
    for row, reason in examples:
        examples_rows.append({
            "barcode": row["barcode"], "product_name": row["product_name"],
            "primary_brand": row["primary_brand"], "query_category": row["query_category"],
            "claim_category_1": row.get("claim_category_1"),
            "claim_category_2": row.get("claim_category_2"),
            "pack_claims_found": row.get("pack_claims_found"),
            "nutrition_benchmark_flags": row.get("nutrition_benchmark_flags"),
            "claim_benchmark_intersections": row.get("claim_benchmark_intersections"),
            "positioning_composition_gap": row.get("positioning_composition_gap"),
            "composition_marker_score": row.get("composition_marker_score"),
            "nova_group": row.get("nova_group"), "nutriscore_grade": row.get("nutriscore_grade"),
            "image_url": row.get("image_url"), "selection_reason": reason,
        })
    examples_path = SAMPLE_DIR / f"powerbi_positioning_examples_{timestamp}.csv"
    pd.DataFrame(examples_rows).to_csv(examples_path, index=False, encoding="utf-8-sig")

    return products_path, analysis_path, summary_path, examples_path


# ── Main ──────────────────────────────────────────────────────────────────────


# ── Ozempic / market trend tracker ────────────────────────────────────────────

import re as _re

def _parse_pack_size_g(quantity_val) -> float | None:
    """
    Extract numeric pack size in grams from the quantity field.
    Handles common formats: "400 g", "400g", "1.5 kg", "500 ml", etc.
    Returns None for unrecognised formats or non-gram units.
    Only grams are returned (kg converted); ml/cl/l excluded — volume
    and weight are not comparable across product types.
    """
    if not isinstance(quantity_val, str) or not quantity_val.strip():
        return None
    s = quantity_val.strip().lower()
    # Match number followed by g or kg
    m = _re.search(r"([\d.,]+)\s*(kg|g)\b", s)
    if not m:
        return None
    try:
        val = float(m.group(1).replace(",", "."))
        return val * 1000 if m.group(2) == "kg" else val
    except ValueError:
        return None


def compute_market_trend_weekly(df: "pd.DataFrame", week_ending: str,
                                 run_timestamp: str) -> list[dict]:
    """
    Compute one row per query_category for market_trend_weekly.

    All metrics are computed on the FULL current DB snapshot (not just
    products ingested in this run). This means each weekly row represents
    a cross-sectional view of the entire database at the time of the run,
    not an incremental delta. Longitudinal trend is visible by comparing
    rows across weeks using the 3-month rolling window at read time.

    Products with missing nutrient values are excluded per-metric
    (not excluded from the whole row) so that coverage differences
    between metrics are transparent.
    """
    import numpy as np
    from datetime import datetime, timedelta

    cutoff_90d = (datetime.now() - timedelta(days=90)).timestamp()
    rows = []

    for category in df["query_category"].dropna().unique():
        cat = df[df["query_category"] == category].copy()
        n = len(cat)
        if n == 0:
            continue

        # ── Coverage ──────────────────────────────────────────────────────────
        # New products: created_t is a UNIX timestamp in the DB
        try:
            created_numeric = pd.to_numeric(cat["created_t"], errors="coerce")
            new_count = int((created_numeric > cutoff_90d).sum())
        except Exception:
            new_count = 0

        pack_analyzed = int(
            (pd.to_numeric(cat.get("pack_analysis_attempted", pd.Series()),
                           errors="coerce") == 1).sum()
        )

        # ── Nutrient helpers ──────────────────────────────────────────────────
        def _col(name):
            return pd.to_numeric(cat.get(name, pd.Series()), errors="coerce")

        protein  = _col("protein_100g")
        energy   = _col("energy_kcal")
        fiber    = _col("fiber_100g")
        carbs    = _col("carbs_100g")
        sugars   = _col("sugars_100g")
        nova     = _col("nova_group")

        # Protein pivot
        valid_pe  = protein.notna() & energy.notna() & (energy > 0)
        avg_prot_kcal = float((protein[valid_pe] / energy[valid_pe] * 100).mean())             if valid_pe.sum() > 0 else None
        pct_high_protein = float(
            (protein.notna() & (protein >= 20)).sum() / n * 100
        )

        # Fibre/carb
        valid_fc  = fiber.notna() & carbs.notna() & (carbs > 0)
        avg_fib_carb = float((fiber[valid_fc] / carbs[valid_fc]).mean())             if valid_fc.sum() > 0 else None

        # NOVA
        total_nova = nova.notna().sum()
        def nova_pct(g):
            return float((nova == g).sum() / n * 100) if n > 0 else None
        pct_n1, pct_n2, pct_n3, pct_n4 = (
            nova_pct(1.0), nova_pct(2.0), nova_pct(3.0), nova_pct(4.0)
        )
        n1_count = (nova == 1.0).sum()
        n4_count = (nova == 4.0).sum()
        nova4_ratio = float(n4_count / n1_count) if n1_count > 0 else None

        # Sugar/carb (Ozempic tongue)
        valid_sc  = sugars.notna() & carbs.notna() & (carbs > 0)
        avg_sug_carb = float((sugars[valid_sc] / carbs[valid_sc]).mean())             if valid_sc.sum() > 0 else None

        # Pack size
        pack_sizes = cat.get("quantity", pd.Series()).apply(_parse_pack_size_g)
        pack_sizes = pack_sizes.dropna()
        median_pack = float(pack_sizes.median()) if len(pack_sizes) > 0 else None

        # Claims
        def claim_pct(code):
            return float(
                (cat.get("claim_category_1", pd.Series()) == code).sum() / n * 100
            )
        pct_func  = claim_pct("FUNCTIONAL")
        pct_free  = claim_pct("FREE_OF")
        pct_nat   = claim_pct("NATURAL_ORGANIC")
        pct_none  = claim_pct("NO_CLAIM")

        # Additives — from OFF's own additives_tags field (not our formula).
        # Measures E-number presence directly from the label, computed by OFF.
        additives_raw = cat.get("additives_tags", pd.Series()).fillna("")
        additive_counts = additives_raw.apply(
            lambda x: len([a for a in str(x).split("|") if a.strip()])
        )
        avg_additive_count = float(additive_counts.mean()) if len(additive_counts) > 0 else None
        pct_with_additives = float(
            (additive_counts > 0).sum() / n * 100
        ) if n > 0 else None

        rows.append({
            "week_ending":                  week_ending,
            "run_timestamp":                run_timestamp,
            "query_category":               category,
            "product_count":                n,
            "new_product_count":            new_count,
            "pack_analyzed_count":          pack_analyzed,
            "pct_pack_analyzed":            round(pack_analyzed / n * 100, 2) if n else None,
            "avg_protein_per_kcal":         round(avg_prot_kcal, 4) if avg_prot_kcal is not None else None,
            "pct_high_protein":             round(pct_high_protein, 2),
            "avg_fiber_per_carb":           round(avg_fib_carb, 4) if avg_fib_carb is not None else None,
            "pct_nova1":                    round(pct_n1, 2) if pct_n1 is not None else None,
            "pct_nova2":                    round(pct_n2, 2) if pct_n2 is not None else None,
            "pct_nova3":                    round(pct_n3, 2) if pct_n3 is not None else None,
            "pct_nova4":                    round(pct_n4, 2) if pct_n4 is not None else None,
            "nova4_to_nova1_ratio":         round(nova4_ratio, 3) if nova4_ratio is not None else None,
            "avg_sugar_per_carb":           round(avg_sug_carb, 4) if avg_sug_carb is not None else None,
            "median_pack_size_g":           round(median_pack, 1) if median_pack is not None else None,
            "pct_functional_claims":        round(pct_func, 2),
            "pct_free_of_claims":           round(pct_free, 2),
            "pct_natural_organic_claims":   round(pct_nat, 2),
            "pct_no_claim":                 round(pct_none, 2),
            "avg_additives_count":           round(avg_additive_count, 2) if avg_additive_count is not None else None,
            "pct_with_additives":            round(pct_with_additives, 2) if pct_with_additives is not None else None,
        })

    return rows


def write_market_trend_weekly(conn, rows: list[dict], week_ending: str) -> int:
    """
    Insert market trend rows, replacing any existing rows for this week_ending.
    Uses INSERT OR REPLACE so re-running db_summary.py is idempotent.
    """
    if not rows:
        return 0
    conn.execute(
        "DELETE FROM market_trend_weekly WHERE week_ending = ?", (week_ending,)
    )
    cols = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    col_str = ", ".join(cols)
    for row in rows:
        conn.execute(
            f"INSERT INTO market_trend_weekly ({col_str}) VALUES ({placeholders})",
            [row[c] for c in cols],
        )
    conn.commit()
    return len(rows)


def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # week_ending is the snapshot date this run was executed, used as
    # the reporting period boundary. In development this is simply
    # today's date; in a weekly production schedule it represents the
    # week-ending / reporting snapshot date for that run.
    week_ending = datetime.now().strftime("%Y-%m-%d")
    print(f"\nFood & Beverage Positioning Radar - db_summary.py")
    print(f"Run timestamp: {timestamp}")
    print(f"Week ending:   {week_ending}")
    print(f"Source scope:  {SOURCE_SCOPE} (always — see module docstring)\n")

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    print("  Loading full products + product_analysis snapshot from DB...")
    df = load_full_snapshot(conn)
    print(f"  Loaded {len(df):,} products")

    pack_analyzed_total = (df["pack_analysis_attempted"] == 1).sum()
    tagged_total = df["claim_category_1"].notna().sum()
    print(f"  Pack-image analyzed: {pack_analyzed_total:,}")
    print(f"  Claim-tagged:        {tagged_total:,}")

    # ── Weekly brand positioning summary ──────────────────────────────────────
    print(f"\n  Computing weekly_brand_positioning_summary "
          f"(brand/category groupings with >= {MIN_GROUP_SIZE} products)...")
    summary_rows = compute_weekly_brand_positioning_summary(df, week_ending, timestamp)
    n_written = write_weekly_brand_positioning_summary(conn, summary_rows, week_ending)
    print(f"  Wrote {n_written:,} brand/category rows for week_ending={week_ending}")

    # ── Positioning example products ──────────────────────────────────────────
    print(f"\n  Selecting positioning_example_products...")
    examples = select_positioning_examples(df)
    n_examples = write_positioning_examples(conn, examples, timestamp)
    print(f"  Wrote {n_examples:,} example rows")

    by_reason = {}
    for _, reason in examples:
        by_reason[reason] = by_reason.get(reason, 0) + 1
    for reason, n in by_reason.items():
        print(f"    {reason:<50} {n}")


    # ── Market trend weekly (Ozempic / longitudinal tracker) ─────────────────
    # Runs silently every time db_summary.py executes. Each row is a
    # timestamped cross-sectional snapshot of all key metrics per category.
    # Compare rows across weeks to build the longitudinal signal.
    # See docs/ADR.md ADR-014 and the project brief's Phase 3F section.
    trend_rows = compute_market_trend_weekly(df, week_ending, timestamp)
    n_trend = write_market_trend_weekly(conn, trend_rows, week_ending)
    print(f"  Market trend snapshot: {n_trend} category rows written "
          f"to market_trend_weekly (week_ending={week_ending})")

    conn.close()

    # ── Power BI exports ───────────────────────────────────────────────────────
    print(f"\n  Writing final Power BI exports...")
    products_path, analysis_path, summary_path, examples_path = export_powerbi_csvs(
        df, summary_rows, examples, timestamp
    )
    print(f"  -> {products_path.name}")
    print(f"  -> {analysis_path.name}")
    print(f"  -> {summary_path.name}")
    print(f"  -> {examples_path.name}")

    print(f"\n  Done. Final reporting tables and exports are ready.")
    print(f"  Next step: streamlit run app.py\n")


if __name__ == "__main__":
    main()
