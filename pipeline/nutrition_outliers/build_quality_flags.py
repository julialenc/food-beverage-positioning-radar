"""
build_quality_flags.py
----------------------
Builds nutrition-quality flags and audit exports without overwriting raw
Open Food Facts nutrition values.

This script is the audited nutrition-governance layer. It reads a cleaned
pipeline CSV, derives nutrition quality fields from preserved OFF values, and
writes review/audit outputs. It does not delete products or correct source
nutrition values.

Usage:
    python pipeline/nutrition_outliers/build_quality_flags.py
    python pipeline/nutrition_outliers/build_quality_flags.py --input data/sample/clean_20260822_220423.csv
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime

import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared.beverage_segments import beverage_view_segment

SAMPLE_DIR = os.path.join(ROOT, "data", "sample")
AUDIT_DIR = os.path.join(ROOT, "data", "nutrition_outlier_review", "audits")
COMPANY_MAPPING_PATH = os.path.join(
    ROOT, "data", "reference", "company_brand_mapping.csv"
)

SOURCE_NUTRITION_COLS = {
    "energy_kcal_100g": "energy_kcal",
    "protein_g_100g": "protein_100g",
    "carbs_g_100g": "carbs_100g",
    "fat_g_100g": "fat_100g",
    "sugars_g_100g": "sugars_100g",
    "saturated_fat_g_100g": "saturated_fat_100g",
    "fiber_g_100g": "fiber_100g",
    "salt_g_100g": "salt_100g",
}

NUTRIENT_G_COLS = [
    "protein_g_100g",
    "carbs_g_100g",
    "fat_g_100g",
    "sugars_g_100g",
    "saturated_fat_g_100g",
    "fiber_g_100g",
    "salt_g_100g",
]

DENSITY_LIMITS = {
    "protein_g_per_100kcal": 28.0,
    "fat_g_per_100kcal": 12.5,
}

ZERO_ENERGY_MACRO_TOLERANCE_G_100G = 0.5
RELATIONAL_NUTRIENT_TOLERANCE_G_100G = 0.5
MAX_KNOWN_MASS_G_100G = 105.0
MAX_SALT_G_100G = 50.0
MINIMUM_IMPLIED_ENERGY_RATIO = 1.25
MINIMUM_IMPLIED_ENERGY_ABS_DIFF_KCAL = 20.0
ENERGY_MACRO_DIFF_PCT_THRESHOLD = 0.15
ALCOHOL_FORMULA_EXCEPTION_MAX_KCAL = 100
ENERGY_MACRO_WARNING_TEXT = (
    "Energy-macro mismatch: Reported kcal and macro-derived kcal differ "
    "materially. The product is still useful to inspect, but nutrition "
    "interpretation should be cautious."
)
WITHIN_BRAND_WARNING_TEXT = (
    "Within-brand nutrition outlier: One or more nutrition values differ "
    "sharply from comparable products in the same brand/category/region, "
    "suggesting a possible OFF entry issue or unusual product format."
)
WITHIN_BRAND_MIN_PRODUCTS = 10
WITHIN_BRAND_MIN_METRIC_VALUES = 10
WITHIN_BRAND_LOW_MULTIPLIER = 0.5
WITHIN_BRAND_HIGH_MULTIPLIER = 1.5
WITHIN_BRAND_ROBUST_Z_THRESHOLD = 4.5
WITHIN_BRAND_METRIC_FLOORS = {
    "energy_kcal_100g": 75.0,
    "protein_g_100g": 5.0,
    "carbs_g_100g": 15.0,
    "fat_g_100g": 7.5,
    "sugars_g_100g": 12.0,
    "saturated_fat_g_100g": 5.0,
    "fiber_g_100g": 5.0,
    "salt_g_100g": 0.8,
}
WITHIN_BRAND_BROAD_PORTFOLIO_PATTERNS = [
    r"\bcoca[\s-]?cola\b",
    r"\bpepsi\b",
    r"\bpepsico\b",
]
ALCOHOL_PATTERN = (
    r"\b(?:wine|vin|champagne|brut|beer|bi[eè]re|lager|cider|cidre|sake|"
    r"liqueur|alcohol|alcool|cocktail|spritz|aperitif|apéritif|vodka|gin|"
    r"rum|rhum|whisky|whiskey|tequila|prosecco|merlot|chardonnay|pinot|"
    r"cabernet|ros[eé])\b"
)

AUDIT_COLUMNS = [
    "barcode",
    "product_name",
    "brand",
    "company",
    "region",
    "category",
    "image_url",
    "energy_kcal_100g",
    "protein_g_100g",
    "carbs_g_100g",
    "fat_g_100g",
    "sugars_g_100g",
    "saturated_fat_g_100g",
    "fiber_g_100g",
    "salt_g_100g",
    "energy_kcal_macro_calculated_100g",
    "energy_kcal_macro_diff_abs",
    "energy_kcal_macro_diff_pct",
    "effective_carbs_g_100g",
    "effective_fat_g_100g",
    "minimum_implied_energy_kcal_100g",
    "minimum_implied_energy_diff_kcal_100g",
    "minimum_implied_energy_ratio",
    "minimum_known_mass_g_100g",
    "protein_g_per_100kcal",
    "carbs_g_per_100kcal",
    "fat_g_per_100kcal",
    "nutrition_quality_status",
    "nutrition_quality_reason",
    "energy_macro_exception_type",
    "beverage_view_segment",
    "include_in_product_explorer",
    "include_in_market_overview_calculations",
    "include_in_market_overview_charts",
    "warning_flag",
    "warning_types",
    "warning_summary",
]


def find_latest_clean(sample_dir: str = SAMPLE_DIR) -> str:
    files = [
        f for f in os.listdir(sample_dir)
        if f.startswith("clean_") and f.endswith(".csv")
    ]
    if not files:
        raise FileNotFoundError(
            f"No clean_*.csv found in {sample_dir}. Run pipeline/clean.py first."
        )
    files.sort(reverse=True)
    return os.path.join(sample_dir, files[0])


def normalize_key(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def load_company_map(path: str = COMPANY_MAPPING_PATH) -> dict[str, str]:
    if not os.path.exists(path):
        return {}

    mapping_df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    confirmed = mapping_df[
        mapping_df["ownership_resolution_status"].str.strip().str.lower().isin(
            ["direct", "market_scoped"]
        )
    ].copy()

    brand_to_company: dict[str, str] = {}
    ambiguous: set[str] = set()
    for _, row in confirmed.iterrows():
        brand = normalize_key(row.get("primary_brand_db") or row.get("brand"))
        company = str(row.get("parent_company", "")).strip()
        if not brand or not company:
            continue
        if brand in brand_to_company and brand_to_company[brand] != company:
            ambiguous.add(brand)
            continue
        brand_to_company[brand] = company

    for brand in ambiguous:
        brand_to_company.pop(brand, None)
    return brand_to_company


def raw_nutrition_series(df: pd.DataFrame, clean_col: str) -> pd.Series:
    raw_col = f"{clean_col}_off_raw"
    source_col = raw_col if raw_col in df.columns else clean_col
    if source_col not in df.columns:
        return pd.Series(pd.NA, index=df.index, dtype="Float64")
    return pd.to_numeric(df[source_col], errors="coerce")


def append_reason(df: pd.DataFrame, mask: pd.Series, reason: str) -> None:
    if int(mask.sum()) == 0:
        return

    def add(existing):
        if not isinstance(existing, str) or existing.strip() == "":
            return reason
        parts = [p for p in existing.split(";") if p]
        if reason not in parts:
            parts.append(reason)
        return ";".join(parts)

    df.loc[mask, "nutrition_quality_reason"] = df.loc[
        mask, "nutrition_quality_reason"
    ].apply(add)


def apply_hard_error(df: pd.DataFrame, mask: pd.Series, reason: str) -> None:
    append_reason(df, mask, reason)
    if int(mask.sum()) == 0:
        return
    df.loc[mask, "nutrition_quality_status"] = "data_quality_error"
    df.loc[mask, "include_in_product_explorer"] = False
    df.loc[mask, "include_in_market_overview_calculations"] = False
    df.loc[mask, "include_in_market_overview_charts"] = False


def effective_parent_or_subset(parent: pd.Series, subset: pd.Series) -> pd.Series:
    return parent.where(parent.notna(), subset).fillna(0)


def apply_accepted_exception(
    df: pd.DataFrame,
    mask: pd.Series,
    exception_type: str,
    reason: str,
) -> None:
    append_reason(df, mask, reason)
    if int(mask.sum()) == 0:
        return

    def add_exception(existing):
        if not isinstance(existing, str) or existing.strip() == "":
            return exception_type
        parts = [p for p in existing.split(";") if p]
        if exception_type not in parts:
            parts.append(exception_type)
        return ";".join(parts)

    df.loc[mask, "energy_macro_exception_type"] = df.loc[
        mask, "energy_macro_exception_type"
    ].apply(add_exception)


def append_warning(df: pd.DataFrame, mask: pd.Series, warning_type: str) -> None:
    if int(mask.sum()) == 0:
        return

    def add(existing):
        if not isinstance(existing, str) or existing.strip() == "":
            return warning_type
        parts = [p for p in existing.split("|") if p]
        if warning_type not in parts:
            parts.append(warning_type)
        return "|".join(parts)

    df.loc[mask, "warning_types"] = df.loc[mask, "warning_types"].apply(add)
    df.loc[mask, "warning_flag"] = True


def append_warning_summary(df: pd.DataFrame, mask: pd.Series, summary: str) -> None:
    if int(mask.sum()) == 0:
        return

    def add(existing):
        if not isinstance(existing, str) or existing.strip() == "":
            return summary
        parts = [p for p in existing.split("\n\n") if p]
        if summary not in parts:
            parts.append(summary)
        return "\n\n".join(parts)

    df.loc[mask, "warning_summary"] = df.loc[mask, "warning_summary"].apply(add)


def add_display_fields(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy(deep=True)
    company_map = load_company_map()

    out["brand"] = out.get("primary_brand", out.get("brands", "")).fillna("")
    out["company"] = (
        out["brand"].map(lambda value: company_map.get(normalize_key(value), ""))
        if len(out)
        else ""
    )
    out["region"] = out.get("observed_market_region_codes", "").fillna("")
    out["category"] = out.get("query_category", "").fillna("")
    off_categories = (
        out["off_categories"]
        if "off_categories" in out.columns
        else pd.Series("", index=out.index)
    )
    out["beverage_view_segment"] = [
        beverage_view_segment(category, name, off_cat)
        for category, name, off_cat in zip(
            out["category"],
            out.get("product_name", pd.Series("", index=out.index)),
            off_categories,
        )
    ]
    return out


def known_broad_beverage_portfolio_mask(frame: pd.DataFrame) -> pd.Series:
    brand = frame["_brand_key"].fillna("").astype(str)
    known_broad_brand = pd.Series(False, index=frame.index)
    for pattern in WITHIN_BRAND_BROAD_PORTFOLIO_PATTERNS:
        known_broad_brand = known_broad_brand | brand.str.contains(
            pattern,
            regex=True,
            na=False,
        )
    return frame["category"].astype(str).str.lower().eq("beverages") & known_broad_brand


def within_brand_warning_mask(df: pd.DataFrame) -> pd.Series:
    eligible = df[
        df["include_in_product_explorer"].astype(bool)
        & df["category"].fillna("").astype(str).str.strip().ne("")
        & df["region"].fillna("").astype(str).str.strip().ne("")
        & df["brand"].fillna("").astype(str).str.strip().ne("")
    ].copy()
    if eligible.empty:
        return pd.Series(False, index=df.index)

    eligible["_source_index"] = eligible.index
    eligible["region"] = eligible["region"].fillna("").astype(str).str.split("|")
    eligible = eligible.explode("region")
    eligible["region"] = eligible["region"].fillna("").astype(str).str.strip()
    eligible = eligible[eligible["region"].ne("")]
    eligible["_brand_key"] = eligible["brand"].map(normalize_key)
    eligible = eligible[eligible["_brand_key"].ne("")]

    group_cols = ["region", "category", "_brand_key"]
    eligible["_group_size"] = eligible.groupby(group_cols)["barcode"].transform("size")
    eligible = eligible[
        eligible["_group_size"].ge(WITHIN_BRAND_MIN_PRODUCTS)
        & ~known_broad_beverage_portfolio_mask(eligible)
    ].copy()
    if eligible.empty:
        return pd.Series(False, index=df.index)

    metric_warning = pd.Series(False, index=eligible.index)
    for metric in SOURCE_NUTRITION_COLS:
        value = pd.to_numeric(eligible[metric], errors="coerce")
        grouped = value.groupby(
            [eligible[col] for col in group_cols],
            dropna=False,
        )
        median = grouped.transform("median")
        metric_count = grouped.transform("count")
        absolute_diff = (value - median).abs()
        mad = absolute_diff.groupby(
            [eligible[col] for col in group_cols],
            dropna=False,
        ).transform("median")
        robust_z = absolute_diff / (1.4826 * mad)
        q1 = grouped.transform(lambda s: s.quantile(0.25))
        q3 = grouped.transform(lambda s: s.quantile(0.75))
        iqr = q3 - q1
        statistical_extreme = (
            (mad.gt(0) & robust_z.ge(WITHIN_BRAND_ROBUST_Z_THRESHOLD))
            | (
                mad.le(0)
                & iqr.gt(0)
                & (
                    value.lt(q1 - 3.0 * iqr)
                    | value.gt(q3 + 3.0 * iqr)
                )
            )
        )
        relative_difference = (
            median.le(0)
            | value.le(median * WITHIN_BRAND_LOW_MULTIPLIER)
            | value.ge(median * WITHIN_BRAND_HIGH_MULTIPLIER)
        )
        floor = WITHIN_BRAND_METRIC_FLOORS[metric]
        metric_warning = metric_warning | (
            value.notna()
            & median.notna()
            & metric_count.ge(WITHIN_BRAND_MIN_METRIC_VALUES)
            & statistical_extreme
            & relative_difference
            & absolute_diff.ge(floor)
        )

    warning_indices = set(
        eligible.loc[metric_warning, "_source_index"].astype(int).tolist()
    )
    return df.index.to_series().isin(warning_indices)


def build_nutrition_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with derived nutrition quality fields added."""
    out = add_display_fields(df)

    for derived_col, clean_col in SOURCE_NUTRITION_COLS.items():
        out[derived_col] = raw_nutrition_series(out, clean_col)

    out["nutrition_quality_status"] = "valid"
    out["nutrition_quality_reason"] = ""
    out["energy_macro_exception_type"] = ""
    out["include_in_product_explorer"] = True
    out["include_in_market_overview_calculations"] = True
    out["include_in_market_overview_charts"] = True
    out["warning_flag"] = False
    out["warning_types"] = ""
    out["warning_summary"] = ""

    energy = out["energy_kcal_100g"]
    protein = out["protein_g_100g"]
    carbs = out["carbs_g_100g"]
    fat = out["fat_g_100g"]
    sugars = out["sugars_g_100g"]
    satfat = out["saturated_fat_g_100g"]
    salt = out["salt_g_100g"]

    out["effective_carbs_g_100g"] = effective_parent_or_subset(carbs, sugars)
    out["effective_fat_g_100g"] = effective_parent_or_subset(fat, satfat)
    effective_protein = protein.fillna(0)
    out["minimum_implied_energy_kcal_100g"] = (
        effective_protein * 4
        + out["effective_carbs_g_100g"] * 4
        + out["effective_fat_g_100g"] * 9
    )
    out["minimum_implied_energy_diff_kcal_100g"] = (
        out["minimum_implied_energy_kcal_100g"] - energy
    )
    out["minimum_implied_energy_ratio"] = (
        out["minimum_implied_energy_kcal_100g"] / energy
    ).where(energy.notna() & energy.ne(0))
    out["minimum_known_mass_g_100g"] = (
        effective_protein
        + out["effective_carbs_g_100g"]
        + out["effective_fat_g_100g"]
        + salt.fillna(0)
    )

    valid_energy = energy.notna() & (energy > 0)
    out["protein_g_per_100kcal"] = (protein / energy * 100).where(valid_energy)
    out["carbs_g_per_100kcal"] = (carbs / energy * 100).where(valid_energy)
    out["fat_g_per_100kcal"] = (fat / energy * 100).where(valid_energy)

    macro_ready = energy.notna() & protein.notna() & carbs.notna() & fat.notna()
    out["energy_kcal_macro_calculated_100g"] = (
        fat * 9 + protein * 4 + carbs * 4
    ).where(macro_ready)
    out["energy_kcal_macro_diff_abs"] = (
        energy - out["energy_kcal_macro_calculated_100g"]
    ).where(macro_ready)
    out["energy_kcal_macro_diff_pct"] = (
        out["energy_kcal_macro_diff_abs"] / energy
    ).where(macro_ready & valid_energy)

    apply_hard_error(out, energy < 0, "negative_nutrient_value")
    apply_hard_error(out, energy > 900, "energy_above_900_kcal")
    for col in NUTRIENT_G_COLS:
        apply_hard_error(out, out[col] < 0, "negative_nutrient_value")
        apply_hard_error(out, out[col] > 100, "nutrient_value_above_100g")

    zero_energy_positive_macro = (
        energy.notna()
        & energy.eq(0)
        & (
            protein.gt(ZERO_ENERGY_MACRO_TOLERANCE_G_100G)
            | carbs.gt(ZERO_ENERGY_MACRO_TOLERANCE_G_100G)
            | fat.gt(ZERO_ENERGY_MACRO_TOLERANCE_G_100G)
            | out["sugars_g_100g"].gt(ZERO_ENERGY_MACRO_TOLERANCE_G_100G)
        )
    )
    apply_hard_error(
        out,
        zero_energy_positive_macro,
        "zero_energy_with_positive_macros",
    )

    minimum_implied_energy_mask = (
        energy.notna()
        & energy.ge(0)
        & (protein.notna() | carbs.notna() | fat.notna() | sugars.notna() | satfat.notna())
        & out["minimum_implied_energy_kcal_100g"].gt(
            energy * MINIMUM_IMPLIED_ENERGY_RATIO
        )
        & out["minimum_implied_energy_diff_kcal_100g"].gt(
            MINIMUM_IMPLIED_ENERGY_ABS_DIFF_KCAL
        )
    )
    apply_hard_error(
        out,
        minimum_implied_energy_mask,
        "reported_energy_below_minimum_implied_energy",
    )

    macro_mass = protein + carbs + fat
    apply_hard_error(
        out,
        protein.notna() & carbs.notna() & fat.notna() & (macro_mass > 105),
        "macro_mass_balance_exceeds_100g",
    )
    apply_hard_error(
        out,
        out["minimum_known_mass_g_100g"].gt(MAX_KNOWN_MASS_G_100G),
        "minimum_known_nutrient_mass_exceeds_105g",
    )
    apply_hard_error(
        out,
        salt.notna() & salt.gt(MAX_SALT_G_100G),
        "salt_above_50g_per_100",
    )
    apply_hard_error(
        out,
        out["sugars_g_100g"].notna()
        & carbs.notna()
        & (
            out["sugars_g_100g"]
            > carbs + RELATIONAL_NUTRIENT_TOLERANCE_G_100G
        ),
        "sugars_greater_than_carbs",
    )
    apply_hard_error(
        out,
        out["saturated_fat_g_100g"].notna()
        & fat.notna()
        & (
            out["saturated_fat_g_100g"]
            > fat + RELATIONAL_NUTRIENT_TOLERANCE_G_100G
        ),
        "saturated_fat_greater_than_fat",
    )

    density_mask = pd.Series(False, index=out.index)
    for col, limit in DENSITY_LIMITS.items():
        density_mask = density_mask | (out[col].notna() & (out[col] > limit))
    apply_hard_error(
        out,
        density_mask,
        "nutrient_density_exceeds_energy_limit",
    )

    energy_macro_mask = (
        out["nutrition_quality_status"].eq("valid")
        & macro_ready
        & valid_energy
        & out["energy_kcal_macro_diff_pct"].abs().ge(
            ENERGY_MACRO_DIFF_PCT_THRESHOLD
        )
    )
    append_reason(
        out,
        energy_macro_mask,
        "energy_macro_difference_15pct_or_more",
    )

    abs_energy_gap = out["energy_kcal_macro_diff_abs"].abs()
    category = out["category"].fillna("").astype(str).str.lower()
    product_name = out["product_name"].fillna("").astype(str).str.lower()
    is_beverage = category.eq("beverages")
    is_alcohol_like = product_name.str.contains(
        ALCOHOL_PATTERN,
        regex=True,
        na=False,
    )

    small_absolute_gap = energy_macro_mask & abs_energy_gap.le(20)
    low_energy_beverage_gap = (
        energy_macro_mask
        & is_beverage
        & energy.le(60)
        & abs_energy_gap.le(10)
    )
    alcohol_formula_exception = (
        energy_macro_mask
        & is_beverage
        & is_alcohol_like
        & energy.gt(0)
        & energy.le(ALCOHOL_FORMULA_EXCEPTION_MAX_KCAL)
    )
    high_energy_beverage_exception_review = (
        energy_macro_mask
        & is_beverage
        & is_alcohol_like
        & energy.gt(ALCOHOL_FORMULA_EXCEPTION_MAX_KCAL)
    )
    accepted_exception = (
        (
            small_absolute_gap
            | low_energy_beverage_gap
            | alcohol_formula_exception
        )
        & ~high_energy_beverage_exception_review
    )

    apply_accepted_exception(
        out,
        small_absolute_gap,
        "small_absolute_kcal_gap_le20",
        "energy_macro_small_absolute_gap_accepted",
    )
    apply_accepted_exception(
        out,
        low_energy_beverage_gap,
        "beverage_energy_le60_abs_gap_le10",
        "low_energy_beverage_macro_gap_accepted",
    )
    apply_accepted_exception(
        out,
        alcohol_formula_exception,
        "alcohol_formula_exception_energy_le100",
        "alcohol_formula_exception_accepted",
    )
    out.loc[
        high_energy_beverage_exception_review, "energy_macro_exception_type"
    ] = ""

    excluded_energy_macro = energy_macro_mask & ~accepted_exception
    out.loc[excluded_energy_macro, "nutrition_quality_status"] = (
        "energy_macro_inconsistency"
    )
    out.loc[
        excluded_energy_macro, "include_in_market_overview_calculations"
    ] = False
    out.loc[excluded_energy_macro, "include_in_market_overview_charts"] = False
    append_reason(
        out,
        high_energy_beverage_exception_review,
        "high_energy_beverage_formula_exception_review",
    )
    product_explorer_energy_macro_warning = (
        excluded_energy_macro
        & out["include_in_product_explorer"].astype(bool)
        & ~is_alcohol_like
    )
    append_warning(
        out,
        product_explorer_energy_macro_warning,
        "energy_macro_mismatch",
    )
    append_warning_summary(
        out,
        product_explorer_energy_macro_warning,
        ENERGY_MACRO_WARNING_TEXT,
    )

    product_explorer_within_brand_warning = within_brand_warning_mask(out)
    append_warning(
        out,
        product_explorer_within_brand_warning,
        "within_brand_nutrition_outlier",
    )
    append_warning_summary(
        out,
        product_explorer_within_brand_warning,
        WITHIN_BRAND_WARNING_TEXT,
    )

    return out


