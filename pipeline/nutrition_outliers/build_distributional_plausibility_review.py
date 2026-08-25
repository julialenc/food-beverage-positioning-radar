"""
build_distributional_plausibility_review.py
-------------------------------------------
Profiles distribution tails after locked hard-error and energy-macro governance.

The goal is pattern discovery, not automatic exclusion. Extreme values are
summarized by region, category, metric, and incremental tail band so Julia can
decide whether a tail is normal category structure, a genuine product-format
outlier cluster, category-scope noise, a data-quality issue, or still unclear.

Usage:
    python pipeline/nutrition_outliers/build_distributional_plausibility_review.py
"""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter
from datetime import datetime

import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAMPLE_DIR = os.path.join(ROOT, "data", "sample")
AUDIT_DIR = os.path.join(ROOT, "data", "nutrition_outlier_review", "audits")
FLAGS_PATH = os.path.join(AUDIT_DIR, "nutrition_quality_flags.csv")

SUMMARY_OUTPUT = os.path.join(
    AUDIT_DIR, "distributional_plausibility_tail_summary.csv"
)
EXAMPLES_OUTPUT = os.path.join(
    AUDIT_DIR, "distributional_plausibility_tail_examples.csv"
)

METRICS = [
    "energy_kcal_100g",
    "protein_g_100g",
    "carbs_g_100g",
    "sugars_g_100g",
    "fat_g_100g",
    "saturated_fat_g_100g",
    "fiber_g_100g",
    "salt_g_100g",
    "protein_g_per_100kcal",
    "carbs_g_per_100kcal",
    "fat_g_per_100kcal",
]

TAIL_BANDS = [
    ("P0-P1", "bottom", 0.0, 1.0),
    ("P1-P5", "bottom", 1.0, 5.0),
    ("P5-P10", "bottom", 5.0, 10.0),
    ("P10-P20", "bottom", 10.0, 20.0),
    ("P80-P90", "top", 80.0, 90.0),
    ("P90-P95", "top", 90.0, 95.0),
    ("P95-P99", "top", 95.0, 99.0),
    ("P99-P100", "top", 99.0, 100.000001),
]

STOPWORDS = {
    "and", "avec", "aux", "bio", "de", "des", "du", "en", "flavour",
    "flavored", "flavour", "for", "from", "la", "le", "les", "no", "of",
    "organic", "original", "sans", "the", "with", "x", "a", "au", "et",
    "saveur", "nature", "natural", "new", "pack", "pour", "sans", "sur",
    "to", "un", "une",
}

GENUINE_TOKENS = {
    "almond", "amande", "amandes", "bar", "bars", "beef", "butter", "cacao",
    "candy", "cheese", "chocolate", "chocolat", "cola", "diet", "drink",
    "gum", "hazelnut", "milk", "noix", "nuts", "peanut", "protein", "tea",
    "zero",
}

CATEGORY_SCOPE_NOISE_TOKENS = {
    "dressing", "huile", "oil", "pasta", "sauce", "soup", "vinegar",
    "vinaigre",
}

DATA_QUALITY_TOKENS = {
    "test", "tester", "unknown",
}


def find_latest_clean(sample_dir: str = SAMPLE_DIR) -> str | None:
    if not os.path.exists(sample_dir):
        return None
    files = [
        f for f in os.listdir(sample_dir)
        if f.startswith("clean_") and f.endswith(".csv")
    ]
    if not files:
        return None
    files.sort(reverse=True)
    return os.path.join(sample_dir, files[0])


def tokenize(values: pd.Series) -> list[str]:
    tokens: list[str] = []
    for value in values.dropna().astype(str):
        for token in re.findall(r"[A-Za-zÀ-ÿ0-9]{3,}", value.lower()):
            if token not in STOPWORDS and not token.isdigit():
                tokens.append(token)
    return tokens


def top_counter(values: pd.Series, limit: int = 8) -> str:
    cleaned = [
        str(value).strip().lower()
        for value in values.dropna()
        if str(value).strip() and str(value).strip().lower() != "nan"
    ]
    counts = Counter(cleaned).most_common(limit)
    return " | ".join(f"{name} ({count})" for name, count in counts)


def top_tokens(values: pd.Series, limit: int = 10) -> str:
    counts = Counter(tokenize(values)).most_common(limit)
    return " | ".join(f"{token} ({count})" for token, count in counts)


