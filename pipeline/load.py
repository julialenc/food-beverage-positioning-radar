"""
load.py
-------
Loads analyzed product data into SQLite database.

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
    - weekly_brand_summary pre-aggregated for early pipeline review
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
import csv
import pandas as pd
import sqlite3
import os
from datetime import datetime


# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(ROOT, "data", "sample")
DB_DIR     = os.path.join(ROOT, "database")
DB_PATH    = os.path.join(DB_DIR, "positioning_radar.db")
COMPANY_MAP_PATH = os.path.join(ROOT, "data", "reference", "company_brand_mapping.csv")
PRODUCT_MAPPING_OVERRIDE_PATH = os.path.join(
    ROOT, "data", "reference", "reviewed_product_mapping_overrides.csv"
)
COMPANY_OTHER_LABEL = "Other / not mapped to a company"
COMPANY_MANUAL_REVIEW_LABEL = "Manual review"


# ── Schema ────────────────────────────────────────────────────────────────────

DDL_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    barcode                      TEXT PRIMARY KEY,
    product_name                 TEXT,
    brands                       TEXT,
    primary_brand                 TEXT,
    off_brands_raw                TEXT,
    off_brand_tokens              TEXT,
    legacy_primary_brand          TEXT,
    brand_entity_raw              TEXT,
    brand_entity_source           TEXT,
    normalized_brand              TEXT,
    brand_family                  TEXT,
    brand_alias_source            TEXT,
    brand_alias_review_status     TEXT,
    resolved_company              TEXT,
    company_ownership_resolution_status TEXT,
    company_mapping_source        TEXT,
    quantity                     TEXT,
    packaging                    TEXT,
    query_category                TEXT,
    off_categories                 TEXT,
    countries                    TEXT,
    primary_country                TEXT,
    observed_market_region_codes   TEXT,      -- pipe-separated region codes, see country_region_mapping.csv
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
    ,
    energy_kcal_off_raw           REAL,
    fat_100g_off_raw              REAL,
    saturated_fat_100g_off_raw    REAL,
    carbs_100g_off_raw            REAL,
    sugars_100g_off_raw           REAL,
    fiber_100g_off_raw            REAL,
    protein_100g_off_raw          REAL,
    salt_100g_off_raw             REAL,
    nutrition_quality_status      TEXT,
    outlier_type                  TEXT,
    include_in_product_table      INTEGER,
    include_in_aggregates         INTEGER,
    include_in_charts             INTEGER,
    nutrition_quality_reason      TEXT,
    energy_kcal_missing           INTEGER,
    fat_100g_missing              INTEGER,
    saturated_fat_100g_missing    INTEGER,
    carbs_100g_missing            INTEGER,
    sugars_100g_missing           INTEGER,
    fiber_100g_missing            INTEGER,
    protein_100g_missing          INTEGER,
    salt_100g_missing             INTEGER
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
    image_context                          TEXT,
    claim_extraction_status                TEXT,
    detected_claim_phrases                 TEXT,
    claims_json                            TEXT,
    release_run_id                         TEXT,
    sampling_region                        TEXT,
    sampling_category                      TEXT,
    sample_component                       TEXT,
    primary_stratum_id                     TEXT,
    sampling_weight                        REAL,
    weight_status                          TEXT,

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

DDL_MARKET_TREND_WEEKLY = """
CREATE TABLE IF NOT EXISTS market_trend_weekly (
    id                           INTEGER PRIMARY KEY AUTOINCREMENT,
    week_ending                  TEXT NOT NULL,
    run_timestamp                TEXT NOT NULL,
    query_category               TEXT NOT NULL,

    -- Coverage
    product_count                INTEGER,   -- products in DB for this category
    new_product_count            INTEGER,   -- created_t in last 90 days (market launches)
    pack_analyzed_count          INTEGER,   -- products with pack_analysis_attempted=1
    pct_pack_analyzed            REAL,

    -- Protein pivot signals (GLP-1 compatibility reformulation)
    avg_protein_per_kcal         REAL,      -- protein_100g / energy_kcal * 100
    pct_high_protein             REAL,      -- % products with protein_100g >= 20g

    -- Fibre signals
    avg_fiber_per_carb           REAL,      -- fiber_100g / carbs_100g

    -- UPF / NOVA distribution
    pct_nova1                    REAL,
    pct_nova2                    REAL,
    pct_nova3                    REAL,
    pct_nova4                    REAL,      -- ultra-processed share — key signal
    nova4_to_nova1_ratio         REAL,

    -- Ozempic tongue: sweetness/intensity
    avg_sugar_per_carb           REAL,      -- sugars_100g / carbs_100g

    -- Pack size (portion-control architecture)
    median_pack_size_g           REAL,      -- parsed from quantity field, grams only

    -- Positioning claim distribution
    pct_functional_claims        REAL,
    pct_free_of_claims           REAL,
    pct_natural_organic_claims   REAL,
    pct_no_claim                 REAL,

    -- Ingredient processing
    -- Additives — E-number presence from OFF's own additives_tags (not a proprietary formula)
    avg_additives_count          REAL,      -- avg number of E-numbers per product in category
    pct_with_additives           REAL,      -- % products with at least one additive

    UNIQUE(week_ending, query_category)
);
"""

DDL_CATEGORY_REGION_AVERAGES = """
CREATE TABLE IF NOT EXISTS category_region_averages (
    snapshot                 TEXT NOT NULL,
    query_category           TEXT NOT NULL,
    region                   TEXT NOT NULL,
    energy_kcal              REAL,
    protein_per_kcal         REAL,
    fiber_per_kcal           REAL,
    satfat_per_kcal          REAL,
    sugars_per_kcal          REAL,
    sugars_100g              REAL,
    salt_100g                REAL,
    PRIMARY KEY (snapshot, query_category, region)
);
"""


DDL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brands);",
    "CREATE INDEX IF NOT EXISTS idx_products_primary_brand ON products(primary_brand);",
    "CREATE INDEX IF NOT EXISTS idx_products_normalized_brand ON products(normalized_brand);",
    "CREATE INDEX IF NOT EXISTS idx_products_resolved_company ON products(resolved_company);",
    "CREATE INDEX IF NOT EXISTS idx_products_ingested_at ON products(ingested_at);",
    "CREATE INDEX IF NOT EXISTS idx_products_category ON products(query_category);",
    "CREATE INDEX IF NOT EXISTS idx_products_country ON products(primary_country);",
    "CREATE INDEX IF NOT EXISTS idx_products_nova ON products(nova_group);",
    "CREATE INDEX IF NOT EXISTS idx_products_modified ON products(last_modified_t);",
    "CREATE INDEX IF NOT EXISTS idx_products_snapshot_category ON products(ingested_at, query_category);",
    "CREATE INDEX IF NOT EXISTS idx_products_snapshot_company ON products(ingested_at, resolved_company);",
    "CREATE INDEX IF NOT EXISTS idx_products_snapshot_category_company ON products(ingested_at, query_category, resolved_company);",
    "CREATE INDEX IF NOT EXISTS idx_products_snapshot_category_brand ON products(ingested_at, query_category, normalized_brand, primary_brand);",
    "CREATE INDEX IF NOT EXISTS idx_products_snapshot_nutriscore ON products(ingested_at, nutriscore_grade);",
    "CREATE INDEX IF NOT EXISTS idx_products_snapshot_product_name ON products(ingested_at, product_name);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_score ON product_analysis(composition_marker_score);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_band ON product_analysis(composition_marker_band);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_claim_source ON product_analysis(claim_source);",
    "CREATE INDEX IF NOT EXISTS idx_category_region_averages_snapshot ON category_region_averages(snapshot);",
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
    cursor.execute(DDL_MARKET_TREND_WEEKLY)
    cursor.execute(DDL_CATEGORY_REGION_AVERAGES)
    conn.commit()
    migrate_products_schema(conn)
    for idx_sql in DDL_INDEXES:
        cursor.execute(idx_sql)
    conn.commit()
    print(f"  Database initialised: {DB_PATH}")


PRODUCT_COLUMN_TYPES = {
    "off_brands_raw": "TEXT",
    "off_brand_tokens": "TEXT",
    "legacy_primary_brand": "TEXT",
    "brand_entity_raw": "TEXT",
    "brand_entity_source": "TEXT",
    "normalized_brand": "TEXT",
    "brand_family": "TEXT",
    "brand_alias_source": "TEXT",
    "brand_alias_review_status": "TEXT",
    "resolved_company": "TEXT",
    "company_ownership_resolution_status": "TEXT",
    "company_mapping_source": "TEXT",
    "energy_kcal_off_raw": "REAL",
    "fat_100g_off_raw": "REAL",
    "saturated_fat_100g_off_raw": "REAL",
    "carbs_100g_off_raw": "REAL",
    "sugars_100g_off_raw": "REAL",
    "fiber_100g_off_raw": "REAL",
    "protein_100g_off_raw": "REAL",
    "salt_100g_off_raw": "REAL",
    "nutrition_quality_status": "TEXT",
    "outlier_type": "TEXT",
    "include_in_product_table": "INTEGER",
    "include_in_aggregates": "INTEGER",
    "include_in_charts": "INTEGER",
    "nutrition_quality_reason": "TEXT",
    "energy_kcal_missing": "INTEGER",
    "fat_100g_missing": "INTEGER",
    "saturated_fat_100g_missing": "INTEGER",
    "carbs_100g_missing": "INTEGER",
    "sugars_100g_missing": "INTEGER",
    "fiber_100g_missing": "INTEGER",
    "protein_100g_missing": "INTEGER",
    "salt_100g_missing": "INTEGER",
}


def migrate_products_schema(conn):
    """Add product columns introduced after the original SQLite schema."""
    cursor = conn.cursor()
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(products)")}
    added = []
    for column, column_type in PRODUCT_COLUMN_TYPES.items():
        if column not in existing:
            cursor.execute(f"ALTER TABLE products ADD COLUMN {column} {column_type}")
            added.append(column)
    conn.commit()
    if added:
        print(f"  Products schema migrated: added {len(added)} columns")


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


def _normalize_brand(value):
    import re
    import unicodedata

    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = text.replace("&", " and ")
    text = re.sub(r"['`´’]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_review_key(value):
    import re
    import unicodedata

    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = text.replace("&", " and ")
    text = re.sub(r"['`´’]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _split_scope_values(value):
    return [v.strip() for v in str(value or "").split("|") if v.strip()]


def _any_token_match(source_value, tokens):
    if not tokens:
        return False
    source_tokens = {
        v.strip().lower()
        for v in str(source_value or "").split("|")
        if v.strip()
    }
    return any(token.lower() in source_tokens for token in tokens)


def _row_scope_matches(row, countries, region_codes):
    include_regions = _split_scope_values(row.get("region_codes_include", ""))
    exclude_regions = _split_scope_values(row.get("region_codes_exclude", ""))
    include_countries = _split_scope_values(row.get("country_tags_include", ""))
    exclude_countries = _split_scope_values(row.get("country_tags_exclude", ""))

    if not include_regions and not include_countries:
        return False
    if exclude_regions and _any_token_match(region_codes, exclude_regions):
        return False
    if exclude_countries and _any_token_match(countries, exclude_countries):
        return False

    return (
        _any_token_match(region_codes, include_regions)
        or _any_token_match(countries, include_countries)
    )


def load_company_mapping_index():
    if not os.path.exists(COMPANY_MAP_PATH):
        return {}

    by_brand = {}
    with open(COMPANY_MAP_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            company = (row.get("parent_company") or "").strip()
            brand = (row.get("primary_brand_db") or "").strip()
            if not company or not brand:
                continue
            record = {
                "parent_company": company,
                "status": (
                    (row.get("ownership_resolution_status") or "").strip().lower()
                    or "direct"
                ),
                "needs_manual_review": (
                    row.get("needs_manual_review") or ""
                ).strip().lower(),
                "category": (
                    row.get("category_scope")
                    or row.get("category")
                    or ""
                ).strip().lower(),
                "country_tags_include": (row.get("country_tags_include") or "").strip(),
                "country_tags_exclude": (row.get("country_tags_exclude") or "").strip(),
                "region_codes_include": (row.get("region_codes_include") or "").strip(),
                "region_codes_exclude": (row.get("region_codes_exclude") or "").strip(),
            }
            by_brand.setdefault(_normalize_brand(brand), []).append(record)
    return by_brand


def _category_scope_matches(mapping_category, product_category):
    mapping_values = {
        value.strip().lower()
        for value in str(mapping_category or "").split("|")
        if value.strip()
    }
    if not mapping_values:
        return True
    if mapping_values & {"food_beverage", "food_beverage_review"}:
        return True
    return str(product_category or "").strip().lower() in mapping_values


def resolve_company_owner_for_load(
    brand,
    category,
    countries,
    region_codes,
    mapping_index,
):
    brand_norm = _normalize_brand(brand)
    if not brand_norm:
        return COMPANY_OTHER_LABEL

    rows = [
        r for r in mapping_index.get(brand_norm, [])
        if _category_scope_matches(r.get("category", ""), category)
    ]
    if not rows:
        return COMPANY_OTHER_LABEL

    scoped = [
        r for r in rows
        if r["status"] in {"market_scoped", "licensed_or_partnered"}
        and r.get("needs_manual_review") != "yes"
        and (
            r.get("region_codes_include")
            or r.get("country_tags_include")
            or r.get("region_codes_exclude")
            or r.get("country_tags_exclude")
        )
    ]
    manual = [
        r for r in rows
        if r["status"] == "manual_review"
        or r.get("needs_manual_review") == "yes"
        or r["parent_company"].lower() == COMPANY_MANUAL_REVIEW_LABEL.lower()
    ]
    direct = [
        r for r in rows
        if r["status"] in {
            "direct",
            "recently_demerged",
            "recently_sold_or_spun_off",
            "licensed_or_partnered",
        }
        and r.get("needs_manual_review") != "yes"
        and r["parent_company"].lower() != COMPANY_MANUAL_REVIEW_LABEL.lower()
    ]

    if scoped:
        matches = [
            r for r in scoped
            if _row_scope_matches(r, countries, region_codes)
        ]
        companies = sorted({r["parent_company"] for r in matches})
        if len(companies) == 1:
            return companies[0]
        return COMPANY_MANUAL_REVIEW_LABEL if manual or scoped else COMPANY_OTHER_LABEL

    direct_companies = sorted({r["parent_company"] for r in direct})
    if len(direct_companies) == 1:
        return direct_companies[0]
    if len(direct_companies) > 1 or manual:
        return COMPANY_MANUAL_REVIEW_LABEL
    return COMPANY_OTHER_LABEL


def is_coca_cola_simply_beverage_product(brand_key, category, product_name):
    """Return True only for supported Coca-Cola Simply beverage portfolio rows."""
    if brand_key != "simply" or str(category or "") != "beverages":
        return False
    import re

    name = str(product_name or "")
    return bool(
        re.search(
            r"\bsimply\s+(orange|lemonade|limeade|apple|cranberry|fruit\s+punch|"
            r"grapefruit|peach|tropical|smoothie|juice|juices|beverage|beverages)\b",
            name,
            flags=re.IGNORECASE,
        )
    )


def resolve_manual_review_replacement(
    brand,
    category,
    primary_country,
    region_codes,
    product_name="",
):
    """Return visible launch owner plus backend status/source for Manual Review rows."""
    brand_key = _normalize_review_key(brand)
    country = str(primary_country or "").strip()
    regions = str(region_codes or "").strip()

    if brand_key == "simply":
        if is_coca_cola_simply_beverage_product(brand_key, category, product_name):
            return (
                "The Coca-Cola Company",
                "resolved_from_coca_cola_simply_beverage_product_evidence",
                "manual_review_company_replacement_rule_simply_beverage",
            )
        return (
            COMPANY_OTHER_LABEL,
            "manual_review_collision_prone_generic_brand",
            "manual_review_company_replacement_rule_simply_collision",
        )

    if "cadbury" in brand_key:
        company = (
            "The Hershey Company"
            if country == "United States"
            else "Mondelēz International"
        )
        return (
            company,
            "market_scoped",
            "manual_review_company_replacement_rule_cadbury",
        )

    if "kellogg" in brand_key:
        company = (
            "Ferrero / WK Kellogg"
            if country in {"United States", "Canada"} or regions == "US_CANADA"
            else "Mars / Kellanova"
        )
        return (
            company,
            "recently_changed_market_scoped",
            "manual_review_company_replacement_rule_kellogg",
        )

    if brand_key == "lipton" or brand_key.startswith("lipton "):
        return (
            "LIPTON Teas and Infusions / Pepsi Lipton channel-scoped",
            "licensed_or_partnered_manual_review",
            "manual_review_company_replacement_rule_lipton",
        )

    return (
        COMPANY_OTHER_LABEL,
        "manual_review",
        "manual_review_company_replacement_fallback_other",
    )


def load_reviewed_product_mapping_overrides():
    """Load exact reviewed barcode-level mapping/category overrides."""
    if not os.path.exists(PRODUCT_MAPPING_OVERRIDE_PATH):
        return {}

    overrides = {}
    with open(PRODUCT_MAPPING_OVERRIDE_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            status = (row.get("status") or "").strip().lower()
            barcode = (row.get("gtin") or row.get("barcode") or "").strip()
            if status != "active" or not barcode:
                continue
            overrides.setdefault(barcode, []).append({
                "region": (row.get("region") or "").strip(),
                "brand": (row.get("reviewed_brand") or "").strip(),
                "company": (row.get("reviewed_company") or "").strip(),
                "category": (row.get("reviewed_category") or "").strip(),
                "source": (row.get("source") or "").strip()
                          or "reviewed_product_mapping_overrides.csv",
            })
    return overrides


def _product_override_for_row(overrides, barcode, region_codes):
    candidates = overrides.get(str(barcode or "").strip()) or []
    if not candidates:
        return None
    row_regions = {
        value.strip()
        for value in str(region_codes or "").split("|")
        if value.strip()
    }
    unscoped = None
    for candidate in candidates:
        region = candidate.get("region", "")
        if not region:
            unscoped = candidate
            continue
        if region in row_regions:
            return candidate
    return unscoped


def apply_reviewed_product_mapping_overrides(df):
    """Apply exact reviewed GTIN decisions without changing raw OFF fields."""
    overrides = load_reviewed_product_mapping_overrides()
    if not overrides or "barcode" not in df.columns:
        return df

    matched = 0
    region_values = df.get("observed_market_region_codes", pd.Series("", index=df.index))
    region_values = region_values.fillna("").astype(str)
    for idx, barcode in df["barcode"].fillna("").astype(str).items():
        override = _product_override_for_row(overrides, barcode, region_values.loc[idx])
        if not override:
            continue
        matched += 1
        brand = override["brand"]
        company = override["company"]
        category = override["category"]
        source = override["source"]

        if brand:
            df.at[idx, "normalized_brand"] = brand
            df.at[idx, "brand_family"] = brand
            df.at[idx, "brand_alias_source"] = source
            df.at[idx, "brand_alias_review_status"] = "reviewed_product_override"
        if company:
            df.at[idx, "resolved_company"] = company
            df.at[idx, "company_ownership_resolution_status"] = (
                "reviewed_product_override"
            )
            df.at[idx, "company_mapping_source"] = source
        if category:
            df.at[idx, "query_category"] = None if category == "OUT_OF_SCOPE" else category

    if matched:
        print(f"  Reviewed product mapping overrides applied: {matched:,} rows")
    return df


def add_resolved_company_column(df):
    """Precompute company ownership once so Streamlit can filter in SQL."""
    mapping_index = load_company_mapping_index()
    display_brand = (
        df.get("normalized_brand", pd.Series(index=df.index, dtype="object"))
        .fillna("")
        .astype(str)
        .str.strip()
    )
    legacy_brand = (
        df.get("primary_brand", pd.Series(index=df.index, dtype="object"))
        .fillna("")
        .astype(str)
        .str.strip()
    )
    brand_values = display_brand.where(display_brand != "", legacy_brand)
    countries = df.get("countries", pd.Series("", index=df.index)).fillna("").astype(str)
    regions = (
        df.get("observed_market_region_codes", pd.Series("", index=df.index))
        .fillna("")
        .astype(str)
    )

    key_df = pd.DataFrame({
        "brand": brand_values,
        "category": df.get("query_category", pd.Series("", index=df.index)),
        "countries": countries,
        "regions": regions,
    }).drop_duplicates()

    resolved = {
        (row.brand, row.category, row.countries, row.regions): resolve_company_owner_for_load(
            row.brand,
            row.category,
            row.countries,
            row.regions,
            mapping_index,
        )
        for row in key_df.itertuples(index=False)
    }
    df["resolved_company"] = [
        resolved.get((brand, category, country, region), COMPANY_OTHER_LABEL)
        for brand, category, country, region in zip(
            brand_values,
            df.get("query_category", pd.Series("", index=df.index)),
            countries,
            regions,
        )
    ]
    df["company_ownership_resolution_status"] = "resolved_from_company_brand_mapping"
    df["company_mapping_source"] = "company_brand_mapping.csv"

    manual_mask = df["resolved_company"].eq(COMPANY_MANUAL_REVIEW_LABEL)
    if manual_mask.any():
        replacements = [
            resolve_manual_review_replacement(
                brand,
                category,
                country,
                region,
                product_name,
            )
            for brand, category, country, region, product_name in zip(
                brand_values[manual_mask],
                df.loc[manual_mask, "query_category"],
                df.loc[manual_mask, "primary_country"],
                regions[manual_mask],
                df.loc[manual_mask, "product_name"],
            )
        ]
        df.loc[manual_mask, "resolved_company"] = [item[0] for item in replacements]
        df.loc[manual_mask, "company_ownership_resolution_status"] = [
            item[1] for item in replacements
        ]
        df.loc[manual_mask, "company_mapping_source"] = [
            item[2] for item in replacements
        ]
    return apply_reviewed_product_mapping_overrides(df)


# ── Products table ────────────────────────────────────────────────────────────

PRODUCT_COLS = [
    "barcode", "product_name", "brands", "primary_brand",
    "off_brands_raw", "off_brand_tokens", "legacy_primary_brand",
    "brand_entity_raw", "brand_entity_source", "normalized_brand",
    "brand_family", "brand_alias_source", "brand_alias_review_status",
    "resolved_company", "company_ownership_resolution_status",
    "company_mapping_source",
    "quantity", "packaging",
    "query_category", "off_categories", "countries", "primary_country",
    "observed_market_region_codes",
    "labels", "ingredients_text", "additives_tags",
    "energy_kcal", "fat_100g", "saturated_fat_100g", "carbs_100g",
    "sugars_100g", "fiber_100g", "protein_100g", "salt_100g",
    "nutriscore_grade", "nova_group", "completeness_score",
    "ingredients_lang", "ingredient_analysis_eligible", "created_t",
    "last_modified_t", "image_url",
    "energy_kcal_off_raw", "fat_100g_off_raw", "saturated_fat_100g_off_raw",
    "carbs_100g_off_raw", "sugars_100g_off_raw", "fiber_100g_off_raw",
    "protein_100g_off_raw", "salt_100g_off_raw",
    "nutrition_quality_status", "outlier_type",
    "include_in_product_table", "include_in_aggregates", "include_in_charts",
    "nutrition_quality_reason",
    "energy_kcal_missing", "fat_100g_missing", "saturated_fat_100g_missing",
    "carbs_100g_missing", "sugars_100g_missing", "fiber_100g_missing",
    "protein_100g_missing", "salt_100g_missing",
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
    "image_context", "claim_extraction_status", "detected_claim_phrases",
    "claims_json", "release_run_id", "sampling_region", "sampling_category",
    "sample_component", "primary_stratum_id", "sampling_weight",
    "weight_status",
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
    non_key_analysis_cols = [c for c in analysis_cols_to_load if c != "barcode"]
    if not non_key_analysis_cols:
        print("  Product analysis: skipped; input has no analysis columns")
        return 0, 0

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
    This pre-aggregation supports early pipeline review. Grouped by
    primary_brand (normalized), not the raw brands field, for consistency
    with every other aggregation in the pipeline.

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


def compute_category_region_averages(df, conn, timestamp):
    """Precompute Product Explorer reference averages for fast first load."""
    required = {"query_category", "primary_country", "energy_kcal"}
    missing = required - set(df.columns)
    if missing:
        print(
            "  Category-region averages: skipped; missing columns "
            f"{', '.join(sorted(missing))}"
        )
        return

    work = df.copy()
    brand_source = (
        work["normalized_brand"]
        if "normalized_brand" in work.columns
        else work.get("primary_brand", "")
    )
    fallback_brand = work.get("primary_brand", "")
    brand = brand_source.fillna("").astype(str).str.strip()
    fallback = fallback_brand.fillna("").astype(str).str.strip()
    brand = brand.where(brand != "", fallback)
    brand_ok = brand.notna() & ~brand.str.lower().isin(["unknown", "", "nan"])
    work = work[brand_ok].copy()

    country_region = {
        "France": "FRANCE",
        "United Kingdom": "UK_IE",
        "Great Britain": "UK_IE",
        "Ireland": "UK_IE",
        "England": "UK_IE",
        "Scotland": "UK_IE",
        "United States": "US_CANADA",
        "Canada": "US_CANADA",
    }
    work["region"] = work["primary_country"].map(country_region).fillna("OTHER")

    numeric_cols = [
        "energy_kcal",
        "protein_100g",
        "fiber_100g",
        "saturated_fat_100g",
        "sugars_100g",
        "salt_100g",
    ]
    for col in numeric_cols:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
        else:
            work[col] = pd.NA

    work = work[work["energy_kcal"].notna() & (work["energy_kcal"] > 0)].copy()
    kcal = work["energy_kcal"]
    work["protein_per_kcal"] = work["protein_100g"] / kcal * 100
    work["fiber_per_kcal"] = work["fiber_100g"] / kcal * 100
    work["satfat_per_kcal"] = work["saturated_fat_100g"] / kcal * 100
    work["sugars_per_kcal"] = work["sugars_100g"] / kcal * 100

    metrics = [
        "energy_kcal",
        "protein_per_kcal",
        "fiber_per_kcal",
        "satfat_per_kcal",
        "sugars_per_kcal",
        "sugars_100g",
        "salt_100g",
    ]

    rows = []
    grouped_frames = [
        work.groupby(["query_category", "region"], dropna=False),
        work.assign(region="ALL").groupby(["query_category", "region"], dropna=False),
    ]
    for grouped in grouped_frames:
        for (category, region), group in grouped:
            values = {}
            for metric in metrics:
                valid = group[metric].dropna()
                values[metric] = float(valid.mean()) if len(valid) >= 10 else None
            rows.append((timestamp, str(category), str(region), *[values[m] for m in metrics]))

    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM category_region_averages WHERE snapshot = ?",
        (timestamp,),
    )
    cursor.executemany(
        """
        INSERT OR REPLACE INTO category_region_averages (
            snapshot, query_category, region, energy_kcal, protein_per_kcal,
            fiber_per_kcal, satfat_per_kcal, sugars_per_kcal, sugars_100g,
            salt_100g
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    print(f"  Category-region averages: {len(rows)} rows inserted")


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
    parser.add_argument(
        "--input",
        help="Optional explicit CSV to load. Use this for clean_*.csv product-only refreshes."
    )
    parser.add_argument(
        "--products-only", action="store_true",
        help="Only load/update products. Leaves product_analysis and weekly_brand_summary unchanged."
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\nFood & Beverage Positioning Radar — load.py")
    print(f"Run timestamp: {timestamp}")
    print(f"Source: {args.source}")

    # ── Load analyzed CSV ─────────────────────────────────────────────────────
    input_path = args.input or find_latest_analyzed(SAMPLE_DIR)
    print(f"\n  Input file: {os.path.basename(input_path)}")
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    print(f"  Rows: {len(df)}")
    print("  Resolving company / owner labels...")
    df = add_resolved_company_column(df)

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

        print(f"\n  Computing category-region averages...")
        compute_category_region_averages(df, conn, timestamp)

        if args.products_only:
            a_ins, a_upd = 0, 0
            print("\n  Product analysis: skipped (--products-only)")
            print("  Weekly brand summary: skipped (--products-only)")
        else:
            # ── Load product analysis ─────────────────────────────────────────
            print(f"\n  Loading product_analysis table...")
            a_ins, a_upd = load_product_analysis(df, conn, timestamp)
            print(f"  Product analysis: {a_ins} inserted, {a_upd} updated")

            # ── Compute weekly brand summary ──────────────────────────────────
            print(f"\n  Computing weekly brand summary...")
            compute_weekly_brand_summary(df, conn, timestamp)

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
