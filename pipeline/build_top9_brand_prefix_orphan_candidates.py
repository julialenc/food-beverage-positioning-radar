"""
Build Top 9 brand-prefix orphan candidate audit.

This script does not update product data, company mapping, or Streamlit.
It only finds products whose displayed brand is currently not mapped to a
company and whose brand string starts with a known Top 9 portfolio brand.

The matching surface is the brand field, not product_name.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "positioning_radar.db"
TOP9_MATRIX_PATH = ROOT / "data" / "reference" / "top_company_brand_portfolio_matrix.csv"
OUT_DIR = ROOT / "data" / "brand_mapping_review"
OUT_PATH = OUT_DIR / "top9_brand_prefix_orphan_candidates.csv"
SUMMARY_PATH = OUT_DIR / "top9_brand_prefix_orphan_candidates_summary.csv"

COMPANY_OTHER_LABEL = "Other / not mapped to a company"

LAUNCH_BRAND_OVERRIDES = {
    # Launch brand normalization keeps Clif as the consumer-facing master brand;
    # the Top 9 exception matrix still carries Clif Bar as its source label.
    "clif bar": ("Clif", "clif"),
}


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
    return re.sub(r"\s+", " ", text).strip()


def display_brand_key(value: object) -> str:
    return normalize_key(value)


def choose_company_for_country(row: pd.Series, primary_country: str) -> str:
    country = str(primary_country or "").strip()
    column_by_country = {
        "United States": "us_assigned_company",
        "Canada": "ca_assigned_company",
        "United Kingdom": "uk_assigned_company",
        "Ireland": "ie_assigned_company",
        "France": "fr_assigned_company",
    }
    scoped_col = column_by_country.get(country)
    if scoped_col:
        scoped = str(row.get(scoped_col, "") or "").strip()
        if scoped:
            return scoped
    return str(row.get("default_assigned_company", "") or "").strip()


def load_top9_brands() -> list[dict[str, object]]:
    df = pd.read_csv(TOP9_MATRIX_PATH, dtype=str, encoding="utf-8-sig").fillna("")
    records: dict[tuple[str, str], dict[str, object]] = {}
    for _, row in df.iterrows():
        canonical = str(row.get("canonical_brand", "") or "").strip()
        brand = str(row.get("brand", "") or "").strip()
        source_key = normalize_key(row.get("brand_key", "") or canonical or brand)
        override = LAUNCH_BRAND_OVERRIDES.get(source_key)
        if override:
            canonical, brand_key = override
        else:
            brand_key = source_key
        if not brand_key:
            continue
        key = (str(row.get("core_cpg_group", "") or "").strip(), brand_key)
        if key not in records:
            records[key] = {
                "top9_group": key[0],
                "matched_top9_brand": canonical or brand,
                "matched_brand_key": brand_key,
                "matrix_rows": [],
            }
        records[key]["matrix_rows"].append(row)

    # Longest first prevents broad brands from hiding more specific lines,
    # e.g. Cadbury Dairy Milk before Cadbury.
    return sorted(
        records.values(),
        key=lambda item: len(str(item["matched_brand_key"])),
        reverse=True,
    )


def prefix_match(candidate_key: str, brand_key: str) -> tuple[bool, str]:
    if not candidate_key or not brand_key:
        return False, ""
    if candidate_key == brand_key:
        return True, "exact_brand_match"
    if candidate_key.startswith(brand_key + " "):
        return True, "brand_prefix_with_separator"

    # Concatenated forms are useful candidates for manual review when the
    # portfolio brand is long enough. Example: milkamondelez starts with milka.
    # Very short brands such as LU and Hu require a separator/exact match to
    # avoid sweeping up unrelated strings.
    if len(brand_key.replace(" ", "")) >= 4 and candidate_key.startswith(
        brand_key.replace(" ", "")
    ):
        return True, "brand_prefix_concatenated_review"
    return False, ""


def load_orphan_products() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    latest = conn.execute("select max(ingested_at) from products").fetchone()[0]
    query = """
        SELECT
            barcode,
            product_name,
            brands,
            off_brands_raw,
            primary_brand,
            normalized_brand,
            COALESCE(NULLIF(TRIM(normalized_brand), ''), primary_brand) AS displayed_brand,
            query_category,
            primary_country,
            observed_market_region_codes,
            image_url,
            resolved_company,
            ingested_at
        FROM products
        WHERE ingested_at = ?
          AND resolved_company = ?
          AND COALESCE(NULLIF(TRIM(normalized_brand), ''), primary_brand) IS NOT NULL
          AND TRIM(COALESCE(NULLIF(TRIM(normalized_brand), ''), primary_brand)) != ''
          AND TRIM(LOWER(COALESCE(NULLIF(TRIM(normalized_brand), ''), primary_brand)))
              NOT IN ('unknown', 'nan', 'none', 'null')
    """
    return pd.read_sql_query(query, conn, params=[latest, COMPANY_OTHER_LABEL])


def join_examples(values: pd.Series, limit: int = 5) -> str:
    seen: list[str] = []
    for raw in values.fillna("").astype(str):
        text = raw.strip()
        if not text or text in seen:
            continue
        seen.append(text)
        if len(seen) >= limit:
            break
    return " | ".join(seen)


def build_candidates() -> tuple[pd.DataFrame, pd.DataFrame]:
    top9_brands = load_top9_brands()
    products = load_orphan_products()
    products["displayed_brand_key"] = products["displayed_brand"].map(display_brand_key)

    candidate_rows = []
    for product in products.itertuples(index=False):
        candidate_key = product.displayed_brand_key
        for brand in top9_brands:
            matched, rule = prefix_match(candidate_key, str(brand["matched_brand_key"]))
            if not matched:
                continue
            matrix_rows = brand["matrix_rows"]
            company_candidates = {
                choose_company_for_country(row, product.primary_country)
                for row in matrix_rows
            }
            company_candidates = {c for c in company_candidates if c}
            candidate_rows.append({
                "matched_top9_company_group": brand["top9_group"],
                "matched_top9_brand": brand["matched_top9_brand"],
                "matched_brand_key": brand["matched_brand_key"],
                "candidate_orphan_brand": product.displayed_brand,
                "candidate_orphan_brand_key": candidate_key,
                "current_company_owner": product.resolved_company,
                "proposed_company_owner_candidates": " | ".join(sorted(company_candidates)),
                "query_category": product.query_category,
                "primary_country": product.primary_country,
                "observed_market_region_codes": product.observed_market_region_codes,
                "product_name": product.product_name,
                "barcode": product.barcode,
                "brands": product.brands,
                "off_brands_raw": product.off_brands_raw,
                "primary_brand": product.primary_brand,
                "normalized_brand": product.normalized_brand,
                "image_url": product.image_url,
                "match_rule": rule,
                "suggested_action": "review_prefix_candidate",
                "review_decision": "",
                "review_note": "",
            })
            break

    detail = pd.DataFrame(candidate_rows)
    if detail.empty:
        return detail, pd.DataFrame()

    group_cols = [
        "matched_top9_company_group",
        "matched_top9_brand",
        "matched_brand_key",
        "candidate_orphan_brand",
        "candidate_orphan_brand_key",
        "current_company_owner",
        "proposed_company_owner_candidates",
        "query_category",
        "primary_country",
        "observed_market_region_codes",
        "match_rule",
    ]
    grouped = []
    for keys, grp in detail.groupby(group_cols, dropna=False, sort=True):
        row = dict(zip(group_cols, keys))
        row["product_count"] = int(len(grp))
        row["example_product_names"] = join_examples(grp["product_name"])
        row["example_off_brands_raw"] = join_examples(grp["off_brands_raw"])
        row["example_barcodes"] = join_examples(grp["barcode"])
        row["example_image_urls"] = join_examples(grp["image_url"], limit=3)
        row["suggested_action"] = "review_prefix_candidate"
        row["review_decision"] = ""
        row["review_note"] = ""
        grouped.append(row)
    review = pd.DataFrame(grouped).sort_values(
        ["product_count", "matched_top9_brand", "candidate_orphan_brand"],
        ascending=[False, True, True],
    )

    summary = (
        review.groupby(
            [
                "matched_top9_company_group",
                "matched_top9_brand",
                "match_rule",
            ],
            dropna=False,
        )["product_count"]
        .sum()
        .reset_index(name="candidate_product_count")
        .sort_values("candidate_product_count", ascending=False)
    )
    return review, summary


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    review, summary = build_candidates()
    review.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")

    print(f"Wrote: {OUT_PATH}")
    print(f"Wrote: {SUMMARY_PATH}")
    print(f"Review rows: {len(review)}")
    print(f"Candidate products: {int(review['product_count'].sum()) if not review.empty else 0}")
    if not summary.empty:
        print("\nTop candidate groups:")
        print(summary.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