def top_off_categories(values: pd.Series, limit: int = 8) -> str:
    parts: list[str] = []
    for value in values.dropna().astype(str):
        for part in re.split(r"[,|;]", value):
            text = part.strip()
            if text and text.lower() != "nan":
                parts.append(text)
    counts = Counter(parts).most_common(limit)
    return " | ".join(f"{name} ({count})" for name, count in counts)


def product_examples(frame: pd.DataFrame, metric: str, direction: str, limit: int = 8) -> str:
    ascending = direction == "bottom"
    examples = frame.sort_values(metric, ascending=ascending).head(limit)
    values = []
    for _, row in examples.iterrows():
        barcode = str(row.get("barcode", "")).strip()
        name = str(row.get("product_name", "")).strip() or "unknown product"
        value = row.get(metric)
        if pd.notna(value):
            values.append(f"{barcode}: {name} ({value:.3g})")
        else:
            values.append(f"{barcode}: {name}")
    return " | ".join(values)


def suggest_pattern_label(frame: pd.DataFrame, metric: str, direction: str) -> str:
    record_count = len(frame)
    if record_count < 5:
        return "needs_manual_review"

    tokens = Counter(tokenize(frame["product_name"]))
    token_total = sum(tokens.values()) or 1
    top_token, top_count = tokens.most_common(1)[0] if tokens else ("", 0)
    top_token_share = top_count / token_total

    token_set = set(tokens)
    off_text = " ".join(frame.get("off_categories", pd.Series(dtype=str)).fillna("").astype(str)).lower()
    reason_text = " ".join(
        frame.get("nutrition_quality_reason", pd.Series(dtype=str)).fillna("").astype(str)
    ).lower()

    if token_set & DATA_QUALITY_TOKENS or "review" in reason_text:
        return "likely_data_quality_issue"

    if token_set & CATEGORY_SCOPE_NOISE_TOKENS or any(
        word in off_text for word in CATEGORY_SCOPE_NOISE_TOKENS
    ):
        return "likely_category_scope_noise"

    if token_set & GENUINE_TOKENS and top_token_share >= 0.08:
        return "likely_genuine_outlier_cluster"

    if top_token_share >= 0.18:
        return "likely_genuine_outlier_cluster"

    if record_count >= 30:
        return "normal_category_tail"

    return "needs_manual_review"


def load_review_base(flags_path: str, clean_path: str | None) -> pd.DataFrame:
    if not os.path.exists(flags_path):
        raise FileNotFoundError(
            f"{flags_path} not found. Run build_quality_flags.py first."
        )
    flags = pd.read_csv(flags_path, encoding="utf-8-sig", low_memory=False)

    if clean_path and os.path.exists(clean_path):
        clean_cols = ["barcode", "off_categories"]
        clean = pd.read_csv(
            clean_path,
            encoding="utf-8-sig",
            usecols=lambda col: col in clean_cols,
            low_memory=False,
        )
        clean["barcode"] = clean["barcode"].astype(str)
        flags["barcode"] = flags["barcode"].astype(str)
        flags = flags.merge(clean.drop_duplicates("barcode"), on="barcode", how="left")
    elif "off_categories" not in flags.columns:
        flags["off_categories"] = ""

    return flags


