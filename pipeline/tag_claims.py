"""
tag_claims.py
--------------
Computes claim taxonomy and nutrition benchmark flags.
Writes results back to the product_analysis table and updates the
Power BI export.

TWO-CUT CLAIM TAXONOMY:

Cut 1 — claim_category_1 (broad):
    FUNCTIONAL       — "has something" or "does something"
                       protein, fiber, probiotic, vitamin, immune, energy
    FREE_OF          — "doesn't have something" or "has reduced amounts"
                       no added sugar, reduced sugar, no artificial,
                       no palm oil, gluten-free, dairy-free, vegan,
                       plant-based
    NATURAL_ORGANIC  — organic, natural, clean label, minimal ingredients
    OTHER            — heritage, gender targeting, comparative,
                       sustainability, weight-management positioning
    NO_CLAIM         — no claims detected

claim_category_1/2 reflect the single highest-priority claim category
present on a product (see CATEGORY_1_PRIORITY) — not a complete count
of every claim territory found on pack. A product with both a protein
claim and a no-added-sugar claim is categorized as FUNCTIONAL only. For
claim territory share analysis across ALL claims on a product, use
pack_claims_found directly rather than claim_category_1/2.

Cut 2 — claim_category_2 (sub-group):
    protein | fiber | gut_health | vitamins | immune | energy
    no_added_x | no_artificial | free_from
    organic | natural
    comparative | heritage | sustainability | other
    none

NUTRITION BENCHMARK FLAGS (per 100g solid / per 100ml liquid):
    HIGH sugar:        >22.5g (solid) / >11.25g (liquid)
    HIGH saturated fat:>5g    (solid) / >3g     (liquid)
    HIGH fat:          >17.5g (solid) / >7.5g   (liquid)
    HIGH salt:         >1.25g (solid) / >0.625g (liquid)

    nutrition_benchmark_flags stores neutral codes (e.g.
    sugar_above_reference), not display text — consistent with
    claim_category_1/2. See docs/UI_LABELS.md for the code-to-display
    mapping used by app.py and the Power BI deck.

    Thresholds follow the UK Food Standards Agency's voluntary
    front-of-pack labelling guidance, used here as a single reference
    scheme for cross-product comparison. The EU's mandatory nutrition
    declaration (Regulation 1169/2011) requires these nutrient values to
    be stated on pack but does not itself define high/low thresholds —
    that was deliberately left to individual Member States and food
    businesses. US-market products are assessed against the same
    thresholds for comparability — see docs/METHODOLOGY.md and
    docs/LIMITATIONS.md.

    Liquid detection: products with energy_kcal < 100 kcal/100ml treated
    as liquids, all others as solids. This is an MVP approximation and
    may misclassify some categories — see docs/LIMITATIONS.md.

Claim source:
    claim_source records which evidence layer fed claim_category_1/2 for
    each product: "vision" when pack-image claim extraction was
    available (including when it found zero claims), "ingredient_text_only"
    when it was not. This depends on the merge_scores.py contract for
    pack_claims_found (claims string on success, "" on success-with-no-
    claims, NULL when never attempted or failed) — see
    update_db_positioning_scores() in merge_scores.py and
    docs/COLUMN_DESCRIPTIONS.md.

    When claim_source is "ingredient_text_only", the fallback claim
    evidence combines BOTH ingredient_based_claim_signals_found and
    absence_reduction_claims_found — many FREE_OF claims (no added
    sugar, gluten-free, no palm oil) live only in the latter, so using
    either field alone would undercount that category.

Usage:
    python pipeline/tag_claims.py

Output:
    - Updates product_analysis table in SQLite (columns are already
      declared by load.py — this script only UPDATEs, it does not
      ALTER TABLE)
    - Saves data/sample/powerbi_tagged_<timestamp>.csv — a product-level
      tagged export, not the final aggregated Power BI deck source (see
      db_summary.py for that)
"""

import sqlite3
import pandas as pd
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).parent.parent
DB_PATH    = ROOT / "database" / "positioning_radar.db"
SAMPLE_DIR = ROOT / "data" / "sample"

# ── Nutrition benchmark thresholds ───────────────────────────────────────────
# UK Food Standards Agency front-of-pack guidance — see module docstring
# for the EU 1169/2011 vs UK FSA sourcing distinction.
# Applied per 100g (solids) or per 100ml (liquids).

