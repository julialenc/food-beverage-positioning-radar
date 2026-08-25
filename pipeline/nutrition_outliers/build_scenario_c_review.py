"""
build_scenario_c_review.py
--------------------------
Creates Scenario C review exports without changing current nutrition-quality
flags or app/database behavior.

Scenario C re-includes for Market Overview calculations:
1. small_absolute_kcal_gap
2. beverage_energy_not_captured_by_macros

Usage:
    python pipeline/nutrition_outliers/build_scenario_c_review.py
"""

from __future__ import annotations

import os

import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUDIT_DIR = os.path.join(ROOT, "data", "nutrition_outlier_review", "audits")
REVIEW_PATH = os.path.join(
    AUDIT_DIR, "market_overview_exclusion_reduction_review.csv"
)
FLAGS_PATH = os.path.join(AUDIT_DIR, "nutrition_quality_flags.csv")

SCENARIO_C_REINCLUDE_BUCKETS = {
    "small_absolute_kcal_gap",
    "beverage_energy_not_captured_by_macros",
}

REINCLUDED_OUTPUT = os.path.join(
    AUDIT_DIR, "scenario_c_reincluded_for_review.csv"
)
STILL_EXCLUDED_OUTPUT = os.path.join(
    AUDIT_DIR, "scenario_c_still_excluded_for_review.csv"
)
SUMMARY_OUTPUT = os.path.join(AUDIT_DIR, "scenario_c_summary.csv")


def build_scenario_c(review: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenario_c_reincluded = review[
        review["review_priority_bucket"].isin(SCENARIO_C_REINCLUDE_BUCKETS)
    ].copy()
    scenario_c_still_excluded = review[
        ~review["review_priority_bucket"].isin(SCENARIO_C_REINCLUDE_BUCKETS)
    ].copy()

    scenario_c_reincluded["scenario_c_proposed_treatment"] = (
        "include_in_market_overview_calculations_and_charts"
    )
    scenario_c_reincluded["scenario_c_review_status"] = "pending_julia_review"
    scenario_c_reincluded["scenario_c_rationale"] = scenario_c_reincluded[
        "review_priority_bucket"
    ].map(
        {
            "small_absolute_kcal_gap": (
                "The percentage difference exceeds 15%, but the absolute kcal "
                "gap is small enough to be analytically non-material."
            ),
            "beverage_energy_not_captured_by_macros": (
                "Beverage energy can be affected by alcohol, fermentation, "
                "acids, sweeteners, or low-kcal rounding; the simple macro "
                "formula is not reliable enough as a standalone exclusion rule."
            ),
        }
    )

    scenario_c_still_excluded["scenario_c_proposed_treatment"] = (
        "remain_excluded_from_market_overview_calculations_and_charts"
    )
    scenario_c_still_excluded["scenario_c_review_status"] = (
        "pending_julia_review"
    )
    scenario_c_still_excluded["scenario_c_rationale"] = (
        "Not covered by Scenario C re-inclusion buckets; hard errors and "
        "material non-beverage energy-macro gaps remain excluded by default."
    )

    return scenario_c_reincluded, scenario_c_still_excluded


def build_summary(review: pd.DataFrame, total_records: int) -> pd.DataFrame:
    current_excluded = len(review)
    small_gap = int(review["review_priority_bucket"].eq("small_absolute_kcal_gap").sum())
    beverage_exception = int(
        review["review_priority_bucket"].eq(
            "beverage_energy_not_captured_by_macros"
        ).sum()
    )

    rows = [
        {
            "scenario": "Scenario A",
            "definition": "current rules",
            "records_reincluded_vs_current": 0,
            "excluded_records": current_excluded,
        },
        {
            "scenario": "Scenario B",
            "definition": "re-include small_absolute_kcal_gap",
            "records_reincluded_vs_current": small_gap,
            "excluded_records": current_excluded - small_gap,
        },
        {
            "scenario": "Scenario C",
            "definition": (
                "re-include small_absolute_kcal_gap + "
                "beverage_energy_not_captured_by_macros"
            ),
            "records_reincluded_vs_current": small_gap + beverage_exception,
            "excluded_records": current_excluded - small_gap - beverage_exception,
        },
    ]
    summary = pd.DataFrame(rows)
    summary["total_records"] = total_records
    summary["excluded_pct"] = (
        summary["excluded_records"] / summary["total_records"] * 100
    ).round(2)
    summary["included_for_market_overview_calculations"] = (
        summary["total_records"] - summary["excluded_records"]
    )
    summary["included_pct"] = (
        summary["included_for_market_overview_calculations"]
        / summary["total_records"]
        * 100
    ).round(2)

    return summary[
        [
            "scenario",
            "definition",
            "total_records",
            "records_reincluded_vs_current",
            "excluded_records",
            "excluded_pct",
            "included_for_market_overview_calculations",
            "included_pct",
        ]
    ]


def main() -> None:
    if not os.path.exists(REVIEW_PATH):
        raise FileNotFoundError(
            f"{REVIEW_PATH} not found. Run build_exclusion_reduction_review.py first."
        )
    if not os.path.exists(FLAGS_PATH):
        raise FileNotFoundError(
            f"{FLAGS_PATH} not found. Run build_quality_flags.py first."
        )

    review = pd.read_csv(REVIEW_PATH, encoding="utf-8-sig", low_memory=False)
    total_records = len(
        pd.read_csv(
            FLAGS_PATH,
            encoding="utf-8-sig",
            usecols=["barcode"],
            low_memory=False,
        )
    )
    reincluded, still_excluded = build_scenario_c(review)
    summary = build_summary(review, total_records=total_records)

    reincluded.to_csv(REINCLUDED_OUTPUT, index=False, encoding="utf-8-sig")
    still_excluded.to_csv(STILL_EXCLUDED_OUTPUT, index=False, encoding="utf-8-sig")
    summary.to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8-sig")

    print("\nScenario C review package")
    print(f"Re-included candidate records: {len(reincluded):,}")
    print(f"Still-excluded records: {len(still_excluded):,}")
    print("\nScenario summary:")
    print(summary.to_string(index=False))
    print(f"\nRe-included review file: {REINCLUDED_OUTPUT}")
    print(f"Still-excluded review file: {STILL_EXCLUDED_OUTPUT}")
    print(f"Scenario summary file: {SUMMARY_OUTPUT}")


if __name__ == "__main__":
    main()
