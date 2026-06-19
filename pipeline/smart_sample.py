"""
smart_sample.py
----------------
Generates the priority image sample for pack-image claim extraction.

Four-tier sampling strategy (see docs/ADR.md ADR-006):

TIER 1 — Named priority brands (sampled regardless of brand-level
    thresholds)
    Brands selected for their high density of front-of-pack positioning
    claims, identified during early data exploration.
    TIER1_SAMPLE_N products per brand, spread across the available
    composition-marker score distribution.

TIER 2 — NOVA group 4 + Nutri-Score D/E + ingredient-based claim signals
    Products where additional pack-image context is analytically useful:
    an ingredient/name-derived claim signal is present alongside NOVA
    group 4 and Nutri-Score D/E reference grades. This tier prioritizes
    records where composition indicators and positioning signals
    intersect, without treating that intersection as a product verdict.
    TIER2_SAMPLE_N products per brand, brands with >= TIER2_MIN_N products.

TIER 3 — Brands with higher average composition marker scores
    Brands with a higher average composition_marker_score, not already
    captured by Tier 1 or 2.
    TIER3_SAMPLE_N products per brand, avg score >= TIER3_MIN_AVG_SCORE,
    n >= TIER3_MIN_N.

TIER 4 — Named intersection pattern quota sampling
    A dedicated quota for two specific, recurring intersection patterns
    (see docs/COLUMN_DESCRIPTIONS.md), to ensure sufficient pack-image
    coverage for these patterns regardless of brand.

Methodology note:
    This is a purposive priority sample for pack-image claim extraction,
    not a market-representative sample. The goal is to maximize useful
    coverage for OCR/LLM analysis by prioritizing brands, categories, and
    product patterns where front-of-pack positioning signals are likely
    to be analytically informative. Product counts in this sample should
    not be interpreted as market share, retail distribution, or claim
    prevalence.

Output:
    data/sample/smart_sample_<timestamp>.csv
    - barcode, product_name, brands, image_url
    - tier (1/2/3/4), sampling_reason
    - all nutritional + analysis columns for context

Usage:
    python pipeline/smart_sample.py

Prerequisites:
    - database/positioning_radar.db must exist and have been populated
      via pipeline/load.py

Cost guidance:
    The original pack-image extraction run (v3, see docs/ADR.md) covered
    approximately 4,700 products using Azure AI Vision (OCR) and Azure
    OpenAI gpt-4.1-nano (claim extraction), at a total cost of
    approximately 8 CHF — roughly 1.70 CHF per 1,000 products for OCR
    and LLM extraction combined. This is a historical project estimate
    based on the v3 run, not a pricing guarantee — cloud and model
    prices may change; confirm current pricing before larger reruns.
    This script can be rerun to select an additional sample for the
    planned v3.5 model benchmark (~50 CHF budget, see docs/ADR.md).
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH    = os.path.join(ROOT, "database", "positioning_radar.db")
SAMPLE_DIR = os.path.join(ROOT, "data", "sample")

# Estimated cost per 1,000 products, based on the actual v3 run total
# (~8 CHF for ~4,700 products, OCR + LLM combined, gpt-4.1-nano).
# Historical estimate, not a pricing guarantee — see module docstring.
ACTUAL_COST_PER_1000_CHF = 1.70
V35_BUDGET_CHF = 50

# ── Brands to exclude from sampling ──────────────────────────────────────────
# Brands excluded because they are outside the MVP scope or appear due to
# category noise in Open Food Facts.
EXCLUDE_BRANDS = [
    'sapporo ichiban',  # instant noodles appearing in beverage/snack scope
    'sapporo',          # alcoholic beverage brand, outside MVP scope
]

# ── Tier 1: Named priority brands ────────────────────────────────────────────
# These are sampled regardless of brand-level thresholds. Selected during
# early data exploration for their high density of front-of-pack
# positioning claims.
TIER1_BRANDS = [
    # Swiss / European premium snacks and dairy
    "emmi", "chiefs",
    # Natural/fruit positioning
    "innocent", "nakd",
    # Plant milk
    "alpro", "oatly",
    # Breakfast / snack fortification
    "belvita", "gerble", "nature valley",
    # Cereal
    "kellogg's", "special k",
    # Probiotic drinks
    "actimel", "danone",
    # High-protein
    "hipro", "fairlife",
    # Confectionery with protein claims
    "mars", "snickers", "bounty", "twix",
    # Conglomerates
    "nestle",
]

# ── Tier 2: NOVA group 4 + D/E + ingredient-based claim signals ──────────────
TIER2_NOVA       = 4.0
TIER2_NUTRISCORE = ("D", "E")
TIER2_MIN_N      = 5
TIER2_SAMPLE_N   = 8

# ── Tier 3: Brands with higher average composition marker scores ────────────
TIER3_MIN_AVG_SCORE = 20
TIER3_MIN_N         = 10
TIER3_SAMPLE_N      = 5

# ── Per-brand sample size ─────────────────────────────────────────────────────
TIER1_SAMPLE_N = 15


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_products_with_scores(conn):
    """Load all products with composition scores and image URLs."""
    df = pd.read_sql("""
        SELECT
            p.barcode, p.product_name, p.brands, p.primary_brand,
            p.query_category, p.off_categories, p.primary_country,
            p.nova_group, p.nutriscore_grade,
            p.energy_kcal, p.fat_100g, p.saturated_fat_100g,
            p.carbs_100g, p.sugars_100g, p.protein_100g, p.salt_100g,
            p.image_url,
            a.composition_marker_score,
            a.processing_markers_found,
            a.ingredient_based_claim_signals_found,
            a.absence_reduction_claims_found,
            a.has_artificial_sweetener,
            a.sugar_positioning_intersection_flag,
            a.protein_fat_intersection_flag,
            a.fibre_sugar_processing_intersection_flag,
            a.plant_based_nutrition_intersection_flag,
            a.pack_analysis_attempted
        FROM products p
        LEFT JOIN product_analysis a ON p.barcode = a.barcode
        WHERE p.image_url IS NOT NULL
          AND p.image_url NOT LIKE '%/invalid/%'
          AND p.image_url != ''
    """, conn)
    # Note: pack_analysis_attempted is included for forward compatibility
    # with a future --mode flag distinguishing model-benchmark reruns
    # (which may reasonably reuse previously analyzed products) from
    # coverage-expansion runs (which should exclude them). Not yet
    # populated by the pipeline — written later by merge_scores.py — and
    # not filtered on here. See docs/ADR.md v3.5.
    df = df[~df['primary_brand'].isin(EXCLUDE_BRANDS)]
    return df


def sample_diverse(group, n, score_col="composition_marker_score"):
    """
    Select up to n products from a group, spread across the available
    composition-marker score distribution where scores exist. If fewer
    than n scored products are available, remaining slots are filled
    from products without a score, so a brand is still represented at
    its target sample size even when scoring data is incomplete.

    This is a score-diverse per-brand sample, not a statistically
    representative one — see the methodology note in the module
    docstring.
    """
    if len(group) <= n:
        return group

    scored = group.dropna(subset=[score_col])

    if len(scored) >= n:
        scored = scored.sort_values(score_col)
        if n > 1:
            indices = [int(i * (len(scored) - 1) / (n - 1)) for i in range(n)]
        else:
            indices = [0]
        return scored.iloc[indices]

    # Fewer than n scored products available — take all scored products
    # and fill the remaining quota from unscored products, so Tier 1
    # brands in particular are still represented at their target count.
    unscored = group[group[score_col].isna()]
    n_fill = n - len(scored)
    filled = unscored.sample(min(n_fill, len(unscored)), random_state=42)
    return pd.concat([scored.sort_values(score_col), filled])


def sample_tier1(df):
    """
    Tier 1: named brands, sampled regardless of brand-level thresholds,
    score-diverse with unscored fill (see sample_diverse()).
    """
    print(f"\n  TIER 1 — Named priority brands ({len(TIER1_BRANDS)} brands, {TIER1_SAMPLE_N} products each)")
    results = []
    for brand in TIER1_BRANDS:
        group = df[df["primary_brand"] == brand].copy()
        if len(group) == 0:
            print(f"    {brand:<25} not present in current DB snapshot")
            continue
        sampled = sample_diverse(group, TIER1_SAMPLE_N)
        sampled = sampled.copy()
        sampled["tier"] = 1
        sampled["sampling_reason"] = f"tier1_named_brand:{brand}"
        results.append(sampled)
        print(f"    {brand:<25} {len(group):>5} in DB → {len(sampled)} sampled")
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


def sample_tier2(df, already_sampled_barcodes):
    """
    Tier 2: NOVA group 4 + D/E Nutri-Score + ingredient-based claim
    signals, by brand. Selected because this is where pack-image
    analysis is most useful — an ingredient-based claim signal is
    present alongside NOVA group 4 and a D/E Nutri-Score reference
    grade.
    """
    print(f"\n  TIER 2 — NOVA group 4 + Nutri-Score D/E + ingredient-based claim signals")

    mask = (
        (df["nova_group"] == TIER2_NOVA) &
        (df["nutriscore_grade"].str.upper().isin(TIER2_NUTRISCORE)) &
        (df["ingredient_based_claim_signals_found"].notna()) &
        (df["ingredient_based_claim_signals_found"] != "") &
        (~df["barcode"].isin(already_sampled_barcodes))
    )
    pool = df[mask].copy()
    print(f"    Pool: {len(pool):,} products match NOVA group 4 + Nutri-Score D/E + claim signal criteria")

    results = []
    brand_counts = pool["primary_brand"].value_counts()
    eligible_brands = brand_counts[brand_counts >= TIER2_MIN_N].index

    for brand in eligible_brands[:500]:
        group = pool[pool["primary_brand"] == brand]
        sampled = sample_diverse(group, TIER2_SAMPLE_N)
        sampled = sampled.copy()
        sampled["tier"] = 2
        sampled["sampling_reason"] = f"tier2_nova4_de_claim_signals:{brand}"
        results.append(sampled)

    tier2_df = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
    print(f"    {len(eligible_brands)} eligible brands → {len(tier2_df)} products sampled")
    return tier2_df


def sample_tier3(df, already_sampled_barcodes):
    """
    Tier 3: brands with higher average composition marker scores, not
    already captured by Tier 1 or 2.
    """
    print(f"\n  TIER 3 — Brands with higher average composition marker scores")

    pool = df[
        (~df["barcode"].isin(already_sampled_barcodes)) &
        (df["composition_marker_score"].notna())
    ].copy()

    brand_stats = pool.groupby("primary_brand").agg(
        avg_score=("composition_marker_score", "mean"),
        n=("barcode", "count")
    ).reset_index()

    eligible = brand_stats[
        (brand_stats["avg_score"] >= TIER3_MIN_AVG_SCORE) &
        (brand_stats["n"] >= TIER3_MIN_N)
    ].sort_values("avg_score", ascending=False)

    print(f"    {len(eligible)} brands with avg_score >= {TIER3_MIN_AVG_SCORE}, n >= {TIER3_MIN_N}")

    results = []
    for _, row in eligible.head(150).iterrows():
        brand = row["primary_brand"]
        group = pool[pool["primary_brand"] == brand]
        sampled = sample_diverse(group, TIER3_SAMPLE_N)
        sampled = sampled.copy()
        sampled["tier"] = 3
        sampled["sampling_reason"] = f"tier3_higher_composition_marker_score:{brand}"
        results.append(sampled)

    tier3_df = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
    print(f"    {len(tier3_df)} products sampled from {min(len(eligible), 150)} brands")
    return tier3_df


def sample_tier4_intersection_patterns(df, already_sampled_barcodes):
    """
    Tier 4: dedicated quota sampling for two specific, recurring
    intersection patterns, to ensure sufficient pack-image coverage
    for these patterns regardless of brand. See docs/COLUMN_DESCRIPTIONS.md
    for the full definition of each pattern flag.
    """
    print(f"\n  TIER 4 — Intersection pattern quota sampling")
    results = []
    patterns = [
        ("sugar_positioning_intersection_flag",      "Sugar positioning intersection",      100),
        ("fibre_sugar_processing_intersection_flag", "Fibre/processing intersection",       100),
    ]
    for col, label, target in patterns:
        pool = df[
            (df[col] == True) &
            (~df["barcode"].isin(already_sampled_barcodes))
        ].copy()
        sampled = pool.sample(min(target, len(pool)), random_state=42)
        sampled = sampled.copy()
        sampled["tier"] = 4
        sampled["sampling_reason"] = f"tier4_{col}"
        results.append(sampled)
        print(f"    {label}: {len(pool):,} available → {len(sampled)} sampled")
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\nFood & Beverage Positioning Radar - smart_sample.py")
    print(f"Run timestamp: {timestamp}")
    print(f"DB: {DB_PATH}\n")

    if not os.path.exists(DB_PATH):
        print("ERROR: Database not found. Run pipeline/load.py first.")
        return

    conn = get_conn()
    print("  Loading products with image URLs from DB...")
    df = load_products_with_scores(conn)
    conn.close()

    print(f"  Products with valid image URLs: {len(df):,}")

    # Run four tiers
    tier1 = sample_tier1(df)
    tier1_barcodes = set(tier1["barcode"].tolist()) if len(tier1) else set()

    tier2 = sample_tier2(df, tier1_barcodes)
    tier2_barcodes = set(tier2["barcode"].tolist()) if len(tier2) else set()

    tier3 = sample_tier3(df, tier1_barcodes | tier2_barcodes)
    tier3_barcodes = set(tier3["barcode"].tolist()) if len(tier3) else set()

    tier4 = sample_tier4_intersection_patterns(
        df, tier1_barcodes | tier2_barcodes | tier3_barcodes
    )
    tier4_barcodes = set(tier4["barcode"].tolist()) if len(tier4) else set()

    # Combine
    all_tiers = []
    for t in [tier1, tier2, tier3, tier4]:
        if len(t):
            all_tiers.append(t)

    if not all_tiers:
        print("\nERROR: No products sampled. Check DB content.")
        return

    sample = pd.concat(all_tiers, ignore_index=True)
    sample = sample.drop_duplicates(subset=["barcode"])

    # Summary
    print(f"\n  -- Summary --------------------------------------------------")
    print(f"  Total sampled:  {len(sample):,} products")
    print(f"  Tier 1:         {(sample['tier'] == 1).sum():,}")
    print(f"  Tier 2:         {(sample['tier'] == 2).sum():,}")
    print(f"  Tier 3:         {(sample['tier'] == 3).sum():,}")
    print(f"  Tier 4:         {(sample['tier'] == 4).sum():,}")

    print(f"\n  Estimated cost (historical estimate based on the v3 run, "
          f"gpt-4.1-nano — not a pricing guarantee):")
    n = len(sample)
    estimated_cost = n * ACTUAL_COST_PER_1000_CHF / 1000
    print(f"    Estimated total:                {estimated_cost:.2f} CHF")
    print(f"    Remaining v3.5 budget ({V35_BUDGET_CHF} CHF):  "
          f"{V35_BUDGET_CHF - estimated_cost:.2f} CHF")

    # Intersection pattern breakdown
    print(f"\n  Benchmark intersection patterns in sample:")
    for col, label in [
        ("sugar_positioning_intersection_flag",          "Sugar positioning intersection"),
        ("protein_fat_intersection_flag",                "Protein/fat intersection"),
        ("fibre_sugar_processing_intersection_flag",     "Fibre/processing intersection"),
        ("plant_based_nutrition_intersection_flag",      "Plant-based/nutrition intersection"),
    ]:
        if col in sample.columns:
            n_flag = sample[col].sum()
            print(f"    {label}: {int(n_flag):,}")

    # Save
    output_path = os.path.join(SAMPLE_DIR, f"smart_sample_{timestamp}.csv")
    sample.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n  Saved -> smart_sample_{timestamp}.csv")
    print(f"  ({len(sample):,} rows, {len(sample.columns)} columns)")
    print(f"\n  Next step: python pipeline/vision_extract.py")
    print(f"  Input: smart_sample_{timestamp}.csv")
    print(f"  Confirm remaining v3.5 budget before running.\n")


if __name__ == "__main__":
    main()