NUTRITION_BENCHMARK_THRESHOLDS = {
    "solid": {
        "sugar":         {"high": 22.5, "low": 5.0},
        "saturated_fat": {"high": 5.0,  "low": 1.5},
        "fat":           {"high": 17.5, "low": 3.0},
        "salt":          {"high": 1.25, "low": 0.3},
    },
    "liquid": {
        "sugar":         {"high": 11.25, "low": 2.5},
        "saturated_fat": {"high": 3.0,   "low": 0.75},
        "fat":           {"high": 7.5,   "low": 1.5},
        "salt":          {"high": 0.625, "low": 0.3},
    }
}

# Liquid detection threshold (kcal/100ml) — see docs/LIMITATIONS.md
LIQUID_KCAL_THRESHOLD = 100

# ── Claim taxonomy mappings ───────────────────────────────────────────────────
# Maps claim keywords to (category_1, category_2).

CLAIM_TAXONOMY = {
    # FUNCTIONAL claims
    "protein_claim":             ("FUNCTIONAL", "protein"),
    "fibre_claim":                ("FUNCTIONAL", "fiber"),
    "probiotic_claim":            ("FUNCTIONAL", "gut_health"),
    "prebiotic_claim":            ("FUNCTIONAL", "gut_health"),
    "immune_claim":               ("FUNCTIONAL", "immune"),
    "fortification_claim":        ("FUNCTIONAL", "vitamins"),
    "energy_claim":                ("FUNCTIONAL", "energy"),
    "vitalite_concept":            ("FUNCTIONAL", "vitamins"),

    # FREE_OF claims — three distinct sub-types
    "no_added_sugar":             ("FREE_OF", "no_added_x"),
    "reduced_sugar":               ("FREE_OF", "no_added_x"),
    "no_artificial":               ("FREE_OF", "no_artificial"),
    "no_palm_oil":                  ("FREE_OF", "free_from"),
    "gluten_free_claim":           ("FREE_OF", "free_from"),
    "dairy_free_claim":            ("FREE_OF", "free_from"),
    "plant_based_claim":           ("FREE_OF", "free_from"),
    "vegan_claim":                  ("FREE_OF", "free_from"),

    # NATURAL_ORGANIC claims
    "natural_claim":               ("NATURAL_ORGANIC", "natural"),
    "organic_claim":                ("NATURAL_ORGANIC", "organic"),
    "clean_label_claim":            ("NATURAL_ORGANIC", "natural"),
    "minimal_ingredients_claim":    ("NATURAL_ORGANIC", "natural"),

    # OTHER claims
    "comparative_claim":           ("OTHER", "comparative"),
    "reformulation_claim":          ("OTHER", "comparative"),
    "heritage_claim":               ("OTHER", "heritage"),
    "gender_targeting_claim":       ("OTHER", "other"),
    "sustainability_halo":          ("OTHER", "sustainability"),
    "origin_quality_claim":         ("OTHER", "heritage"),
    "artisan_claim":                 ("OTHER", "heritage"),
    "glp1_positioning":              ("OTHER", "other"),
}

