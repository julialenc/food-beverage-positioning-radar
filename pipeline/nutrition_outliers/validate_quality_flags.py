"""
validate_quality_flags.py
-------------------------
Lightweight validation checks for nutrition quality governance.

Usage:
    python pipeline/nutrition_outliers/validate_quality_flags.py
"""

from __future__ import annotations

import pandas as pd

from build_quality_flags import build_nutrition_quality_flags


BASE_ROW = {
    "barcode": "base",
    "product_name": "Validation product",
    "brands": "validation brand",
    "primary_brand": "validation brand",
    "observed_market_region_codes": "FRANCE",
    "query_category": "snacks",
    "image_url": "https://example.com/image.jpg",
    "energy_kcal_off_raw": 100.0,
    "protein_100g_off_raw": 5.0,
    "carbs_100g_off_raw": 10.0,
    "fat_100g_off_raw": 4.0,
    "sugars_100g_off_raw": 4.0,
    "saturated_fat_100g_off_raw": 1.0,
    "fiber_100g_off_raw": 2.0,
    "salt_100g_off_raw": 0.2,
}


def row_with(**overrides):
    row = BASE_ROW.copy()
    row.update(overrides)
    return row


def flag_single(row):
    return build_nutrition_quality_flags(pd.DataFrame([row])).iloc[0]


def assert_status(row, status, reason):
    flagged = flag_single(row)
    assert flagged["nutrition_quality_status"] == status, flagged
    assert reason in flagged["nutrition_quality_reason"], flagged
    return flagged


def main():
    assert_status(
        row_with(
            protein_100g_off_raw=40.0,
            carbs_100g_off_raw=40.0,
            fat_100g_off_raw=25.0,
            energy_kcal_off_raw=600.0,
        ),
        "data_quality_error",
        "macro_mass_balance_exceeds_100g",
    )
    assert_status(
        row_with(carbs_100g_off_raw=5.0, sugars_100g_off_raw=6.0),
        "data_quality_error",
        "sugars_greater_than_carbs",
    )
    assert_status(
        row_with(fat_100g_off_raw=5.0, saturated_fat_100g_off_raw=6.0),
        "data_quality_error",
        "saturated_fat_greater_than_fat",
    )
    assert_status(
        row_with(energy_kcal_off_raw=100.0, protein_100g_off_raw=28.0),
        "data_quality_error",
        "nutrient_density_exceeds_energy_limit",
    )
    assert_status(
        row_with(energy_kcal_off_raw=100.0, carbs_100g_off_raw=28.0),
        "data_quality_error",
        "nutrient_density_exceeds_energy_limit",
    )
    assert_status(
        row_with(energy_kcal_off_raw=100.0, fat_100g_off_raw=13.0),
        "data_quality_error",
        "nutrient_density_exceeds_energy_limit",
    )

    energy_case = flag_single(
        row_with(
            energy_kcal_off_raw=500.0,
            protein_100g_off_raw=5.0,
            carbs_100g_off_raw=50.0,
            fat_100g_off_raw=10.0,
        )
    )
    assert energy_case["nutrition_quality_status"] == "energy_macro_inconsistency"
    assert (
        "energy_macro_difference_15pct_or_more"
        in energy_case["nutrition_quality_reason"]
    )
    assert bool(energy_case["include_in_product_explorer"]) is True
    assert bool(energy_case["include_in_market_overview_calculations"]) is False
    assert bool(energy_case["include_in_market_overview_charts"]) is False

    small_gap_case = flag_single(
        row_with(
            energy_kcal_off_raw=100.0,
            protein_100g_off_raw=5.0,
            carbs_100g_off_raw=5.0,
            fat_100g_off_raw=4.5,
        )
    )
    assert small_gap_case["nutrition_quality_status"] == "valid"
    assert (
        "energy_macro_small_absolute_gap_accepted"
        in small_gap_case["nutrition_quality_reason"]
    )
    assert bool(small_gap_case["include_in_market_overview_calculations"]) is True
    assert bool(small_gap_case["include_in_market_overview_charts"]) is True

    low_energy_beverage_case = flag_single(
        row_with(
            query_category="beverages",
            energy_kcal_off_raw=5.0,
            protein_100g_off_raw=0.07,
            carbs_100g_off_raw=0.9,
            fat_100g_off_raw=0.02,
            sugars_100g_off_raw=0.5,
            saturated_fat_100g_off_raw=0.0,
        )
    )
    assert low_energy_beverage_case["nutrition_quality_status"] == "valid"
    assert (
        "low_energy_beverage_macro_gap_accepted"
        in low_energy_beverage_case["nutrition_quality_reason"]
    )
    assert bool(low_energy_beverage_case["include_in_market_overview_calculations"])

    plausible_alcohol_case = flag_single(
        row_with(
            product_name="Beer",
            query_category="beverages",
            energy_kcal_off_raw=80.0,
            protein_100g_off_raw=0.0,
            carbs_100g_off_raw=1.0,
            fat_100g_off_raw=0.0,
            sugars_100g_off_raw=0.5,
            saturated_fat_100g_off_raw=0.0,
        )
    )
    assert plausible_alcohol_case["nutrition_quality_status"] == "valid"
    assert (
        "alcohol_formula_exception_accepted"
        in plausible_alcohol_case["nutrition_quality_reason"]
    )
    assert bool(plausible_alcohol_case["include_in_market_overview_calculations"])

    high_energy_alcohol_case = flag_single(
        row_with(
            product_name="Vodka",
            query_category="beverages",
            energy_kcal_off_raw=120.0,
            protein_100g_off_raw=0.0,
            carbs_100g_off_raw=0.0,
            fat_100g_off_raw=0.0,
            sugars_100g_off_raw=0.0,
            saturated_fat_100g_off_raw=0.0,
        )
    )
    assert (
        high_energy_alcohol_case["nutrition_quality_status"]
        == "energy_macro_inconsistency"
    )
    assert (
        "high_energy_beverage_formula_exception_review"
        in high_energy_alcohol_case["nutrition_quality_reason"]
    )
    assert bool(
        high_energy_alcohol_case["include_in_market_overview_calculations"]
    ) is False

    source = pd.DataFrame([row_with()])
    before = source.copy(deep=True)
    _ = build_nutrition_quality_flags(source)
    pd.testing.assert_frame_equal(source, before)

    print("All nutrition quality validation checks passed.")


if __name__ == "__main__":
    main()
