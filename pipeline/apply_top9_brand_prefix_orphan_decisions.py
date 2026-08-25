"""
Apply reviewed Top 9 brand-prefix orphan decisions.

Input is the manually reviewed CSV:
    C:/Users/julia/OneDrive/Desktop/Downloads_temp/
    top9_brand_prefix_orphan_candidates_reviewed.csv

This script is intentionally narrow:
  - applies only rows where apply_to_mapping == True;
  - never applies rows whose review_decision starts with "reject prefix match";
  - removes any previous partial rows from this exact source before rebuilding;
  - updates reference files only, not product rows or the SQLite database.

Run clean.py and load.py afterwards to materialize the reference updates.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = ROOT / "data" / "brand_mapping_review"
EXTERNAL_REVIEWED_PATH = Path(
    r"C:\Users\julia\OneDrive\Desktop\Downloads_temp"
    r"\top9_brand_prefix_orphan_candidates_reviewed.csv"
)
LOCAL_REVIEWED_PATH = REVIEW_DIR / "top9_brand_prefix_orphan_candidates_reviewed.csv"
DECISION_PATH = REVIEW_DIR / "top9_brand_prefix_orphan_candidates_applied_decisions.csv"
SUMMARY_PATH = REVIEW_DIR / "top9_brand_prefix_orphan_apply_summary.csv"
ALIAS_PATH = ROOT / "data" / "reference" / "brand_alias_mapping.csv"
COMPANY_MAPPING_PATH = ROOT / "data" / "reference" / "company_brand_mapping.csv"

ALIAS_PATTERN = "top9_prefix_orphan_review"
SOURCE_TAG = "top9_brand_prefix_orphan_review_20260825"


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


def clean_company(value: object) -> str:
    text = str(value or "").strip()
    fixes = {
        "Mondelez International": "Mondelēz International",
        "Nestle": "Nestlé",
    }
    return fixes.get(text, text)


def clean_brand(value: object) -> str:
    text = str(value or "").strip()
    fixes = {
        "Lay's": "Lay’s",
    }
    return fixes.get(text, text)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def source_review_path() -> Path:
    if EXTERNAL_REVIEWED_PATH.exists():
        return EXTERNAL_REVIEWED_PATH
    if LOCAL_REVIEWED_PATH.exists():
        return LOCAL_REVIEWED_PATH
    raise FileNotFoundError(
        "Reviewed prefix-orphan file not found in Downloads_temp or data/brand_mapping_review."
    )


def prepare_reviewed_decisions() -> pd.DataFrame:
    source = source_review_path()
    reviewed = read_csv(source)
    write_csv(LOCAL_REVIEWED_PATH, reviewed)

    reviewed["apply_to_mapping_bool"] = (
        reviewed["apply_to_mapping"].astype(str).str.strip().str.lower().eq("true")
    )
    reviewed["review_decision_clean"] = reviewed["review_decision"].astype(str).str.strip()
    reviewed["target_company_owner"] = reviewed["final_company_owner"].map(clean_company)
    reviewed["target_normalized_brand"] = reviewed["matched_top9_brand"].map(clean_brand)
    reviewed["target_primary_brand_db"] = reviewed["candidate_orphan_brand"].astype(str).str.strip()
    reviewed["target_brand_key"] = reviewed["target_primary_brand_db"].map(normalize_key)
    reviewed["target_company_key"] = reviewed["target_company_owner"].map(normalize_key)
    reviewed["product_count_num"] = pd.to_numeric(
        reviewed["product_count"], errors="coerce"
    ).fillna(0).astype(int)

    reject_mask = reviewed["review_decision_clean"].str.startswith("reject prefix match")
    reviewed.loc[reject_mask, "apply_to_mapping_bool"] = False

    applied = reviewed[
        reviewed["apply_to_mapping_bool"]
        & (reviewed["target_company_owner"] != "")
        & (reviewed["target_primary_brand_db"] != "")
    ].copy()

    reviewed["applied_by_script"] = reviewed.index.isin(applied.index)
    write_csv(DECISION_PATH, reviewed)
    return applied


def purge_previous_alias_rows() -> int:
    alias_df = read_csv(ALIAS_PATH)
    before = len(alias_df)
    if "pattern" in alias_df.columns:
        alias_df = alias_df[alias_df["pattern"].astype(str) != ALIAS_PATTERN].copy()
    write_csv(ALIAS_PATH, alias_df)
    return before - len(alias_df)


def purge_previous_company_rows() -> int:
    mapping_df = read_csv(COMPANY_MAPPING_PATH)
    before = len(mapping_df)
    if "brand_mapping_source" in mapping_df.columns:
        mapping_df = mapping_df[
            mapping_df["brand_mapping_source"].astype(str) != SOURCE_TAG
        ].copy()
    write_csv(COMPANY_MAPPING_PATH, mapping_df)
    return before - len(mapping_df)


def append_alias_rows(applied: pd.DataFrame) -> int:
    alias_df = read_csv(ALIAS_PATH)
    existing = {
        (normalize_key(row["variant_brand"]), normalize_key(row["canonical_brand"]))
        for _, row in alias_df.iterrows()
    }
    rows = []
    grouped = (
        applied.groupby(
            ["target_primary_brand_db", "target_normalized_brand"],
            dropna=False,
            as_index=False,
        )
        .agg(product_count_num=("product_count_num", "sum"))
        .sort_values("product_count_num", ascending=False)
    )
    for _, row in grouped.iterrows():
        variant = row["target_primary_brand_db"]
        canonical = row["target_normalized_brand"]
        key = (normalize_key(variant), normalize_key(canonical))
        if not key[0] or not key[1] or key in existing:
            continue
        existing.add(key)
        rows.append({
            "variant_brand": variant,
            "canonical_brand": canonical,
            "pattern": ALIAS_PATTERN,
            "variant_count": str(int(row["product_count_num"])),
            "canonical_count": "",
            "confidence": "reviewed",
            "action": "confirm",
            "notes": "Manually reviewed Top 9 brand-prefix orphan cleanup.",
        })
    if rows:
        alias_df = pd.concat([alias_df, pd.DataFrame(rows)], ignore_index=True)
        write_csv(ALIAS_PATH, alias_df)
    return len(rows)


def status_from_decision(decision: str) -> str:
    if decision in {
        "map to Cereal Partners Worldwide",
        "map to General Mills",
        "map to Nestlé",
    }:
        return "market_scoped"
    return "direct"


def append_company_rows(applied: pd.DataFrame) -> int:
    mapping_df = read_csv(COMPANY_MAPPING_PATH)
    existing = {
        (
            normalize_key(row["parent_company"]),
            normalize_key(row["primary_brand_db"]),
            str(row.get("category_scope") or row.get("category") or "").strip(),
            str(row.get("region_codes_include") or "").strip(),
        )
        for _, row in mapping_df.iterrows()
    }
    rows = []
    grouped = (
        applied.groupby(
            [
                "target_company_owner",
                "target_normalized_brand",
                "target_primary_brand_db",
                "query_category",
                "observed_market_region_codes",
                "review_decision_clean",
            ],
            dropna=False,
            as_index=False,
        )
        .agg(
            product_count_num=("product_count_num", "sum"),
            example_product_names=("example_product_names", "first"),
            example_off_brands_raw=("example_off_brands_raw", "first"),
        )
        .sort_values("product_count_num", ascending=False)
    )
    for _, row in grouped.iterrows():
        company = row["target_company_owner"]
        brand = row["target_normalized_brand"]
        brand_db = row["target_primary_brand_db"]
        category = str(row["query_category"]).strip()
        regions = str(row["observed_market_region_codes"]).strip()
        key = (normalize_key(company), normalize_key(brand_db), category, regions)
        if not key[0] or not key[1] or key in existing:
            continue
        existing.add(key)
        rows.append({
            "parent_company": company,
            "brand": brand,
            "primary_brand_db": brand_db,
            "category": category,
            "hq_country": "",
            "notes": "Manually reviewed Top 9 brand-prefix orphan cleanup.",
            "ownership_resolution_status": status_from_decision(row["review_decision_clean"]),
            "market_scope": regions,
            "country_tags_include": "",
            "country_tags_exclude": "",
            "region_codes_include": regions,
            "product_scope_note": "Applied only because apply_to_mapping=True in reviewed file.",
            "normalized_brand": brand,
            "category_scope": category,
            "brand_mapping_source": SOURCE_TAG,
            "source_note": str(LOCAL_REVIEWED_PATH.relative_to(ROOT)).replace("\\", "/"),
            "review_note": (
                f"{row['review_decision_clean']}; reviewed candidate '{brand_db}' "
                f"as '{brand}'. Product count in review: {int(row['product_count_num'])}."
            ),
            "needs_manual_review": "no",
            "scope_rule_type": "reviewed_brand_prefix_orphan",
            "region_codes_exclude": "",
        })
    if rows:
        mapping_df = pd.concat([mapping_df, pd.DataFrame(rows)], ignore_index=True)
        write_csv(COMPANY_MAPPING_PATH, mapping_df)
    return len(rows)


def write_summary(
    reviewed_applied: pd.DataFrame,
    purged_alias: int,
    purged_company: int,
    added_alias: int,
    added_company: int,
) -> None:
    source = read_csv(DECISION_PATH)
    source["product_count_num"] = pd.to_numeric(
        source["product_count"], errors="coerce"
    ).fillna(0).astype(int)
    summary = (
        source.groupby(["review_decision", "apply_to_mapping", "applied_by_script"], dropna=False)
        .agg(
            review_rows=("candidate_orphan_brand", "count"),
            product_count=("product_count_num", "sum"),
        )
        .reset_index()
        .sort_values(["apply_to_mapping", "product_count"], ascending=[False, False])
    )
    metadata = pd.DataFrame([
        {
            "review_decision": "SCRIPT_METADATA",
            "apply_to_mapping": "",
            "review_rows": (
                f"purged_alias_rows={purged_alias}; purged_company_rows={purged_company}; "
                f"added_alias_rows={added_alias}; added_company_rows={added_company}; "
                f"applied_review_rows={len(reviewed_applied)}"
            ),
            "product_count": int(reviewed_applied["product_count_num"].sum()),
        }
    ])
    write_csv(SUMMARY_PATH, pd.concat([metadata, summary], ignore_index=True))


def main() -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    applied = prepare_reviewed_decisions()
    purged_alias = purge_previous_alias_rows()
    purged_company = purge_previous_company_rows()
    added_alias = append_alias_rows(applied)
    added_company = append_company_rows(applied)
    write_summary(applied, purged_alias, purged_company, added_alias, added_company)

    print(f"Copied reviewed input -> {LOCAL_REVIEWED_PATH}")
    print(f"Wrote applied-decision audit -> {DECISION_PATH}")
    print(f"Wrote apply summary -> {SUMMARY_PATH}")
    print(f"Purged previous alias rows from this source: {purged_alias}")
    print(f"Purged previous company rows from this source: {purged_company}")
    print(f"Applied review rows: {len(applied)}")
    print(f"Applied products: {int(applied['product_count_num'].sum())}")
    print(f"Alias rows added: {added_alias}")
    print(f"Company mapping rows added: {added_company}")


if __name__ == "__main__":
    main()
