"""
Diagnose primary-brand extraction before changing clean.py.

The current clean.py behavior uses the first OFF brand token as primary_brand.
This audit proposes brand-level alternatives when a known Top 9 portfolio brand
appears elsewhere in the raw OFF brands field or in the product name.

Outputs are review files only. This script does not mutate source data,
reference mappings, the database, or Streamlit-facing tables.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "positioning_radar.db"
TOP_COMPANY_MATRIX = ROOT / "data" / "reference" / "top_company_brand_portfolio_matrix.csv"
COMPANY_BRAND_MAPPING = ROOT / "data" / "reference" / "company_brand_mapping.csv"
OUT_DIR = ROOT / "data" / "brand_mapping_review"
DETAIL_OUT = OUT_DIR / "brand_extraction_primary_brand_diagnosis.csv"
SUMMARY_OUT = OUT_DIR / "brand_extraction_primary_brand_diagnosis_summary.csv"
NESTLE_FR_SNACKS_OUT = OUT_DIR / "nestle_france_snacks_primary_brand_diagnosis.csv"


PARENT_COMPANY_KEYS = {
    "nestle",
    "pepsico",
    "pepsi co",
    "the coca cola company",
    "coca cola company",
    "coca cola",
    "mondelez",
    "mondelez international",
    "danone",
    "kraft heinz",
    "the kraft heinz company",
    "hershey",
    "the hershey company",
    "starbucks",
    "unilever",
    "unilever foods",
}


GENERIC_BRAND_KEYS = {
    "",
    "unknown",
    "nan",
    "none",
    "null",
    "bio",
    "classic",
    "original",
    "selection",
    "extra",
    "light",
    "zero",
    "diet",
}


def normalize_key(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    if not text or text == "nan":
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " and ")
    text = re.sub(r"['`´’]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_brand_tokens(raw_brands: object) -> list[str]:
    if raw_brands is None:
        return []
    text = str(raw_brands).strip()
    if not text or text.lower() == "nan":
        return []
    parts = re.split(r"[,;|/]+", text)
    return [normalize_key(part) for part in parts if normalize_key(part)]


def compile_phrase_pattern(key: str) -> re.Pattern[str]:
    escaped = re.escape(key)
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def load_portfolio_brands() -> pd.DataFrame:
    matrix = pd.read_csv(TOP_COMPANY_MATRIX, dtype=str, encoding="utf-8-sig").fillna("")
    rows = []
    for _, row in matrix.iterrows():
        key = normalize_key(row.get("brand_key") or row.get("brand"))
        canonical = (row.get("canonical_brand") or row.get("brand") or "").strip()
        group = (row.get("core_cpg_group") or "").strip()
        if key in GENERIC_BRAND_KEYS or len(key) < 3:
            continue
        if key in PARENT_COMPANY_KEYS:
            continue
        rows.append(
            {
                "brand_key": key,
                "canonical_brand": canonical,
                "core_cpg_group": group,
                "key_length": len(key),
                "token_count": len(key.split()),
            }
        )
    if COMPANY_BRAND_MAPPING.exists():
        mapping = pd.read_csv(COMPANY_BRAND_MAPPING, dtype=str, encoding="utf-8-sig").fillna("")
        for _, row in mapping.iterrows():
            parent = (row.get("parent_company") or "").strip()
            if not any(normalize_key(parent).startswith(normalize_key(key)) for key in PARENT_COMPANY_KEYS):
                continue
            canonical = (
                row.get("normalized_brand")
                or row.get("brand")
                or row.get("primary_brand_db")
                or ""
            ).strip()
            for source_col in ["normalized_brand", "brand", "primary_brand_db"]:
                key = normalize_key(row.get(source_col, ""))
                if key in GENERIC_BRAND_KEYS or len(key) < 3:
                    continue
                if key in PARENT_COMPANY_KEYS:
                    continue
                rows.append(
                    {
                        "brand_key": key,
                        "canonical_brand": canonical,
                        "core_cpg_group": parent,
                        "key_length": len(key),
                        "token_count": len(key.split()),
                    }
                )
    portfolio = pd.DataFrame(rows).drop_duplicates("brand_key")
    return portfolio.sort_values(["token_count", "key_length"], ascending=False).reset_index(drop=True)


def build_lookup(portfolio: pd.DataFrame) -> tuple[dict[str, dict[str, str]], list[tuple[str, re.Pattern[str], dict[str, str]]]]:
    exact = {}
    patterns = []
    for record in portfolio.to_dict("records"):
        exact[record["brand_key"]] = record
        compact_key = record["brand_key"].replace(" ", "")
        if compact_key and compact_key not in exact:
            exact[compact_key] = record
        patterns.append((record["brand_key"], compile_phrase_pattern(record["brand_key"]), record))
    return exact, patterns


def choose_from_brand_tokens(
    tokens: list[str],
    current_primary: str,
    exact_lookup: dict[str, dict[str, str]],
) -> tuple[str, str, str, str]:
    matches = []
    for token in tokens:
        lookup_key = token if token in exact_lookup else token.replace(" ", "")
        if lookup_key in exact_lookup:
            record = exact_lookup[lookup_key]
            matches.append((record["token_count"], record["key_length"], token, record))

    if not matches:
        if current_primary in PARENT_COMPANY_KEYS:
            for token in tokens:
                if token not in PARENT_COMPANY_KEYS and token not in GENERIC_BRAND_KEYS:
                    cleaned = token
                    for parent_key in sorted(PARENT_COMPANY_KEYS, key=len, reverse=True):
                        if cleaned.startswith(parent_key + " "):
                            cleaned = cleaned[len(parent_key) + 1 :].strip()
                            break
                    if cleaned and cleaned not in GENERIC_BRAND_KEYS:
                        return (
                            cleaned,
                            token,
                            "current primary brand is parent/company token; another OFF brand token needs brand-level review",
                            "",
                        )
        return "", "", "", ""

    matches.sort(reverse=True)
    _, _, matched_key, record = matches[0]
    proposed = normalize_key(record["canonical_brand"])
    if proposed and proposed != current_primary:
        reason = "known portfolio brand appears in OFF brands field"
        if current_primary in PARENT_COMPANY_KEYS:
            reason = "current primary brand is parent/company token; portfolio brand appears in OFF brands field"
        return proposed, matched_key, reason, record["core_cpg_group"]
    return "", "", "", ""


def choose_from_product_name(
    product_name_key: str,
    current_primary: str,
    patterns: list[tuple[str, re.Pattern[str], dict[str, str]]],
) -> tuple[str, str, str, str]:
    if not product_name_key:
        return "", "", "", ""
    for brand_key, pattern, record in patterns:
        if pattern.search(product_name_key):
            proposed = normalize_key(record["canonical_brand"])
            if proposed and proposed != current_primary:
                reason = "known portfolio brand appears in product name while OFF primary brand is less specific"
                if current_primary in PARENT_COMPANY_KEYS:
                    reason = "current primary brand is parent/company token; portfolio brand appears in product name"
                return proposed, brand_key, reason, record["core_cpg_group"]
    return "", "", "", ""


def classify_row(
    row: pd.Series,
    exact_lookup: dict[str, dict[str, str]],
    patterns: list[tuple[str, re.Pattern[str], dict[str, str]]],
) -> dict[str, str]:
    raw_brands = row.get("brands", "")
    current_primary = normalize_key(row.get("primary_brand", ""))
    tokens = split_brand_tokens(raw_brands)
    product_name_key = normalize_key(row.get("product_name", ""))

    proposed, matched_key, reason, group = choose_from_brand_tokens(tokens, current_primary, exact_lookup)
    source = "top_company_portfolio_matrix_off_brands"
    confidence = "high"

    if not proposed and current_primary in PARENT_COMPANY_KEYS:
        proposed, matched_key, reason, group = choose_from_product_name(product_name_key, current_primary, patterns)
        source = "top_company_portfolio_matrix_product_name"
        confidence = "medium"

    if not proposed:
        proposed = current_primary
        source = "no_change"
        confidence = ""
        reason = "no more-specific Top 9 portfolio brand detected"
        matched_key = ""
        group = ""

    return {
        "raw_brand_tokens": "; ".join(tokens),
        "current_primary_brand": current_primary,
        "proposed_primary_brand": proposed,
        "primary_brand_would_change": str(proposed != current_primary),
        "detected_portfolio_brand_key": matched_key,
        "detected_portfolio_group": group,
        "detection_source": source,
        "detection_confidence": confidence,
        "detection_reason": reason,
    }


def read_products() -> pd.DataFrame:
    parent_filters = [
        "nestl",
        "pepsi",
        "coca",
        "mondelez",
        "danone",
        "kraft",
        "heinz",
        "hershey",
        "starbucks",
        "unilever",
    ]
    where_parts = [
        "lower(coalesce(primary_brand, '')) in ("
        + ",".join(["?"] * len(PARENT_COMPANY_KEYS))
        + ")"
    ]
    params = list(PARENT_COMPANY_KEYS)
    for term in parent_filters:
        where_parts.append("lower(coalesce(brands, '')) like ?")
        params.append(f"%{term}%")

    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql_query(
            f"""
            select
                barcode,
                product_name,
                brands,
                primary_brand,
                query_category,
                observed_market_region_codes,
                countries,
                off_categories
            from products
            where {" or ".join(where_parts)}
            """,
            con,
            params=params,
        ).fillna("")


def write_outputs(audit: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    changed = audit[audit["primary_brand_would_change"] == "True"].copy()
    changed.to_csv(DETAIL_OUT, index=False, encoding="utf-8-sig")

    summary = (
        audit.groupby(
            [
                "query_category",
                "observed_market_region_codes",
                "current_primary_brand",
                "proposed_primary_brand",
                "detected_portfolio_group",
                "detection_source",
                "detection_reason",
            ],
            dropna=False,
        )
        .agg(
            record_count=("barcode", "count"),
            example_product_names=("product_name", lambda s: " | ".join([x for x in s.astype(str).head(5) if x])),
            example_raw_brands=("brands", lambda s: " | ".join([x for x in s.astype(str).head(5) if x])),
        )
        .reset_index()
        .sort_values("record_count", ascending=False)
    )
    summary.to_csv(SUMMARY_OUT, index=False, encoding="utf-8-sig")

    nestle_fr_snacks = audit[
        (audit["query_category"] == "snacks")
        & audit["observed_market_region_codes"].str.contains("FRANCE", na=False)
        & (
            (audit["current_primary_brand"] == "nestle")
            | audit["brands"].map(normalize_key).str.contains("nestle", na=False)
            | audit["detected_portfolio_group"].str.contains("Nest", case=False, na=False)
        )
    ].copy()
    nestle_fr_snacks.to_csv(NESTLE_FR_SNACKS_OUT, index=False, encoding="utf-8-sig")


def validate_outputs(audit: pd.DataFrame) -> None:
    checks = {
        ("nestle, kitkat", "kitkat"),
        ("nestle, kit kat", "kitkat"),
        ("nestle, lion", "lion"),
        ("nestle, smarties", "smarties"),
        ("nestle, after eight", "after eight"),
        ("nestle, chocapic", "chocapic"),
    }
    exact_lookup, patterns = build_lookup(load_portfolio_brands())
    for raw_brands, expected in checks:
        test_row = pd.Series({"brands": raw_brands, "primary_brand": "nestle", "product_name": ""})
        result = classify_row(test_row, exact_lookup, patterns)
        actual = result["proposed_primary_brand"]
        if actual != expected:
            raise AssertionError(f"{raw_brands!r}: expected {expected!r}, got {actual!r}")

    if audit.empty:
        raise AssertionError("Brand extraction audit unexpectedly has no rows.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose portfolio-aware primary-brand extraction.")
    parser.add_argument(
        "--all-rows",
        action="store_true",
        help="Write all rows to the detail output instead of only rows where proposed primary_brand differs.",
    )
    args = parser.parse_args()

    portfolio = load_portfolio_brands()
    exact_lookup, patterns = build_lookup(portfolio)
    products = read_products()
    diagnostics = products.apply(lambda row: classify_row(row, exact_lookup, patterns), axis=1, result_type="expand")
    audit = pd.concat([products, diagnostics], axis=1)

    validate_outputs(audit)
    if args.all_rows:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        audit.to_csv(DETAIL_OUT, index=False, encoding="utf-8-sig")
    else:
        write_outputs(audit)

    changed = (audit["primary_brand_would_change"] == "True").sum()
    print(f"Rows reviewed: {len(audit):,}")
    print(f"Rows with proposed primary_brand change: {changed:,}")
    print(f"Wrote: {DETAIL_OUT}")
    print(f"Wrote: {SUMMARY_OUT}")
    print(f"Wrote: {NESTLE_FR_SNACKS_OUT}")


if __name__ == "__main__":
    main()
