"""
build_exclusion_reduction_review.py
-----------------------------------
Creates a prioritized review list of records currently excluded from Market
Overview calculations, so rules can be adjusted toward the 2-3% exclusion
range without silently changing governance decisions.

Usage:
    python pipeline/nutrition_outliers/build_exclusion_reduction_review.py
"""

from __future__ import annotations

import os

import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUDIT_DIR = os.path.join(ROOT, "data", "nutrition_outlier_review", "audits")
FLAGS_PATH = os.path.join(AUDIT_DIR, "nutrition_quality_flags.csv")
REVIEW_PATH = os.path.join(
    AUDIT_DIR, "market_overview_exclusion_reduction_review.csv"
)
SUMMARY_PATH = os.path.join(
    AUDIT_DIR, "market_overview_exclusion_reduction_review_summary.csv"
)

REVIEW_COLUMNS = [
    "review_rank",
    "review_priority_bucket",
    "review_priority_reason",
    "review_suggestion",
    "reviewer_decision",
    "reviewer_note",
    "barcode",
    "product_name",
    "brand",
    "company",
    "region",
    "category",
    "image_url",
    "nutrition_quality_status",
    "nutrition_quality_reason",
    "energy_kcal_100g",
    "energy_kcal_macro_calculated_100g",
    "energy_kcal_macro_diff_abs",
    "energy_kcal_macro_diff_pct",
    "energy_kcal_macro_diff_pct_abs",
    "protein_g_100g",
    "carbs_g_100g",
    "fat_g_100g",
    "sugars_g_100g",
    "saturated_fat_g_100g",
    "fiber_g_100g",
    "salt_g_100g",
    "protein_g_per_100kcal",
    "carbs_g_per_100kcal",
    "fat_g_per_100kcal",
    "include_in_product_explorer",
    "include_in_market_overview_calculations",
    "include_in_market_overview_charts",
]


def classify_review_bucket(row: pd.Series) -> tuple[int, str, str, str]:
    status = str(row.get("nutrition_quality_status", ""))
    category = str(row.get("category", "")).lower()
    energy = row.get("energy_kcal_100g")
    calculated = row.get("energy_kcal_macro_calculated_100g")
    diff_abs_signed = row.get("energy_kcal_macro_diff_abs")
    diff_pct_abs = row.get("energy_kcal_macro_diff_pct_abs")
    fiber = row.get("fiber_g_100g")

    if status == "data_quality_error":
        return (
            90,
            "hard_error_keep_excluded",
            "Hard data-quality error; review only if the rule itself is being reconsidered.",
            "keep_excluded_by_default",
        )

    if status != "energy_macro_inconsistency":
        return (
            80,
            "other_excluded_status",
            "Excluded by a non-energy status; review after hard errors and energy-macro cases.",
            "manual_review",
        )

    if pd.notna(energy) and pd.notna(calculated):
        if category == "beverages" and energy > 0 and calculated <= 10:
            return (
                10,
                "beverage_energy_not_captured_by_macros",
                "Beverage has reported energy but near-zero macro energy; alcohol, acids, or labeling conventions may explain the gap.",
                "candidate_for_rule_review",
            )

        if pd.notna(diff_abs_signed) and abs(diff_abs_signed) <= 75:
            return (
                20,
                "small_absolute_kcal_gap",
                "Energy-macro percent difference is >=15%, but the absolute kcal gap is <=75 kcal.",
                "candidate_for_possible_reinclusion",
            )

        if (
            pd.notna(fiber)
            and fiber >= 5
            and pd.notna(diff_abs_signed)
            and diff_abs_signed < 0
        ):
            return (
                30,
                "high_fiber_possible_formula_explanation",
                "Macro formula may overstate energy when fiber is included in carbohydrate or source fields differ.",
                "candidate_for_rule_review",
            )

        if category == "beverages" and energy < 100:
            return (
                40,
                "low_energy_beverage_formula_gap",
                "Low-energy beverage with material percentage gap; absolute category impact may need separate treatment.",
                "manual_review",
            )

        if pd.notna(diff_pct_abs) and diff_pct_abs < 0.25:
            return (
                50,
                "near_threshold_energy_macro_gap",
                "Energy-macro difference is between 15% and 25%, close to the current threshold.",
                "candidate_for_threshold_review",
            )

    return (
        60,
        "material_energy_macro_gap",
        "Energy-macro inconsistency is material and not covered by an obvious review bucket.",
        "manual_review",
    )


