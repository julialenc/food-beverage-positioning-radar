"""
build_scenario_c2_review.py
---------------------------
Creates guarded Scenario C2 review exports without changing current
nutrition-quality flags or app/database behavior.

Scenario C2 re-includes for Market Overview calculations:
1. small_absolute_kcal_gap where abs(kcal gap) <= 20
2. beverage_energy_not_captured_by_macros where energy <= 60 and abs(kcal gap) <= 10
3. plausible alcohol/fermented beverage formula exceptions where energy <= 100

Usage:
    python pipeline/nutrition_outliers/build_scenario_c2_review.py
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
ALCOHOL_FORMULA_EXCEPTION_MAX_KCAL = 100

REINCLUDED_OUTPUT = os.path.join(
    AUDIT_DIR, "scenario_c2_reincluded_for_review.csv"
)
STILL_EXCLUDED_OUTPUT = os.path.join(
    AUDIT_DIR, "scenario_c2_still_excluded_for_review.csv"
)
SUMMARY_OUTPUT = os.path.join(AUDIT_DIR, "scenario_c2_summary.csv")

ALCOHOL_PATTERN = (
    r"\b(?:wine|vin|champagne|brut|beer|bi[eè]re|lager|cider|cidre|sake|"
    r"liqueur|alcohol|alcool|cocktail|spritz|aperitif|apéritif|vodka|gin|"
    r"rum|rhum|whisky|whiskey|tequila|prosecco|merlot|chardonnay|pinot|"
    r"cabernet|ros[eé])\b"
)


def add_scenario_c2_fields(review: pd.DataFrame) -> pd.DataFrame:
    out = review.copy()
    bucket = out["review_priority_bucket"].fillna("")
    category = out["category"].fillna("").str.lower()
    energy = pd.to_numeric(out["energy_kcal_100g"], errors="coerce")
    abs_gap = pd.to_numeric(out["energy_kcal_macro_diff_abs"], errors="coerce").abs()
    name_text = out["product_name"].fillna("").str.lower()
    is_alcohol_like = name_text.str.contains(ALCOHOL_PATTERN, regex=True, na=False)

    energy_macro_candidate = review["nutrition_quality_status"].eq(
        "energy_macro_inconsistency"
    )
    c2_small_gap = energy_macro_candidate & abs_gap.le(20)
    c2_safe_beverage = (
        energy_macro_candidate
        & category.eq("beverages")
        & energy.le(60)
        & abs_gap.le(10)
    )
    c2_plausible_alcohol = (
        category.eq("beverages")
        & is_alcohol_like
        & energy.gt(0)
        & energy.le(ALCOHOL_FORMULA_EXCEPTION_MAX_KCAL)
        & energy_macro_candidate
    )

    out["scenario_c2_reinclude"] = (
        c2_small_gap | c2_safe_beverage | c2_plausible_alcohol
    )
    out["scenario_c2_rule"] = ""
    out.loc[c2_small_gap, "scenario_c2_rule"] = "small_absolute_kcal_gap_le20"
    out.loc[c2_safe_beverage, "scenario_c2_rule"] = (
        "beverage_energy_le60_abs_gap_le10"
    )
    out.loc[c2_plausible_alcohol, "scenario_c2_rule"] = (
        out.loc[c2_plausible_alcohol, "scenario_c2_rule"]
        .replace("", "plausible_alcohol_formula_exception_energy_le100")
        .where(
            out.loc[c2_plausible_alcohol, "scenario_c2_rule"].eq(""),
            out.loc[c2_plausible_alcohol, "scenario_c2_rule"]
            + ";plausible_alcohol_formula_exception_energy_le100",
        )
    )

    out["scenario_c2_proposed_treatment"] = (
        "remain_excluded_from_market_overview_calculations_and_charts"
    )
    out.loc[out["scenario_c2_reinclude"], "scenario_c2_proposed_treatment"] = (
        "include_in_market_overview_calculations_and_charts"
    )
    out["scenario_c2_review_status"] = "pending_julia_review"
    out["scenario_c2_rationale"] = (
        "Not covered by guarded Scenario C2 re-inclusion rules; remains excluded "
        "by default pending review."
    )
    out.loc[c2_small_gap, "scenario_c2_rationale"] = (
        "Absolute kcal gap is <=20, so the percentage difference is not treated "
        "as material enough for Market Overview exclusion."
    )
    out.loc[c2_safe_beverage, "scenario_c2_rationale"] = (
        "Low/normal-energy beverage with energy <=60 kcal/100g and absolute "
        "kcal gap <=10; percentage-only macro consistency is too sensitive here."
    )
    out.loc[c2_plausible_alcohol, "scenario_c2_rationale"] = (
        "Alcohol/fermented beverage name pattern with plausible energy <=100 "
        "kcal/100g; macro formula does not capture alcohol energy."
    )
    return out


def build_summary(review: pd.DataFrame, total_records: int) -> pd.DataFrame:
    current_excluded = len(review)
    scenario_c = int(
        review["review_priority_bucket"]
        .isin(["small_absolute_kcal_gap", "beverage_energy_not_captured_by_macros"])
        .sum()
    )
    scenario_c2 = int(review["scenario_c2_reinclude"].sum())

    rows = [
        {
            "scenario": "Scenario A",
            "definition": "current rules",
            "records_reincluded_vs_current": 0,
            "excluded_records": current_excluded,
        },
        {
            "scenario": "Scenario C",
            "definition": (
                "re-include all small_absolute_kcal_gap + "
                "beverage_energy_not_captured_by_macros"
            ),
            "records_reincluded_vs_current": scenario_c,
            "excluded_records": current_excluded - scenario_c,
        },
        {
            "scenario": "Scenario C2",
            "definition": "guarded kcal-gap and beverage formula exceptions",
            "records_reincluded_vs_current": scenario_c2,
            "excluded_records": current_excluded - scenario_c2,
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
    review = add_scenario_c2_fields(review)
    reincluded = review[review["scenario_c2_reinclude"]].copy()
    still_excluded = review[~review["scenario_c2_reinclude"]].copy()
    summary = build_summary(review, total_records=total_records)

    reincluded.to_csv(REINCLUDED_OUTPUT, index=False, encoding="utf-8-sig")
    still_excluded.to_csv(STILL_EXCLUDED_OUTPUT, index=False, encoding="utf-8-sig")
    summary.to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8-sig")

    print("\nScenario C2 review package")
    print(f"Re-included candidate records: {len(reincluded):,}")
    print(f"Still-excluded records: {len(still_excluded):,}")
    print("\nScenario summary:")
    print(summary.to_string(index=False))
    print("\nC2 re-included by rule:")
    print(reincluded["scenario_c2_rule"].value_counts().to_string())
    print(f"\nRe-included review file: {REINCLUDED_OUTPUT}")
    print(f"Still-excluded review file: {STILL_EXCLUDED_OUTPUT}")
    print(f"Scenario summary file: {SUMMARY_OUTPUT}")


if __name__ == "__main__":
    main()