def explode_region(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["region"] = out["region"].fillna("").astype(str).str.split("|")
    out = out.explode("region")
    out["region"] = out["region"].replace("", "UNKNOWN")
    return out


def assign_tail_bands(group: pd.DataFrame, metric: str) -> pd.DataFrame:
    values = group[group[metric].notna()].copy()
    if len(values) < 20:
        return pd.DataFrame()

    values = values.sort_values(metric, ascending=True).reset_index(drop=True)
    if len(values) == 1:
        values["_percentile_position"] = 100.0
    else:
        values["_percentile_position"] = (
            values.index / (len(values) - 1) * 100
        )

    frames = []
    for band, direction, low, high in TAIL_BANDS:
        mask = (
            values["_percentile_position"].ge(low)
            & values["_percentile_position"].lt(high)
        )
        band_frame = values[mask].copy()
        if len(band_frame) == 0:
            continue
        band_frame["metric"] = metric
        band_frame["tail_band"] = band
        band_frame["tail_direction"] = direction
        frames.append(band_frame)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_distributional_review(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    eligible = df[
        df["include_in_market_overview_calculations"].astype(bool)
        & df["include_in_product_explorer"].astype(bool)
    ].copy()
    eligible = explode_region(eligible)

    example_frames = []
    for metric in METRICS:
        if metric not in eligible.columns:
            continue
        eligible[metric] = pd.to_numeric(eligible[metric], errors="coerce")
        for _, group in eligible.groupby(["region", "category"], dropna=False):
            banded = assign_tail_bands(group, metric)
            if len(banded):
                example_frames.append(banded)

    examples_all = (
        pd.concat(example_frames, ignore_index=True)
        if example_frames
        else pd.DataFrame()
    )
    if examples_all.empty:
        return pd.DataFrame(), pd.DataFrame()

    summaries = []
    example_rows = []
    group_cols = ["region", "category", "metric", "tail_band", "tail_direction"]
    for keys, group in examples_all.groupby(group_cols, dropna=False):
        region, category, metric, tail_band, direction = keys
        metric_values = pd.to_numeric(group[metric], errors="coerce")
        summary = {
            "region": region,
            "category": category,
            "metric": metric,
            "tail_band": tail_band,
            "tail_direction": direction,
            "record_count": len(group),
            "median_metric_value_in_band": round(float(metric_values.median()), 4),
            "min_metric_value_in_band": round(float(metric_values.min()), 4),
            "max_metric_value_in_band": round(float(metric_values.max()), 4),
            "top_product_name_tokens": top_tokens(group["product_name"]),
            "top_brands": top_counter(group["brand"]),
            "top_off_categories": top_off_categories(group["off_categories"]),
            "top_product_examples": product_examples(group, metric, direction),
            "suggested_pattern_label": suggest_pattern_label(group, metric, direction),
        }
        summaries.append(summary)

        ascending = direction == "bottom"
        selected_examples = group.sort_values(metric, ascending=ascending).head(20)
        for _, row in selected_examples.iterrows():
            example_rows.append(
                {
                    "region": region,
                    "category": category,
                    "metric": metric,
                    "tail_band": tail_band,
                    "tail_direction": direction,
                    "barcode": row.get("barcode"),
                    "product_name": row.get("product_name"),
                    "brand": row.get("brand"),
                    "company": row.get("company"),
                    "off_categories": row.get("off_categories"),
                    "image_url": row.get("image_url"),
                    "metric_value": row.get(metric),
                    "nutrition_quality_status": row.get("nutrition_quality_status"),
                    "nutrition_quality_reason": row.get("nutrition_quality_reason"),
                    "energy_macro_exception_type": row.get("energy_macro_exception_type"),
                    "suggested_pattern_label": summary["suggested_pattern_label"],
                }
            )

    summary_df = pd.DataFrame(summaries).sort_values(
        ["region", "category", "metric", "tail_band"]
    )
    examples_df = pd.DataFrame(example_rows).sort_values(
        ["region", "category", "metric", "tail_band", "metric_value"],
        ascending=[True, True, True, True, True],
    )
    return summary_df, examples_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build distributional plausibility tail review outputs."
    )
    parser.add_argument(
        "--flags-input",
        default=FLAGS_PATH,
        help="nutrition_quality_flags.csv path.",
    )
    parser.add_argument(
        "--clean-input",
        default=None,
        help="Clean CSV path for OFF categories. Defaults to latest clean_*.csv.",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_path = args.clean_input or find_latest_clean()
    print("\nDistributional plausibility review")
    print(f"Run timestamp: {timestamp}")
    print(f"Flags input: {args.flags_input}")
    print(f"Clean input: {clean_path or 'not found; off_categories unavailable'}")

    df = load_review_base(args.flags_input, clean_path)
    summary, examples = build_distributional_review(df)

    os.makedirs(AUDIT_DIR, exist_ok=True)
    summary.to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8-sig")
    examples.to_csv(EXAMPLES_OUTPUT, index=False, encoding="utf-8-sig")

    print(f"\nSummary rows: {len(summary):,}")
    print(f"Example rows: {len(examples):,}")
    print("\nSuggested pattern labels:")
    if len(summary):
        print(summary["suggested_pattern_label"].value_counts().to_string())
    print(f"\nSummary output: {SUMMARY_OUTPUT}")
    print(f"Examples output: {EXAMPLES_OUTPUT}")


if __name__ == "__main__":
    main()