def audit_view(df: pd.DataFrame) -> pd.DataFrame:
    view = df.copy()
    for col in AUDIT_COLUMNS:
        if col not in view.columns:
            view[col] = pd.NA
    return view[AUDIT_COLUMNS]


def explode_region(df: pd.DataFrame) -> pd.DataFrame:
    exploded = df.copy()
    exploded["region"] = exploded["region"].fillna("").astype(str)
    exploded["region"] = exploded["region"].str.split("|")
    exploded = exploded.explode("region")
    exploded["region"] = exploded["region"].replace("", "UNKNOWN")
    return exploded


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    exploded = explode_region(df)
    exploded["nutrition_quality_reason"] = exploded[
        "nutrition_quality_reason"
    ].replace("", "none")

    totals = (
        exploded.groupby(["region", "category"], dropna=False)
        .agg(
            total_records=("barcode", "count"),
            excluded_from_product_explorer_n=(
                "include_in_product_explorer",
                lambda s: int((~s.astype(bool)).sum()),
            ),
            excluded_from_market_overview_calculations_n=(
                "include_in_market_overview_calculations",
                lambda s: int((~s.astype(bool)).sum()),
            ),
            excluded_from_market_overview_charts_n=(
                "include_in_market_overview_charts",
                lambda s: int((~s.astype(bool)).sum()),
            ),
        )
        .reset_index()
    )

    grouped = (
        exploded.groupby(
            [
                "region",
                "category",
                "nutrition_quality_status",
                "nutrition_quality_reason",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="records")
    )
    summary = grouped.merge(totals, on=["region", "category"], how="left")
    summary["records_pct_of_region_category"] = (
        summary["records"] / summary["total_records"] * 100
    ).round(2)

    for col in [
        "excluded_from_product_explorer",
        "excluded_from_market_overview_calculations",
        "excluded_from_market_overview_charts",
    ]:
        count_col = f"{col}_n"
        summary[f"{col}_pct"] = (
            summary[count_col] / summary["total_records"] * 100
        ).round(2)

    return summary.sort_values(
        ["region", "category", "nutrition_quality_status", "records"],
        ascending=[True, True, True, False],
    )


def write_audits(df: pd.DataFrame, audit_dir: str = AUDIT_DIR) -> dict[str, str]:
    os.makedirs(audit_dir, exist_ok=True)
    market_cleanup_dir = os.path.join(audit_dir, "market_overview_cleanup")
    os.makedirs(market_cleanup_dir, exist_ok=True)

    outputs = {
        "hard_data_quality_errors.csv": df[
            df["nutrition_quality_status"].eq("data_quality_error")
        ],
        "energy_macro_inconsistency_15pct.csv": df[
            df["nutrition_quality_status"].eq("energy_macro_inconsistency")
        ],
        "energy_macro_accepted_exceptions.csv": df[
            df["energy_macro_exception_type"].fillna("").ne("")
        ],
        "genuine_outliers.csv": df[
            df["nutrition_quality_status"].eq("genuine_outlier")
        ],
        "category_scope_outliers.csv": df[
            df["nutrition_quality_status"].eq("category_scope_outlier")
        ],
        "nutrition_quality_flags.csv": df,
    }

    written: dict[str, str] = {}
    for filename, frame in outputs.items():
        path = os.path.join(audit_dir, filename)
        audit_view(frame).to_csv(path, index=False, encoding="utf-8-sig")
        written[filename] = path

    summary_path = os.path.join(
        audit_dir, "nutrition_quality_summary_by_region_category.csv"
    )
    build_summary(df).to_csv(summary_path, index=False, encoding="utf-8-sig")
    written["nutrition_quality_summary_by_region_category.csv"] = summary_path

    segment_summary_path = os.path.join(audit_dir, "beverage_view_segment_audit.csv")
    segment_summary = (
        df[df["category"].eq("beverages")]
        .groupby(["region", "beverage_view_segment"], dropna=False)
        .agg(
            record_count=("barcode", "count"),
            product_examples=(
                "product_name",
                lambda s: " | ".join(
                    str(v) for v in s.dropna().astype(str).head(10)
                ),
            ),
        )
        .reset_index()
        .sort_values(["region", "beverage_view_segment"])
    )
    segment_summary.to_csv(segment_summary_path, index=False, encoding="utf-8-sig")
    written["beverage_view_segment_audit.csv"] = segment_summary_path

    reason = df["nutrition_quality_reason"].fillna("").astype(str)
    minimum_energy_cols = [
        "region", "category", "barcode", "product_name", "brand", "company",
        "energy_kcal_100g", "protein_g_100g", "carbs_g_100g", "fat_g_100g",
        "sugars_g_100g", "saturated_fat_g_100g", "effective_carbs_g_100g",
        "effective_fat_g_100g", "minimum_implied_energy_kcal_100g",
        "minimum_implied_energy_diff_kcal_100g", "minimum_implied_energy_ratio",
        "nutrition_quality_reason", "image_url",
    ]
    salt_cols = [
        "region", "category", "barcode", "product_name", "brand", "company",
        "protein_g_100g", "carbs_g_100g", "fat_g_100g", "sugars_g_100g",
        "saturated_fat_g_100g", "salt_g_100g", "effective_carbs_g_100g",
        "effective_fat_g_100g", "minimum_known_mass_g_100g",
        "nutrition_quality_reason", "image_url",
    ]
    minimum_energy_path = os.path.join(
        market_cleanup_dir, "minimum_implied_energy_failures.csv"
    )
    audit_view(
        df[reason.str.contains("reported_energy_below_minimum_implied_energy")]
    ).reindex(columns=minimum_energy_cols).to_csv(
        minimum_energy_path, index=False, encoding="utf-8-sig"
    )
    written["market_overview_cleanup/minimum_implied_energy_failures.csv"] = (
        minimum_energy_path
    )

    salt_path = os.path.join(market_cleanup_dir, "salt_hard_gate_failures.csv")
    salt_reason = reason.str.contains(
        "minimum_known_nutrient_mass_exceeds_105g|salt_above_50g_per_100",
        regex=True,
    )
    audit_view(df[salt_reason]).reindex(columns=salt_cols).to_csv(
        salt_path, index=False, encoding="utf-8-sig"
    )
    written["market_overview_cleanup/salt_hard_gate_failures.csv"] = salt_path
    return written


def quality_counts(df: pd.DataFrame) -> pd.DataFrame:
    counts = df["nutrition_quality_status"].value_counts(dropna=False)
    return counts.rename_axis("nutrition_quality_status").reset_index(name="records")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build nutrition-quality flags and audit exports."
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Clean CSV input. Defaults to latest data/sample/clean_*.csv.",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_path = args.input or find_latest_clean()
    print("\nNutrition quality flag builder")
    print(f"Run timestamp: {timestamp}")
    print(f"Input: {input_path}")

    df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    flagged = build_nutrition_quality_flags(df)
    written = write_audits(flagged)

    total = len(flagged)
    excluded_calc = int(
        (~flagged["include_in_market_overview_calculations"].astype(bool)).sum()
    )
    excluded_calc_pct = excluded_calc / total * 100 if total else 0.0

    print("\nStatus counts:")
    print(quality_counts(flagged).to_string(index=False))
    print("\nExclusion summary:")
    print(f"  Total records: {total:,}")
    print(
        "  Excluded from Product Explorer: "
        f"{(~flagged['include_in_product_explorer'].astype(bool)).sum():,}"
    )
    print(
        "  Excluded from Market Overview calculations: "
        f"{excluded_calc:,} ({excluded_calc_pct:.2f}%)"
    )
    print(
        "  Excluded from Market Overview charts: "
        f"{(~flagged['include_in_market_overview_charts'].astype(bool)).sum():,}"
    )
    if excluded_calc_pct > 3.0:
        print(
            "  REVIEW NOTE: Market Overview calculation exclusion is above "
            "the 2-3% comfort range; audit files were produced for review."
        )

    print("\nAudit outputs:")
    for filename, path in written.items():
        print(f"  {filename}: {path}")


if __name__ == "__main__":
    main()
