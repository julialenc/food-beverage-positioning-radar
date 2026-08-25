"""
Build Layer 3 company / ownership mapping audit.

This review compares the current legacy company attribution path
(`primary_brand`) with the proposed recovered path (`normalized_brand`).
It does not modify the database, Streamlit code, or reference mappings.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample"
OUT_DIR = ROOT / "data" / "brand_mapping_review"
OUT_PATH = OUT_DIR / "company_mapping_layer3_review.csv"
SUMMARY_PATH = OUT_DIR / "company_mapping_layer3_summary.csv"
COMPANY_MAPPING_PATH = ROOT / "data" / "reference" / "company_brand_mapping.csv"
TOP9_MATRIX_PATH = ROOT / "data" / "reference" / "top_company_brand_portfolio_matrix.csv"

COMPANY_OTHER_LABEL = "Other / not mapped to a company"
COMPANY_MANUAL_REVIEW_LABEL = "Manual review / complex ownership"


def normalize_key(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    if not text or text == "nan":
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = text.replace("&", " and ")
    text = re.sub(r"['`´’]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def latest_clean_file() -> Path:
    files = sorted(SAMPLE_DIR.glob("clean_*.csv"), reverse=True)
    if not files:
        raise FileNotFoundError("No data/sample/clean_*.csv file found. Run clean.py first.")
    return files[0]


def split_scope_values(value: object) -> list[str]:
    return [v.strip() for v in str(value or "").split("|") if v.strip()]


def any_token_match(source_value: object, tokens: list[str]) -> bool:
    if not tokens:
        return False
    source_tokens = {
        v.strip().lower()
        for v in str(source_value or "").split("|")
        if v.strip()
    }
    return any(token.lower() in source_tokens for token in tokens)


def row_scope_matches(row: dict[str, str], countries: str, region_codes: str) -> bool:
    include_regions = split_scope_values(row.get("region_codes_include", ""))
    exclude_regions = split_scope_values(row.get("region_codes_exclude", ""))
    include_countries = split_scope_values(row.get("country_tags_include", ""))
    exclude_countries = split_scope_values(row.get("country_tags_exclude", ""))

    if not include_regions and not include_countries:
        return False
    if exclude_regions and any_token_match(region_codes, exclude_regions):
        return False
    if exclude_countries and any_token_match(countries, exclude_countries):
        return False

    return (
        any_token_match(region_codes, include_regions)
        or any_token_match(countries, include_countries)
    )


def load_company_mapping_rows() -> list[dict[str, str]]:
    mapping = pd.read_csv(COMPANY_MAPPING_PATH, dtype=str, encoding="utf-8-sig").fillna("")
    rows: list[dict[str, str]] = []
    for _, raw in mapping.iterrows():
        company = str(raw.get("parent_company", "")).strip()
        brand_fields = [
            raw.get("normalized_brand", ""),
            raw.get("primary_brand_db", ""),
            raw.get("brand", ""),
        ]
        for brand in brand_fields:
            brand = str(brand).strip()
            if not company or not brand:
                continue
            row = {
                "parent_company": company,
                "brand": brand,
                "brand_norm": normalize_key(brand),
                "status": (
                    str(raw.get("ownership_resolution_status", "")).strip().lower()
                    or "direct"
                ),
                "country_tags_include": str(raw.get("country_tags_include", "")).strip(),
                "country_tags_exclude": str(raw.get("country_tags_exclude", "")).strip(),
                "region_codes_include": str(raw.get("region_codes_include", "")).strip(),
                "region_codes_exclude": str(raw.get("region_codes_exclude", "")).strip(),
                "market_scope": str(raw.get("market_scope", "")).strip(),
                "category_scope": str(raw.get("category_scope", "")).strip()
                    or str(raw.get("category", "")).strip(),
                "mapping_source": str(raw.get("brand_mapping_source", "")).strip()
                    or "company_brand_mapping.csv",
                "review_note": str(raw.get("review_note", "")).strip()
                    or str(raw.get("notes", "")).strip(),
            }
            if row["brand_norm"]:
                rows.append(row)
    return rows


def mapping_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        out.setdefault(row["brand_norm"], []).append(row)
    return out


def resolve_company(
    brand: object,
    countries: object,
    region_codes: object,
    index: dict[str, list[dict[str, str]]],
) -> dict[str, str]:
    brand_norm = normalize_key(brand)
    rows = index.get(brand_norm, [])
    if not brand_norm or not rows:
        return {
            "company": COMPANY_OTHER_LABEL,
            "ownership_resolution_status": "unresolved",
            "mapping_source": "no_mapping_match",
            "review_note": "",
            "matched_mapping_brand": "",
        }

    scoped = [
        row for row in rows
        if row["status"] in {"market_scoped", "licensed_or_partnered"}
        and (
            row.get("region_codes_include")
            or row.get("country_tags_include")
            or row.get("region_codes_exclude")
            or row.get("country_tags_exclude")
        )
    ]
    manual = [
        row for row in rows
        if row["status"] == "manual_review"
        or row["parent_company"].lower() == COMPANY_MANUAL_REVIEW_LABEL.lower()
    ]
    direct = [
        row for row in rows
        if row["status"] in {
            "direct",
            "recently_demerged",
            "recently_sold_or_spun_off",
            "licensed_or_partnered",
        }
        and row["parent_company"].lower() != COMPANY_MANUAL_REVIEW_LABEL.lower()
    ]

    selected: dict[str, str] | None = None
    if scoped:
        matches = [
            row for row in scoped
            if row_scope_matches(row, str(countries or ""), str(region_codes or ""))
        ]
        companies = sorted({row["parent_company"] for row in matches})
        if len(companies) == 1:
            selected = matches[0]
        else:
            return {
                "company": COMPANY_MANUAL_REVIEW_LABEL,
                "ownership_resolution_status": "manual_review",
                "mapping_source": "scoped_mapping_ambiguous_or_unmatched",
                "review_note": "Market-scoped mapping exists but did not resolve to one company.",
                "matched_mapping_brand": rows[0]["brand"],
            }
    elif len({row["parent_company"] for row in direct}) == 1:
        selected = direct[0]
    elif len({row["parent_company"] for row in direct}) > 1 or manual:
        return {
            "company": COMPANY_MANUAL_REVIEW_LABEL,
            "ownership_resolution_status": "manual_review",
            "mapping_source": "multiple_or_manual_mapping_rows",
            "review_note": "Multiple direct/manual mapping rows exist for this brand.",
            "matched_mapping_brand": rows[0]["brand"],
        }

    if selected is None:
        return {
            "company": COMPANY_OTHER_LABEL,
            "ownership_resolution_status": "unresolved",
            "mapping_source": "no_resolvable_mapping_row",
            "review_note": "",
            "matched_mapping_brand": rows[0]["brand"],
        }

    return {
        "company": selected["parent_company"],
        "ownership_resolution_status": selected["status"],
        "mapping_source": selected["mapping_source"],
        "review_note": selected["review_note"],
        "matched_mapping_brand": selected["brand"],
    }


def load_top9_brand_keys() -> set[str]:
    if not TOP9_MATRIX_PATH.exists():
        return set()
    matrix = pd.read_csv(TOP9_MATRIX_PATH, dtype=str, encoding="utf-8-sig").fillna("")
    keys = set()
    for _, row in matrix.iterrows():
        for col in ["brand_key", "canonical_brand", "brand"]:
            key = normalize_key(row.get(col, ""))
            if key:
                keys.add(key)
    return keys


def sample_examples(series: pd.Series, n: int = 5) -> str:
    return " | ".join(
        [
            value for value in series.dropna().astype(str).head(n)
            if value and value.lower() != "nan"
        ]
    )


def main() -> None:
    clean_path = latest_clean_file()
    df = pd.read_csv(clean_path, dtype=str, encoding="utf-8-sig").fillna("")
    required = {
        "normalized_brand",
        "primary_brand",
        "countries",
        "observed_market_region_codes",
        "query_category",
        "product_name",
        "off_brands_raw",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"Latest clean file is missing Layer 3 input columns: {missing}")

    rows = load_company_mapping_rows()
    index = mapping_index(rows)
    top9_keys = load_top9_brand_keys()

    unique_inputs = (
        df[["primary_brand", "normalized_brand", "countries", "observed_market_region_codes"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    cache: dict[tuple[str, str, str, str], tuple[dict[str, str], dict[str, str]]] = {}
    for _, row in unique_inputs.iterrows():
        key = (
            row["primary_brand"],
            row["normalized_brand"],
            row["countries"],
            row["observed_market_region_codes"],
        )
        cache[key] = (
            resolve_company(row["primary_brand"], row["countries"], row["observed_market_region_codes"], index),
            resolve_company(row["normalized_brand"], row["countries"], row["observed_market_region_codes"], index),
        )

    current_results = []
    proposed_results = []
    for key in zip(
        df["primary_brand"],
        df["normalized_brand"],
        df["countries"],
        df["observed_market_region_codes"],
    ):
        current, proposed = cache[key]
        current_results.append(current)
        proposed_results.append(proposed)

    current_df = pd.DataFrame(current_results).add_prefix("current_")
    proposed_df = pd.DataFrame(proposed_results).add_prefix("proposed_")
    audit = pd.concat([df, current_df, proposed_df], axis=1)
    audit["company_mapping_would_change"] = (
        audit["current_company"] != audit["proposed_company"]
    )
    audit["normalized_brand_is_top9_portfolio"] = audit["normalized_brand"].map(
        lambda value: normalize_key(value) in top9_keys
    )

    review_scope = audit[
        audit["company_mapping_would_change"]
        | audit["normalized_brand_is_top9_portfolio"]
        | audit["proposed_ownership_resolution_status"].isin(
            ["manual_review", "market_scoped", "licensed_or_partnered", "recently_demerged", "recently_sold_or_spun_off"]
        )
        | audit["proposed_company"].isin([COMPANY_OTHER_LABEL, COMPANY_MANUAL_REVIEW_LABEL])
    ].copy()

    group_cols = [
        "normalized_brand",
        "legacy_primary_brand",
        "primary_brand",
        "brand_entity_raw",
        "brand_entity_source",
        "brand_alias_source",
        "brand_alias_review_status",
        "query_category",
        "primary_country",
        "observed_market_region_codes",
        "current_company",
        "proposed_company",
        "proposed_ownership_resolution_status",
        "proposed_mapping_source",
        "proposed_review_note",
        "proposed_matched_mapping_brand",
        "company_mapping_would_change",
        "normalized_brand_is_top9_portfolio",
    ]
    group_cols = [col for col in group_cols if col in review_scope.columns]
    review = (
        review_scope.groupby(group_cols, dropna=False)
        .agg(
            product_count=("barcode", "count"),
            example_product_names=("product_name", sample_examples),
            example_off_brands_raw=("off_brands_raw", sample_examples),
        )
        .reset_index()
        .sort_values(["company_mapping_would_change", "product_count"], ascending=[False, False])
    )

    summary = (
        audit.groupby(
            [
                "query_category",
                "observed_market_region_codes",
                "current_company",
                "proposed_company",
                "proposed_ownership_resolution_status",
            ],
            dropna=False,
        )
        .agg(product_count=("barcode", "count"))
        .reset_index()
        .sort_values("product_count", ascending=False)
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    review.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")

    print(f"Input clean file: {clean_path}")
    print(f"Rows reviewed: {len(df):,}")
    print(f"Rows in Layer 3 review scope: {len(review_scope):,}")
    print(f"Grouped review rows: {len(review):,}")
    print(f"Rows where company would change: {int(audit['company_mapping_would_change'].sum()):,}")
    print(f"Wrote: {OUT_PATH}")
    print(f"Wrote: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