def build_review(df: pd.DataFrame) -> pd.DataFrame:
    excluded = df[
        ~df["include_in_market_overview_calculations"].astype(bool)
    ].copy()
    excluded["energy_kcal_macro_diff_pct_abs"] = excluded[
        "energy_kcal_macro_diff_pct"
    ].abs()

    classified = excluded.apply(classify_review_bucket, axis=1, result_type="expand")
    classified.columns = [
        "review_bucket_order",
        "review_priority_bucket",
        "review_priority_reason",
        "review_suggestion",
    ]
    review = pd.concat([excluded, classified], axis=1)
    review["reviewer_decision"] = ""
    review["reviewer_note"] = ""

    review = review.sort_values(
        [
            "review_bucket_order",
            "region",
            "category",
            "energy_kcal_macro_diff_pct_abs",
            "energy_kcal_macro_diff_abs",
        ],
        ascending=[True, True, True, True, True],
    ).reset_index(drop=True)
    review["review_rank"] = review.index + 1

    for col in REVIEW_COLUMNS:
        if col not in review.columns:
            review[col] = pd.NA
    return review[REVIEW_COLUMNS]


def build_summary(review: pd.DataFrame, total_records: int) -> pd.DataFrame:
    summary = (
        review.groupby(
            [
                "review_priority_bucket",
                "review_suggestion",
                "nutrition_quality_status",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="records")
        .sort_values("records", ascending=False)
    )
    summary["records_pct_of_total_dataset"] = (
        summary["records"] / total_records * 100
    ).round(2)
    summary["records_pct_of_excluded"] = (
        summary["records"] / len(review) * 100
    ).round(2)

    hard_errors = int(
        review["nutrition_quality_status"].eq("data_quality_error").sum()
    )
    max_excluded_for_3pct = int(total_records * 0.03)
    max_energy_macro_exclusions_for_3pct = max(max_excluded_for_3pct - hard_errors, 0)
    current_energy_macro = int(
        review["nutrition_quality_status"].eq("energy_macro_inconsistency").sum()
    )
    summary.attrs["hard_errors"] = hard_errors
    summary.attrs["current_energy_macro"] = current_energy_macro
    summary.attrs["energy_macro_to_reinclude_for_3pct"] = max(
        current_energy_macro - max_energy_macro_exclusions_for_3pct, 0
    )
    return summary


def main() -> None:
    if not os.path.exists(FLAGS_PATH):
        raise FileNotFoundError(
            f"{FLAGS_PATH} not found. Run build_quality_flags.py first."
        )

    df = pd.read_csv(FLAGS_PATH, encoding="utf-8-sig", low_memory=False)
    review = build_review(df)
    summary = build_summary(review, total_records=len(df))

    review.to_csv(REVIEW_PATH, index=False, encoding="utf-8-sig")
    summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")

    excluded = len(review)
    print("\nMarket Overview exclusion-reduction review list")
    print(f"Total records: {len(df):,}")
    print(f"Currently excluded from Market Overview calculations: {excluded:,}")
    print(
        "Hard data-quality errors, kept excluded by default: "
        f"{summary.attrs['hard_errors']:,}"
    )
    print(
        "Energy-macro inconsistencies currently excluded: "
        f"{summary.attrs['current_energy_macro']:,}"
    )
    print(
        "Approx. energy-macro records to reinstate to reach 3% total exclusion: "
        f"{summary.attrs['energy_macro_to_reinclude_for_3pct']:,}"
    )
    print(f"\nReview list: {REVIEW_PATH}")
    print(f"Review summary: {SUMMARY_PATH}")
    print("\nTop review buckets:")
    print(summary.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