# Priority order for cut 1 (if multiple categories present)
CATEGORY_1_PRIORITY = ["FUNCTIONAL", "FREE_OF", "NATURAL_ORGANIC", "OTHER"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_liquid(kcal):
    """Detect if product is liquid based on energy density."""
    try:
        return float(kcal) < LIQUID_KCAL_THRESHOLD
    except (TypeError, ValueError):
        return False


def get_ingredient_fallback_claims(row):
    """
    Combine both ingredient-based evidence sources for the fallback
    claim string used when pack-image claims are unavailable:
    ingredient_based_claim_signals_found (functional/positioning
    signals) and absence_reduction_claims_found (free-from/reduced
    signals, scanned from product name and labels). Many FREE_OF claims
    — no added sugar, gluten-free, no palm oil — live only in the
    latter, so using either field alone undercounts that category.
    """
    return "|".join([
        str(row.get("ingredient_based_claim_signals_found") or ""),
        str(row.get("absence_reduction_claims_found") or "")
    ])


def compute_claim_categories(pack_claims_str, ingredient_claims_str):
    """
    Compute claim_category_1 and claim_category_2 from claim strings.
    Uses pack-image claims when available, falls back to ingredient-
    based claim signals otherwise — caller decides which string to pass
    as ingredient_claims_str based on pack_claims_found availability
    (see claim_source logic in main()).
    """
    claims_str = str(pack_claims_str or "") + "|" + str(ingredient_claims_str or "")
    claims_present = set(claims_str.lower().split("|"))
    claims_present.discard("")
    claims_present.discard("nan")

    categories_found = set()
    subcategories_found = []

    for claim_key, (cat1, cat2) in CLAIM_TAXONOMY.items():
        if claim_key in claims_present:
            categories_found.add(cat1)
            if cat2 not in subcategories_found:
                subcategories_found.append(cat2)

    if not categories_found:
        return "NO_CLAIM", "none"

    # Pick highest priority category_1
    for cat in CATEGORY_1_PRIORITY:
        if cat in categories_found:
            cat1_result = cat
            break
    else:
        cat1_result = list(categories_found)[0]

    # Primary subcategory
    cat2_result = subcategories_found[0] if subcategories_found else "other"

    return cat1_result, cat2_result


def compute_nutrition_benchmark_flags(row):
    """
    Compute nutrition benchmark flags against UK FSA front-of-pack
    reference thresholds. Returns pipe-separated string of neutral
    codes, or empty string. Computed independently of any claim — see
    docs/METHODOLOGY.md. Display labels for these codes live in
    docs/UI_LABELS.md, not here — this keeps stored values stable and
    rename-resistant, consistent with claim_category_1/2.
    """
    liquid = is_liquid(row.get("energy_kcal"))
    thresholds = NUTRITION_BENCHMARK_THRESHOLDS["liquid"] if liquid \
        else NUTRITION_BENCHMARK_THRESHOLDS["solid"]
    flags = []

    nutrient_map = {
        "sugar":         "sugars_100g",
        "saturated_fat": "saturated_fat_100g",
        "fat":           "fat_100g",
        "salt":          "salt_100g",
    }

    nutrient_codes = {
        "sugar":         "sugar_above_reference",
        "saturated_fat": "saturated_fat_above_reference",
        "fat":           "fat_above_reference",
        "salt":          "salt_above_reference",
    }

    for nutrient, col in nutrient_map.items():
        try:
            value = float(row.get(col))
            if value > thresholds[nutrient]["high"]:
                flags.append(nutrient_codes[nutrient])
        except (TypeError, ValueError):
            continue

    return "|".join(flags)


def compute_claim_benchmark_intersections(row):
    """
    Identify specific, named co-occurrences between a detected claim and
    a nutrition or processing benchmark signal for the same product.
    Only fires when both the claim and the benchmark condition are
    present. Describes co-occurrence only — does not indicate that a
    claim is false, illegal, or misleading. See docs/METHODOLOGY.md.
    """
    intersections = []

    pack_claims = row.get("pack_claims_found")
    if pd.notna(pack_claims) and str(pack_claims).strip() not in ("", "nan"):
        claims = str(pack_claims)  # prefer pack-image claims when available
    else:
        claims = get_ingredient_fallback_claims(row)

    liquid = is_liquid(row.get("energy_kcal"))
    thresholds = NUTRITION_BENCHMARK_THRESHOLDS["liquid"] if liquid \
        else NUTRITION_BENCHMARK_THRESHOLDS["solid"]

    # Protein positioning + sugar or saturated fat above reference threshold
    if "protein_claim" in claims:
        try:
            if float(row.get("sugars_100g")) > thresholds["sugar"]["high"]:
                intersections.append("Protein positioning with sugar above reference threshold")
        except (TypeError, ValueError):
            pass
        try:
            if float(row.get("saturated_fat_100g")) > thresholds["saturated_fat"]["high"]:
                intersections.append("Protein positioning with saturated fat above reference threshold")
        except (TypeError, ValueError):
            pass

    # Sugar-reduction positioning + sugar above reference threshold
    if "no_added_sugar" in claims or "reduced_sugar" in claims:
        try:
            if float(row.get("sugars_100g")) > thresholds["sugar"]["high"]:
                intersections.append("Sugar-reduction positioning with sugar above reference threshold")
        except (TypeError, ValueError):
            pass

    # Natural/organic positioning + NOVA group 4
    if any(c in claims for c in ["natural_claim", "organic_claim"]):
        try:
            if float(row.get("nova_group")) == 4.0:
                intersections.append("Natural/organic positioning with NOVA group 4 classification")
        except (TypeError, ValueError):
            pass

    # Plant-based positioning + sugar or fat above reference threshold
    if "vegan_claim" in claims or "plant_based_claim" in claims:
        try:
            if float(row.get("sugars_100g")) > thresholds["sugar"]["high"]:
                intersections.append("Plant-based positioning with sugar above reference threshold")
        except (TypeError, ValueError):
            pass
        try:
            if float(row.get("fat_100g")) > thresholds["fat"]["high"]:
                intersections.append("Plant-based positioning with fat above reference threshold")
        except (TypeError, ValueError):
            pass

    # Fibre positioning + NOVA group 4 + sugar above reference threshold
    if "fibre_claim" in claims:
        try:
            if (float(row.get("nova_group")) == 4.0 and
                    float(row.get("sugars_100g")) > thresholds["sugar"]["high"]):
                intersections.append("Fibre positioning with NOVA group 4 classification and sugar above reference threshold")
        except (TypeError, ValueError):
            pass

    return "|".join(intersections)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\nFood & Beverage Positioning Radar - tag_claims.py")
    print(f"Run timestamp: {timestamp}")
    print(f"Thresholds: UK FSA front-of-pack guidance (see docs/METHODOLOGY.md)\n")

    # Load from DB
    conn = sqlite3.connect(DB_PATH)
    print("  Loading products + ingredient-stage and pack-image analysis from DB...")

    df = pd.read_sql("""
        SELECT
            p.barcode, p.product_name, p.brands, p.primary_brand,
            p.nova_group, p.nutriscore_grade,
            p.energy_kcal, p.fat_100g, p.saturated_fat_100g,
            p.sugars_100g, p.protein_100g, p.salt_100g,
            p.query_category, p.primary_country,
            a.composition_marker_score, a.positioning_composition_gap,
            a.positioning_composition_gap_band,
            a.ingredient_based_claim_signals_found,
            a.absence_reduction_claims_found,
            a.pack_claims_found, a.pack_analysis_attempted,
            a.sugar_positioning_intersection_flag,
            a.protein_fat_intersection_flag,
            a.fibre_sugar_processing_intersection_flag,
            a.plant_based_nutrition_intersection_flag,
            a.processing_markers_found
        FROM products p
        LEFT JOIN product_analysis a ON p.barcode = a.barcode
    """, conn, dtype={"barcode": str})

    print(f"  Loaded {len(df):,} rows")

    # ── Compute claim source and taxonomy ─────────────────────────────────────
    print("\n  Computing claim source and taxonomy (2-cut)...")

    # claim_source: "vision" whenever pack_claims_found is not null —
    # this correctly covers both "claims found" and "pack analysis
    # succeeded with zero claims found", since merge_scores.py only
    # leaves pack_claims_found null when extraction was never attempted
    # or failed. See docs/COLUMN_DESCRIPTIONS.md.
    df["claim_source"] = df["pack_claims_found"].apply(
        lambda x: "vision" if pd.notna(x) else "ingredient_text_only"
    )

    results = df.apply(
        lambda row: compute_claim_categories(
            row.get("pack_claims_found"),
            # Only fall back to ingredient-based signals when pack
            # claims are not available for this product — uses BOTH
            # ingredient evidence sources, see get_ingredient_fallback_claims().
            get_ingredient_fallback_claims(row)
            if row["claim_source"] == "ingredient_text_only" else None
        ), axis=1
    )

    df["claim_category_1"] = [r[0] for r in results]
    df["claim_category_2"] = [r[1] for r in results]

    print(f"\n  Claim source distribution:")
    for src, n in df["claim_source"].value_counts().items():
        pct = n / len(df) * 100
        print(f"    {src:<20} {n:>10,} ({pct:.1f}%)")

    print(f"\n  Cut 1 distribution (all products):")
    for cat, n in df["claim_category_1"].value_counts().items():
        pct = n / len(df) * 100
        print(f"    {cat:<18} {n:>10,} ({pct:.1f}%)")

    print(f"\n  Cut 2 top subcategories:")
    for cat, n in df["claim_category_2"].value_counts().head(10).items():
        pct = n / len(df) * 100
        print(f"    {cat:<20} {n:>10,} ({pct:.1f}%)")

    print(f"\n  Cut 1 distribution — pack-image-analyzed products only:")
    vision_df = df[df["claim_source"] == "vision"]
    print(f"  Pack-image-analyzed products: {len(vision_df):,}")
    for cat, n in vision_df["claim_category_1"].value_counts().items():
        pct = n / len(vision_df) * 100 if len(vision_df) else 0
        print(f"    {cat:<18} {n:>8,} ({pct:.1f}%)")

    # ── Compute nutrition benchmark flags ─────────────────────────────────────
    print("\n  Computing nutrition benchmark flags...")
    df["nutrition_benchmark_flags"] = df.apply(compute_nutrition_benchmark_flags, axis=1)

    flagged = (df["nutrition_benchmark_flags"] != "").sum()
    print(f"  Products with at least one benchmark flag: {flagged:,} ({flagged/len(df)*100:.1f}%)")

    all_flags = []
    for w in df["nutrition_benchmark_flags"].dropna():
        if w:
            all_flags.extend(w.split("|"))
    for flag, count in Counter(all_flags).most_common():
        print(f"    {flag:<35} {count:,}")

    # ── Compute claim-benchmark intersections ─────────────────────────────────
    print("\n  Computing claim-benchmark intersections...")
    df["claim_benchmark_intersections"] = df.apply(compute_claim_benchmark_intersections, axis=1)

    intersected = (df["claim_benchmark_intersections"] != "").sum()
    print(f"  Products with at least one claim-benchmark intersection: {intersected:,}")

    all_intersections = []
    for c in df["claim_benchmark_intersections"].dropna():
        if c:
            all_intersections.extend(c.split("|"))
    for intersection, count in Counter(all_intersections).most_common():
        print(f"    {intersection:<60} {count:,}")

    # ── Write to DB ───────────────────────────────────────────────────────────
    # No ALTER TABLE needed — claim_category_1, claim_category_2,
    # nutrition_benchmark_flags, claim_benchmark_intersections, and
    # claim_source are all already declared in product_analysis by
    # load.py's DDL. This script only updates existing rows.
    print("\n  Writing tags to database...")

    cursor = conn.cursor()
    updated = 0
    batch = []
    for _, row in df.iterrows():
        batch.append((
            row["claim_category_1"],
            row["claim_category_2"],
            row["claim_source"],
            row["nutrition_benchmark_flags"],
            row["claim_benchmark_intersections"],
            timestamp,
            row["barcode"]
        ))
        if len(batch) >= 10000:
            cursor.executemany("""
                UPDATE product_analysis
                SET claim_category_1              = ?,
                    claim_category_2              = ?,
                    claim_source                  = ?,
                    nutrition_benchmark_flags      = ?,
                    claim_benchmark_intersections  = ?,
                    analyzed_at                    = ?
                WHERE barcode = ?
            """, batch)
            updated += len(batch)
            batch = []
            print(f"    Updated {updated:,} rows...")

    if batch:
        cursor.executemany("""
            UPDATE product_analysis
            SET claim_category_1              = ?,
                claim_category_2              = ?,
                claim_source                  = ?,
                nutrition_benchmark_flags      = ?,
                claim_benchmark_intersections  = ?,
                analyzed_at                    = ?
            WHERE barcode = ?
        """, batch)
        updated += len(batch)

    conn.commit()
    print(f"  Total updated: {updated:,} rows")

    # ── Power BI export ───────────────────────────────────────────────────────
    # This is a product-level tagged export, not the final aggregated
    # Power BI deck source — see db_summary.py for that.
    print("\n  Saving product-level tagged export...")

    pbi_cols = [
        "barcode", "product_name", "brands", "primary_brand",
        "query_category", "primary_country",
        "nova_group", "nutriscore_grade",
        "energy_kcal", "fat_100g", "saturated_fat_100g",
        "sugars_100g", "protein_100g", "salt_100g",
        "composition_marker_score", "positioning_composition_gap",
        "positioning_composition_gap_band",
        "claim_source", "claim_category_1", "claim_category_2",
        "nutrition_benchmark_flags", "claim_benchmark_intersections",
        "pack_claims_found", "ingredient_based_claim_signals_found",
        "absence_reduction_claims_found",
        "sugar_positioning_intersection_flag", "protein_fat_intersection_flag",
        "fibre_sugar_processing_intersection_flag",
        "plant_based_nutrition_intersection_flag",
        "processing_markers_found",
    ]

    pbi_df = df[[c for c in pbi_cols if c in df.columns]].copy()
    output_path = SAMPLE_DIR / f"powerbi_tagged_{timestamp}.csv"
    pbi_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  Saved -> powerbi_tagged_{timestamp}.csv")
    print(f"  ({len(pbi_df):,} rows, {len(pbi_df.columns)} columns)")

    conn.close()
    print(f"\n  Done. Updated columns in product_analysis:")
    print(f"    claim_source                   — vision / ingredient_text_only")
    print(f"    claim_category_1               — FUNCTIONAL / FREE_OF / NATURAL_ORGANIC / OTHER / NO_CLAIM")
    print(f"    claim_category_2               — protein / fiber / gut_health / vitamins / ...")
    print(f"    nutrition_benchmark_flags      — sugar_above_reference | saturated_fat_above_reference | ...")
    print(f"    claim_benchmark_intersections  — Protein positioning with sugar above reference threshold | ...")
    print(f"\n  Next step: python pipeline/db_summary.py (final reporting aggregation),")
    print(f"  then streamlit run app.py\n")


if __name__ == "__main__":
    main()
