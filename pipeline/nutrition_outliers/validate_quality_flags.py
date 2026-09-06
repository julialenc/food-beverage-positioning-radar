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


def flag_rows(rows):
    return build_nutrition_quality_flags(pd.DataFrame(rows))


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
            fat_100g_off_raw=26.0,
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
    sugar_rounding_case = flag_single(
        row_with(carbs_100g_off_raw=5.0, sugars_100g_off_raw=5.5)
    )
    assert sugar_rounding_case["nutrition_quality_status"] != "data_quality_error"
    assert "sugars_greater_than_carbs" not in str(
        sugar_rounding_case["nutrition_quality_reason"]
    )

    assert_status(
        row_with(fat_100g_off_raw=5.0, saturated_fat_100g_off_raw=6.0),
        "data_quality_error",
        "saturated_fat_greater_than_fat",
    )
    saturated_fat_rounding_case = flag_single(
        row_with(fat_100g_off_raw=5.0, saturated_fat_100g_off_raw=5.5)
    )
    assert saturated_fat_rounding_case["nutrition_quality_status"] != "data_quality_error"
    assert "saturated_fat_greater_than_fat" not in str(
        saturated_fat_rounding_case["nutrition_quality_reason"]
    )

    assert_status(
        row_with(energy_kcal_off_raw=100.0, protein_100g_off_raw=29.0),
        "data_quality_error",
        "nutrient_density_exceeds_energy_limit",
    )
    carbohydrate_density_case = flag_single(
        row_with(
            energy_kcal_off_raw=100.0,
            protein_100g_off_raw=0.0,
            carbs_100g_off_raw=29.0,
            fat_100g_off_raw=0.0,
            sugars_100g_off_raw=0.0,
            saturated_fat_100g_off_raw=0.0,
        )
    )
    assert carbohydrate_density_case["nutrition_quality_status"] != "data_quality_error"
    assert "nutrient_density_exceeds_energy_limit" not in str(
        carbohydrate_density_case["nutrition_quality_reason"]
    )

    assert_status(
        row_with(energy_kcal_off_raw=100.0, fat_100g_off_raw=13.0),
        "data_quality_error",
        "nutrient_density_exceeds_energy_limit",
    )
    zero_energy_macro_case = assert_status(
        row_with(
            energy_kcal_off_raw=0.0,
            protein_100g_off_raw=0.0,
            carbs_100g_off_raw=0.0,
            fat_100g_off_raw=0.0,
            sugars_100g_off_raw=0.6,
            saturated_fat_100g_off_raw=0.0,
        ),
        "data_quality_error",
        "zero_energy_with_positive_macros",
    )
    assert bool(zero_energy_macro_case["include_in_product_explorer"]) is False
    assert bool(
        zero_energy_macro_case["include_in_market_overview_calculations"]
    ) is False
    assert bool(zero_energy_macro_case["include_in_market_overview_charts"]) is False

    zero_energy_rounding_case = flag_single(
        row_with(
            energy_kcal_off_raw=0.0,
            protein_100g_off_raw=0.0,
            carbs_100g_off_raw=0.5,
            fat_100g_off_raw=0.0,
            sugars_100g_off_raw=0.5,
            saturated_fat_100g_off_raw=0.0,
        )
    )
    assert zero_energy_rounding_case["nutrition_quality_status"] == "valid"

    minimum_implied_energy_case = assert_status(
        row_with(
            energy_kcal_off_raw=70.0,
            protein_100g_off_raw=8.3,
            carbs_100g_off_raw=None,
            fat_100g_off_raw=None,
            sugars_100g_off_raw=58.3,
            saturated_fat_100g_off_raw=33.3,
        ),
        "data_quality_error",
        "reported_energy_below_minimum_implied_energy",
    )
    assert minimum_implied_energy_case["minimum_implied_energy_kcal_100g"] > (
        minimum_implied_energy_case["energy_kcal_100g"] * 1.25
    )
    assert minimum_implied_energy_case[
        "minimum_implied_energy_diff_kcal_100g"
    ] > 20
    assert bool(minimum_implied_energy_case["include_in_product_explorer"]) is False
    assert bool(minimum_implied_energy_case["warning_flag"]) is False

    salt_ceiling_case = assert_status(
        row_with(salt_100g_off_raw=50.1),
        "data_quality_error",
        "salt_above_50g_per_100",
    )
    assert bool(salt_ceiling_case["include_in_market_overview_calculations"]) is False
    assert bool(salt_ceiling_case["include_in_market_overview_charts"]) is False

    known_mass_case = assert_status(
        row_with(
            protein_100g_off_raw=20.0,
            carbs_100g_off_raw=None,
            fat_100g_off_raw=None,
            sugars_100g_off_raw=40.0,
            saturated_fat_100g_off_raw=36.0,
            salt_100g_off_raw=10.0,
            energy_kcal_off_raw=600.0,
        ),
        "data_quality_error",
        "minimum_known_nutrient_mass_exceeds_105g",
    )
    assert known_mass_case["minimum_known_mass_g_100g"] > 105
    assert bool(known_mass_case["warning_flag"]) is False

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
    assert bool(energy_case["warning_flag"]) is True
    assert "energy_macro_mismatch" in energy_case["warning_types"]
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
    assert bool(high_energy_alcohol_case["warning_flag"]) is False
    assert "energy_macro_mismatch" not in high_energy_alcohol_case["warning_types"]

    within_brand_rows = []
    for i in range(9):
        within_brand_rows.append(row_with(
            barcode=f"within_brand_normal_{i}",
            product_name=f"Normal peer {i}",
            brands="peer brand",
            primary_brand="peer brand",
            energy_kcal_off_raw=100.0 + i,
            protein_100g_off_raw=5.0 + (i % 3) * 0.2,
            carbs_100g_off_raw=10.0 + (i % 4) * 0.4,
            fat_100g_off_raw=4.0 + (i % 3) * 0.3,
        ))
    within_brand_rows.append(
        row_with(
            barcode="within_brand_outlier",
            product_name="High fat peer",
            brands="peer brand",
            primary_brand="peer brand",
            energy_kcal_off_raw=220.0,
            protein_100g_off_raw=5.0,
            carbs_100g_off_raw=10.0,
            fat_100g_off_raw=20.0,
        )
    )
    within_brand_flagged = flag_rows(within_brand_rows)
    outlier_row = within_brand_flagged[
        within_brand_flagged["barcode"].eq("within_brand_outlier")
    ].iloc[0]
    assert bool(outlier_row["include_in_product_explorer"]) is True
    assert bool(outlier_row["warning_flag"]) is True
    assert "within_brand_nutrition_outlier" in outlier_row["warning_types"]

    small_brand_rows = within_brand_rows[:9]
    small_brand_flagged = flag_rows(small_brand_rows)
    assert not small_brand_flagged["warning_types"].astype(str).str.contains(
        "within_brand_nutrition_outlier",
        regex=False,
    ).any()

    source = pd.DataFrame([row_with()])
    before = source.copy(deep=True)
    _ = build_nutrition_quality_flags(source)
    pd.testing.assert_frame_equal(source, before)

    print("All nutrition quality validation checks passed.")


if __name__ == "__main__":
    main()
