"""
Export the vision-analyzed dataset for formulation-vs-claim modeling.

Pulls every product where claim_source = 'vision' (i.e. actually ran
through OCR + LLM extraction — same criterion pages/search.py uses to
decide whether to show a real Positioning value or "Not tested"). This is
NOT the same as everything in product_analysis: ingredient-fallback rows
(claim_source = 'nlp_only') are excluded, since those are estimated from
ingredient text, not observed on pack.

Formulation features included, both raw and per-100kcal-derived (same
energy-validity guard used everywhere else in this app — a per-kcal
metric is never computed from a zero/missing energy denominator):
    energy_kcal, protein_100g, fat_100g, saturated_fat_100g, carbs_100g,
    sugars_100g, fiber_100g, salt_100g, nova_group, nutriscore_grade,
    protein_per_kcal, fiber_per_kcal, satfat_per_kcal, sugars_per_kcal

Claim features: pack_claims_found (the raw pipe-separated field) is
expanded into one binary 0/1 column per claim key, pulled directly from
tag_claims.py's CLAIM_TAXONOMY at runtime — not a hardcoded duplicate
list — so this export never silently drifts out of sync if the taxonomy
changes (e.g. during the upcoming Nielsen-alignment work). claim_category_1/2
(the collapsed single-dominant-claim view) are included too, but the
per-claim binary columns are what a regression/Naive Bayes model should
actually use — claim_category_1/2 keeps only the highest-priority claim
per product and would silently drop information for any product with more
than one claim on pack.

Usage: python pipeline/export_vision_analyzed_dataset.py
Writes: pipeline/vision_analyzed_dataset.csv
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "positioning_radar.db"
OUT_CSV = Path(__file__).resolve().parent / "vision_analyzed_dataset.csv"

# Import the live taxonomy rather than duplicating it — this script lives
# in the same pipeline/ package, so a normal import is appropriate here
# (unlike shared/db.py, which deliberately duplicates small pieces of
# pipeline logic to avoid an app-layer -> pipeline-layer dependency).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tag_claims import CLAIM_TAXONOMY  # noqa: E402

CLAIM_KEYS = list(CLAIM_TAXONOMY.keys())


def main():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    df = pd.read_sql_query("""
        SELECT
            p.barcode, p.product_name, p.primary_brand, p.query_category,
            p.primary_country, p.observed_market_region_codes,
            p.energy_kcal, p.protein_100g, p.fat_100g, p.saturated_fat_100g,
            p.carbs_100g, p.sugars_100g, p.fiber_100g, p.salt_100g,
            p.nova_group, p.nutriscore_grade,
            a.pack_claims_found, a.claim_category_1, a.claim_category_2,
            a.ocr_status, a.llm_status, a.vision_model, a.prompt_version,
            a.pack_analysis_timestamp
        FROM products p
        JOIN product_analysis a ON a.barcode = p.barcode
        WHERE a.claim_source = 'vision'
    """, conn)

    print(f"Vision-analyzed products found: {len(df)}")
    if len(df) == 0:
        print("No rows with claim_source='vision' found — nothing to export.")
        conn.close()
        return

    # Per-100kcal derivation, same guard as shared/db.py's get_market_products.
    for col in ["energy_kcal", "protein_100g", "fat_100g", "saturated_fat_100g",
                "carbs_100g", "sugars_100g", "fiber_100g", "salt_100g"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    valid_energy = df["energy_kcal"].notna() & (df["energy_kcal"] > 0)
    kcal = df["energy_kcal"].where(valid_energy)
    df["protein_per_kcal"] = (df["protein_100g"]       / kcal * 100).where(valid_energy)
    df["fiber_per_kcal"]   = (df["fiber_100g"]         / kcal * 100).where(valid_energy)
    df["satfat_per_kcal"]  = (df["saturated_fat_100g"] / kcal * 100).where(valid_energy)
    df["sugars_per_kcal"]  = (df["sugars_100g"]        / kcal * 100).where(valid_energy)

    # Expand pack_claims_found into one binary column per known claim key.
    claims_lists = df["pack_claims_found"].fillna("").apply(
        lambda s: set(s.split("|")) if s else set()
    )
    for key in CLAIM_KEYS:
        df[f"claim__{key}"] = claims_lists.apply(lambda s: int(key in s))

    # Flag any claim key found in the data that ISN'T in the current
    # taxonomy — would indicate the taxonomy has changed since these
    # products were analyzed, worth knowing before modeling.
    all_found_keys = set().union(*claims_lists) if len(claims_lists) else set()
    unknown_keys = all_found_keys - set(CLAIM_KEYS) - {""}
    if unknown_keys:
        print(f"WARNING: found claim keys in the data not in the current "
              f"CLAIM_TAXONOMY: {sorted(unknown_keys)} — these are NOT "
              f"expanded into columns below.")

    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(df)} rows x {len(df.columns)} columns to {OUT_CSV}")
    print(f"Claim columns added: {len(CLAIM_KEYS)} (prefixed 'claim__')")

    # Quick sanity summary — how common is each claim in this sample,
    # useful before deciding which claims even have enough positive cases
    # to model (a claim present on 3 products out of 5,000 isn't going to
    # produce a stable logistic regression coefficient).
    print("\nClaim prevalence in this exported sample:")
    prevalence = df[[f"claim__{k}" for k in CLAIM_KEYS]].sum().sort_values(ascending=False)
    for key, count in prevalence.items():
        print(f"  {key.replace('claim__', ''):<28} {count:>6} ({count/len(df):.1%})")

    conn.close()


if __name__ == "__main__":
    main()
