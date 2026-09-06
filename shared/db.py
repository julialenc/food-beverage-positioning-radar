"""
Read-only SQLite access for the Streamlit app.
"""

from __future__ import annotations

import gzip
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from shared.beverage_segments import beverage_view_segment

REPO_ROOT        = Path(__file__).resolve().parent.parent
LOCAL_DB_PATH    = REPO_ROOT / "database" / "positioning_radar.db"
PUBLIC_DB_PATH   = REPO_ROOT / "database" / "positioning_radar_public_mvp.db"
PUBLIC_DB_GZ_PATH = REPO_ROOT / "database" / "positioning_radar_public_mvp.db.gz"
COMPANY_MAP_PATH = REPO_ROOT / "data" / "reference" / "company_brand_mapping.csv"
PRODUCT_MAPPING_OVERRIDE_PATH = (
    REPO_ROOT / "data" / "reference" / "reviewed_product_mapping_overrides.csv"
)
REGION_MAP_PATH  = REPO_ROOT / "data" / "country_region_mapping.csv"

DOWNLOAD_SCOPE_REGIONS = {"FRANCE", "UK_IE", "US_CANADA"}
COMPANY_OTHER_LABEL    = "Other / not mapped to a company"
COMPANY_MANUAL_REVIEW_LABEL = "Manual review"
PRODUCT_BRAND_SQL = "COALESCE(NULLIF(TRIM(p.normalized_brand), ''), p.primary_brand)"
PRODUCT_BRAND_SQL_UNALIASED = "COALESCE(NULLIF(TRIM(normalized_brand), ''), primary_brand)"
CURRENT_PRODUCT_SQL = "p.ingested_at = (SELECT MAX(ingested_at) FROM products)"
CURRENT_PRODUCT_SQL_UNALIASED = "ingested_at = (SELECT MAX(ingested_at) FROM products)"
CHART_BAND_COLUMNS = {
    "energy_kcal": "energy_chart_band",
    "protein_100g": "protein_chart_band",
    "fat_100g": "fat_chart_band",
    "saturated_fat_100g": "saturated_fat_chart_band",
    "carbs_100g": "carbs_chart_band",
    "sugars_100g": "sugars_chart_band",
    "fiber_100g": "fiber_chart_band",
    "salt_100g": "salt_chart_band",
    "protein_per_kcal": "protein_per_kcal_chart_band",
    "satfat_per_kcal": "satfat_per_kcal_chart_band",
    "fiber_per_kcal": "fiber_per_kcal_chart_band",
    "sugars_per_kcal": "sugars_per_kcal_chart_band",
}


def _extracted_public_db_path() -> Path:
    return Path(tempfile.gettempdir()) / "positioning_radar_public_mvp.db"


def _extract_public_db_if_needed() -> Path:
    extracted = _extracted_public_db_path()
    gz_mtime = PUBLIC_DB_GZ_PATH.stat().st_mtime
    needs_extract = (
        not extracted.exists()
        or extracted.stat().st_mtime < gz_mtime
        or extracted.stat().st_size == 0
    )
    if needs_extract:
        with gzip.open(PUBLIC_DB_GZ_PATH, "rb") as src:
            with open(extracted, "wb") as dst:
                shutil.copyfileobj(src, dst)
        os.utime(extracted, (gz_mtime, gz_mtime))
    return extracted


def get_database_path() -> Path:
    configured = os.environ.get("POSITIONING_RADAR_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    if LOCAL_DB_PATH.exists():
        return LOCAL_DB_PATH
    if PUBLIC_DB_PATH.exists():
        return PUBLIC_DB_PATH
    if PUBLIC_DB_GZ_PATH.exists():
        return _extract_public_db_if_needed()
    return LOCAL_DB_PATH


def database_exists() -> bool:
    return get_database_path().exists()


def database_display_path() -> str:
    path = get_database_path()
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


@st.cache_resource(show_spinner=False)
def get_connection() -> sqlite3.Connection:
    db_path = get_database_path()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(show_spinner=False)
def get_company_mapping_rows() -> list[dict[str, str]]:
    import csv
    if not COMPANY_MAP_PATH.exists():
        return []
    rows: list[dict[str, str]] = []
    with open(COMPANY_MAP_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            company = row.get("parent_company", "").strip()
            brand = row.get("primary_brand_db", "").strip()
            if not company or not brand:
                continue
            rows.append({
                "parent_company": company,
                "primary_brand_db": brand,
                "brand_norm": _normalize_brand(brand),
                "status": (row.get("ownership_resolution_status", "").strip().lower()
                           or "direct"),
                "needs_manual_review": row.get("needs_manual_review", "").strip().lower(),
                "country_tags_include": row.get("country_tags_include", "").strip(),
                "country_tags_exclude": row.get("country_tags_exclude", "").strip(),
                "region_codes_include": row.get("region_codes_include", "").strip(),
                "region_codes_exclude": row.get("region_codes_exclude", "").strip(),
            })
    return rows


@st.cache_data(show_spinner=False)
def get_company_brand_map() -> dict[str, list[str]]:
    """Company -> brand list for the Product Explorer sidebar.

    This is intentionally conservative: scoped/manual-review duplicate
    ownership keys are not exposed as ordinary company-brand pairs here,
    because Product Explorer currently passes only selected brand strings
    back into the SQL filter, not the company context needed to resolve
    market-scoped ownership. Row-level ownership resolution is handled by
    resolve_company_owner() and get_market_products().
    """
    from collections import defaultdict
    mapping: dict[str, set[str]] = defaultdict(set)
    for brand_rows in get_company_mapping_index().values():
        brand = brand_rows[0]["primary_brand_db"]
        direct_rows = [
            r for r in brand_rows
            if r["status"] in {
                "direct",
                "recently_demerged",
                "recently_sold_or_spun_off",
                "licensed_or_partnered",
            }
            and r.get("needs_manual_review") != "yes"
            and r["parent_company"].lower() != COMPANY_MANUAL_REVIEW_LABEL.lower()
        ]
        scoped_or_review = [
            r for r in brand_rows
            if r["status"] in {
                "market_scoped",
                "manual_review",
            }
            or r.get("needs_manual_review") == "yes"
            or r["parent_company"].lower() == COMPANY_MANUAL_REVIEW_LABEL.lower()
        ]

        direct_companies = sorted({r["parent_company"] for r in direct_rows})
        if not scoped_or_review and len(direct_companies) == 1:
            mapping[direct_companies[0]].add(brand)
        elif scoped_or_review:
            mapping[COMPANY_MANUAL_REVIEW_LABEL].add(brand)

    return {company: sorted(brands) for company, brands in mapping.items()}


@st.cache_data(show_spinner=False)
def get_company_mapping_index() -> dict[str, list[dict[str, str]]]:
    from collections import defaultdict
    by_brand: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in get_company_mapping_rows():
        by_brand[row["brand_norm"]].append(row)
    return dict(by_brand)


@st.cache_data(show_spinner=False)
def get_company_options() -> list[str]:
    return sorted({
        row["parent_company"]
        for row in get_company_mapping_rows()
        if row["parent_company"] != COMPANY_MANUAL_REVIEW_LABEL
    })


@st.cache_data(show_spinner=False)
def get_reviewed_product_mapping_overrides() -> dict[str, list[dict[str, str]]]:
    import csv
    if not PRODUCT_MAPPING_OVERRIDE_PATH.exists():
        return {}
    overrides: dict[str, list[dict[str, str]]] = {}
    with open(PRODUCT_MAPPING_OVERRIDE_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            status = row.get("status", "").strip().lower()
            barcode = row.get("gtin", "").strip()
            if status != "active" or not barcode:
                continue
            overrides.setdefault(barcode, []).append({
                "region": row.get("region", "").strip(),
                "brand": row.get("reviewed_brand", "").strip(),
                "company": row.get("reviewed_company", "").strip(),
                "category": row.get("reviewed_category", "").strip(),
            })
    return overrides


def _reviewed_product_override_for_row(
    barcode: str,
    row_region_codes: str,
    selected_region_codes: Optional[list[str]],
    overrides: Optional[dict[str, list[dict[str, str]]]] = None,
) -> Optional[dict[str, str]]:
    if overrides is None:
        overrides = get_reviewed_product_mapping_overrides()
    candidates = overrides.get(str(barcode or "").strip()) or []
    if not candidates:
        return None
    selected = [code for code in (selected_region_codes or []) if code]
    context = set(selected) if selected else {
        code.strip() for code in str(row_region_codes or "").split("|") if code.strip()
    }
    unscoped = None
    for candidate in candidates:
        region = candidate.get("region", "")
        if not region:
            unscoped = candidate
            continue
        if region in context:
            return candidate
    return unscoped


def _apply_reviewed_product_overrides_for_display(
    df: pd.DataFrame,
    selected_region_codes: Optional[list[str]] = None,
) -> pd.DataFrame:
    if df.empty or "barcode" not in df.columns:
        return df
    out = df.copy()
    overrides = get_reviewed_product_mapping_overrides()
    if not overrides:
        return out
    row_regions = out.get("observed_market_region_codes", pd.Series("", index=out.index))
    row_regions = row_regions.fillna("").astype(str)
    for idx, barcode in out["barcode"].fillna("").astype(str).items():
        override = _reviewed_product_override_for_row(
            barcode,
            row_regions.loc[idx],
            selected_region_codes,
            overrides,
        )
        if not override:
            continue
        category = override.get("category", "")
        if "query_category" in out.columns:
            if category == "OUT_OF_SCOPE":
                out.at[idx, "query_category"] = None
            elif category:
                out.at[idx, "query_category"] = category
        brand = override.get("brand", "")
        if brand:
            if "normalized_brand" in out.columns:
                out.at[idx, "normalized_brand"] = brand
            if "primary_brand" in out.columns:
                out.at[idx, "primary_brand"] = brand
        company = override.get("company", "")
        if company:
            out.at[idx, "company"] = company
            if "resolved_company" in out.columns:
                out.at[idx, "resolved_company"] = company
    return out


def _split_scope_values(value: str) -> list[str]:
    return [v.strip() for v in str(value or "").split("|") if v.strip()]


def _any_token_match(source_value: str, tokens: list[str]) -> bool:
    if not tokens:
        return False
    source_tokens = {v.strip().lower() for v in str(source_value or "").split("|") if v.strip()}
    return any(token.lower() in source_tokens for token in tokens)


def _row_scope_matches(row: dict[str, str], countries: str, region_codes: str) -> bool:
    include_regions = _split_scope_values(row.get("region_codes_include", ""))
    exclude_regions = _split_scope_values(row.get("region_codes_exclude", ""))
    include_countries = _split_scope_values(row.get("country_tags_include", ""))
    exclude_countries = _split_scope_values(row.get("country_tags_exclude", ""))

    # A market-scoped row with no structured scope is a documented caveat,
    # not a resolvable rule. Keep it out of automatic attribution.
    if not include_regions and not include_countries:
        return False
    if exclude_regions and _any_token_match(region_codes, exclude_regions):
        return False
    if exclude_countries and _any_token_match(countries, exclude_countries):
        return False

    region_ok = _any_token_match(region_codes, include_regions)
    country_ok = _any_token_match(countries, include_countries)
    return region_ok or country_ok


def resolve_company_owner(brand: str, countries: str = "",
                          region_codes: str = "") -> str:
    """Resolve brand ownership for one product row.

    This follows docs/BRAND_COMPANY_MAPPING.md's priority order: scoped
    rows are evaluated first, manual-review rows are used as fallbacks,
    direct rows are used only when there is no scoped conflict.
    """
    brand_norm = _normalize_brand(brand or "")
    if not brand_norm:
        return COMPANY_OTHER_LABEL

    rows = get_company_mapping_index().get(brand_norm, [])
    if not rows:
        return COMPANY_OTHER_LABEL

    scoped = [
        r for r in rows
        if r["status"] in {"market_scoped", "licensed_or_partnered"}
        and r.get("needs_manual_review") != "yes"
        and (
            r.get("region_codes_include")
            or r.get("country_tags_include")
            or r.get("region_codes_exclude")
            or r.get("country_tags_exclude")
        )
    ]
    manual = [
        r for r in rows
        if r["status"] == "manual_review"
        or r.get("needs_manual_review") == "yes"
        or r["parent_company"].lower() == COMPANY_MANUAL_REVIEW_LABEL.lower()
    ]
    direct = [
        r for r in rows
        if r["status"] in {
            "direct",
            "recently_demerged",
            "recently_sold_or_spun_off",
            "licensed_or_partnered",
        }
        and r.get("needs_manual_review") != "yes"
        and r["parent_company"].lower() != COMPANY_MANUAL_REVIEW_LABEL.lower()
    ]

    if scoped:
        matches = [r for r in scoped if _row_scope_matches(r, countries, region_codes)]
        companies = sorted({r["parent_company"] for r in matches})
        if len(companies) == 1:
            return companies[0]
        return COMPANY_MANUAL_REVIEW_LABEL if manual or scoped else COMPANY_OTHER_LABEL

    direct_companies = sorted({r["parent_company"] for r in direct})
    if len(direct_companies) == 1:
        return direct_companies[0]
    if len(direct_companies) > 1 or manual:
        return COMPANY_MANUAL_REVIEW_LABEL
    return COMPANY_OTHER_LABEL


def _resolution_region_context(row_region_codes: str,
                               selected_region_codes: Optional[list[str]]) -> str:
    selected = [code for code in (selected_region_codes or []) if code]
    if len(selected) == 1:
        return selected[0]
    if len(selected) > 1:
        return "|".join(selected)
    return row_region_codes or ""


def add_resolved_company(
    df: pd.DataFrame,
    selected_region_codes: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Return a copy with resolver-derived company / owner attribution."""
    out = df.copy()
    if out.empty:
        out["company"] = pd.Series(dtype="object")
        return out

    selected = [code for code in (selected_region_codes or []) if code]
    if len(selected) == 1:
        out["_resolution_region_context"] = selected[0]
    elif len(selected) > 1:
        out["_resolution_region_context"] = "|".join(selected)
    else:
        out["_resolution_region_context"] = out.get("observed_market_region_codes", "")

    key_cols = ["primary_brand", "countries", "_resolution_region_context"]
    unique_keys = out[key_cols].drop_duplicates()
    resolved = {
        tuple(row): resolve_company_owner(
            row[0],
            countries=row[1],
            region_codes=row[2],
        )
        for row in unique_keys.itertuples(index=False, name=None)
    }
    out["company"] = [
        resolved.get((brand, countries, region_ctx), COMPANY_OTHER_LABEL)
        for brand, countries, region_ctx in out[key_cols].itertuples(index=False, name=None)
    ]
    out = out.drop(columns=["_resolution_region_context"])
    return _apply_reviewed_product_overrides_for_display(out, selected_region_codes)


def _apply_display_brand(df: pd.DataFrame) -> pd.DataFrame:
    """Expose normalized_brand through primary_brand for UI compatibility."""
    if df.empty or "primary_brand" not in df.columns or "normalized_brand" not in df.columns:
        return df
    normalized = df["normalized_brand"].astype("string").str.strip()
    df["primary_brand"] = normalized.where(normalized.notna() & (normalized != ""), df["primary_brand"])
    if "resolved_company" in df.columns:
        df["company"] = df["resolved_company"]
    return df


def filter_products_by_company(
    df: pd.DataFrame,
    company_names: Optional[list[str]],
    selected_region_codes: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Filter products by resolved company / owner label."""
    selected = {c for c in (company_names or []) if c}
    if not selected:
        return add_resolved_company(df, selected_region_codes)

    resolved = add_resolved_company(df, selected_region_codes)
    return resolved[resolved["company"].isin(selected)]


@st.cache_data(show_spinner=False)
def get_region_options() -> list[tuple[str, str]]:
    import csv
    seen: dict[str, tuple[str, int]] = {}
    if not REGION_MAP_PATH.exists():
        return []
    with open(REGION_MAP_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code  = row.get("region_code", "").strip()
            label = row.get("region_filter_label", "").strip()
            try:
                order = int(row.get("ui_order", 999))
            except ValueError:
                order = 999
            if code and code in DOWNLOAD_SCOPE_REGIONS and code not in seen:
                seen[code] = (label, order)
    return [(code, label) for code, (label, order) in
            sorted(seen.items(), key=lambda x: x[1][1])]


@st.cache_data(show_spinner=False, ttl=600)
def get_filter_options() -> dict[str, list]:
    """Distinct values for Category and Nutri-Score filters.
    Claim area and Claim focus removed — ingredient-derived taxonomy
    was unreliable; Positioning filter replaces them for vision products.
    """
    conn = get_connection()
    queries = {
        "query_category": """
            SELECT DISTINCT query_category FROM products
            WHERE ingested_at = (SELECT MAX(ingested_at) FROM products)
              AND query_category IS NOT NULL AND TRIM(query_category) != ''
            ORDER BY 1
        """,
        "nutriscore_grade": """
            SELECT DISTINCT LOWER(nutriscore_grade) FROM products
            WHERE ingested_at = (SELECT MAX(ingested_at) FROM products)
              AND nutriscore_grade IS NOT NULL AND TRIM(nutriscore_grade) != ''
            ORDER BY 1
        """,
    }
    results: dict[str, list] = {}
    for key, q in queries.items():
        try:
            results[key] = [row[0] for row in conn.execute(q).fetchall()]
        except Exception as exc:
            print(f"[get_filter_options] '{key}' query failed: {exc}")
            results[key] = []
    return results


@st.cache_data(show_spinner=False, ttl=600)
def get_brand_options(categories: tuple[str, ...] = ()) -> list[str]:
    """Brands filtered by category. Excludes brands with no alphabetic
    characters (numeric codes, symbols) that add noise to the dropdown."""
    conn = get_connection()
    try:
        if categories:
            placeholders = ",".join("?" for _ in categories)
            rows = conn.execute(f"""
                SELECT DISTINCT {PRODUCT_BRAND_SQL_UNALIASED} AS primary_brand
                FROM products
                WHERE {CURRENT_PRODUCT_SQL_UNALIASED}
                AND {PRODUCT_BRAND_SQL_UNALIASED} IS NOT NULL
                AND TRIM({PRODUCT_BRAND_SQL_UNALIASED}) != ''
                AND query_category IN ({placeholders})
                ORDER BY 1
            """, list(categories)).fetchall()
        else:
            rows = conn.execute("""
                SELECT DISTINCT COALESCE(NULLIF(TRIM(normalized_brand), ''), primary_brand) AS primary_brand
                FROM products
                WHERE ingested_at = (SELECT MAX(ingested_at) FROM products)
                AND COALESCE(NULLIF(TRIM(normalized_brand), ''), primary_brand) IS NOT NULL
                AND TRIM(COALESCE(NULLIF(TRIM(normalized_brand), ''), primary_brand)) != ''
                ORDER BY 1
            """).fetchall()
        # Filter out brands with no letter — handles Unicode (é, ñ, etc.)
        return [row[0] for row in rows if any(c.isalpha() for c in (row[0] or ""))]
    except Exception as exc:
        print(f"[get_brand_options] query failed: {exc}")
        return []


@st.cache_data(show_spinner=False, ttl=600)
def get_positioning_options() -> list[str]:
    """Distinct raw claim codes present in vision-analyzed products.
    Callers map codes to friendly names using _CLAIM_NAMES in search.py."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT DISTINCT pack_claims_found FROM product_analysis
            WHERE pack_claims_found IS NOT NULL
              AND TRIM(pack_claims_found) != ''
              AND claim_source = 'vision'
        """).fetchall()
    except Exception:
        return []
    codes: set[str] = set()
    for (val,) in rows:
        for code in str(val).split("|"):
            code = code.strip()
            if code:
                codes.add(code)
    return sorted(codes)


def _qmarks(values: list) -> str:
    return ",".join("?" for _ in values)


@st.cache_data(show_spinner=False, ttl=600)
def product_column_exists(column: str) -> bool:
    conn = get_connection()
    try:
        rows = conn.execute("PRAGMA table_info(products)").fetchall()
    except Exception:
        return False
    return column in {row[1] for row in rows}


def _normalize_brand(b: str) -> str:
    import re
    import unicodedata

    text = str(b or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = text.replace("&", " and ")
    text = re.sub(r"['`´’]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _build_where(
    text: str,
    categories: Optional[list[str]],
    brands: Optional[list[str]],
    company_brands: Optional[list[str]],
    exclude_company_brands: Optional[list[str]],
    company_names: Optional[list[str]],
    region_codes: Optional[list[str]],
    positioning_codes: Optional[list[str]],
    nova_groups: Optional[list[int]],
    nutriscore_grades: Optional[list[str]],
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []

    # Permanent: exclude no-brand and unknown-brand products
    clauses.append(CURRENT_PRODUCT_SQL)
    clauses.append(
        f"{PRODUCT_BRAND_SQL} IS NOT NULL"
        f" AND TRIM(LOWER({PRODUCT_BRAND_SQL})) NOT IN ('unknown', '', 'nan')"
    )
    if product_column_exists("include_in_product_table"):
        clauses.append("COALESCE(p.include_in_product_table, 1) = 1")

    text = str(text or "").strip()
    if text:
        clauses.append("(LOWER(p.product_name) LIKE LOWER(?) OR LOWER(p.brands) LIKE LOWER(?))")
        like = f"%{text}%"
        params.extend([like, like])
    if categories:
        clauses.append(f"p.query_category IN ({_qmarks(categories)})")
        params.extend(categories)
    if brands:
        brand_marks = _qmarks(brands)
        clauses.append(
            f"(p.normalized_brand IN ({brand_marks}) "
            f"OR ((p.normalized_brand IS NULL OR TRIM(p.normalized_brand) = '') "
            f"AND p.primary_brand IN ({brand_marks})))"
        )
        params.extend(brands)
        params.extend(brands)
    if company_brands:
        normalized = [_normalize_brand(b) for b in company_brands]
        clauses.append(
            f"LOWER(REPLACE({PRODUCT_BRAND_SQL}, '-', ' ')) IN ({_qmarks(normalized)})"
        )
        params.extend(normalized)
    if exclude_company_brands:
        normalized = [_normalize_brand(b) for b in exclude_company_brands]
        clauses.append(
            f"LOWER(REPLACE({PRODUCT_BRAND_SQL}, '-', ' ')) NOT IN ({_qmarks(normalized)})"
        )
        params.extend(normalized)
    if company_names:
        clauses.append(f"p.resolved_company IN ({_qmarks(company_names)})")
        params.extend(company_names)
    if region_codes:
        region_clause = " OR ".join(
            "p.observed_market_region_codes LIKE ?" for _ in region_codes
        )
        clauses.append(f"({region_clause})")
        params.extend(f"%{code}%" for code in region_codes)
    if positioning_codes:
        # OR logic: product must have at least one of the selected claim codes
        pos_clause = " OR ".join(
            "a.pack_claims_found LIKE ?" for _ in positioning_codes
        )
        clauses.append(f"(a.claim_source = 'vision' AND ({pos_clause}))")
        params.extend(f"%{code}%" for code in positioning_codes)
    if nova_groups:
        clauses.append(f"p.nova_group IN ({_qmarks(nova_groups)})")
        params.extend(nova_groups)
    if nutriscore_grades:
        clauses.append(f"LOWER(p.nutriscore_grade) IN ({_qmarks(nutriscore_grades)})")
        params.extend([g.lower() for g in nutriscore_grades])

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def count_products(
    text: str = "",
    categories: Optional[list[str]] = None,
    brands: Optional[list[str]] = None,
    company_brands: Optional[list[str]] = None,
    exclude_company_brands: Optional[list[str]] = None,
    company_names: Optional[list[str]] = None,
    region_codes: Optional[list[str]] = None,
    positioning_codes: Optional[list[str]] = None,
    nova_groups: Optional[list[int]] = None,
    nutriscore_grades: Optional[list[str]] = None,
) -> int:
    conn = get_connection()
    where_sql, params = _build_where(
        text, categories, brands, company_brands, exclude_company_brands,
        company_names, region_codes, positioning_codes, nova_groups,
        nutriscore_grades
    )
    join_sql = (
        "LEFT JOIN product_analysis a ON a.barcode = p.barcode"
        if positioning_codes else ""
    )
    return conn.execute(f"""
        SELECT COUNT(*)
        FROM products p
        {join_sql}
        {where_sql}
    """, params).fetchone()[0]


def search_products(
    text: str = "",
    categories: Optional[list[str]] = None,
    brands: Optional[list[str]] = None,
    company_brands: Optional[list[str]] = None,
    exclude_company_brands: Optional[list[str]] = None,
    company_names: Optional[list[str]] = None,
    region_codes: Optional[list[str]] = None,
    positioning_codes: Optional[list[str]] = None,
    nova_groups: Optional[list[int]] = None,
    nutriscore_grades: Optional[list[str]] = None,
    limit: Optional[int] = 1000,
) -> pd.DataFrame:
    conn = get_connection()
    where_sql, params = _build_where(
        text, categories, brands, company_brands, exclude_company_brands,
        company_names, region_codes, positioning_codes, nova_groups,
        nutriscore_grades
    )
    if product_column_exists("warning_types"):
        warning_select = """
            p.warning_flag,
            p.warning_types,
            p.warning_summary,
        """
    else:
        warning_select = """
            0 AS warning_flag,
            '' AS warning_types,
            '' AS warning_summary,
        """
    limit_sql = "LIMIT ?" if limit is not None else ""
    query_params = [*params, limit] if limit is not None else params
    df = pd.read_sql_query(f"""
        SELECT
            p.barcode,
            p.product_name,
            p.brands,
            p.primary_brand,
            p.normalized_brand,
            p.resolved_company,
            p.quantity,
            p.query_category,
            p.primary_country,
            p.observed_market_region_codes,
            p.image_url,
            p.ingredients_text,
            p.energy_kcal,
            p.fat_100g,
            p.saturated_fat_100g,
            p.carbs_100g,
            p.sugars_100g,
            p.fiber_100g,
            p.protein_100g,
            p.salt_100g,
            p.nutriscore_grade,
            p.nova_group,
            p.completeness_score,
            {warning_select}
            a.pack_claims_found,
            a.claim_source
        FROM products p
        LEFT JOIN product_analysis a ON a.barcode = p.barcode
        {where_sql}
        {limit_sql}
    """, conn, params=query_params)
    df = df.loc[:, ~df.columns.duplicated()]
    df = _apply_display_brand(df)
    return df


def count_products_resolved(
    text: str = "",
    categories: Optional[list[str]] = None,
    brands: Optional[list[str]] = None,
    company_names: Optional[list[str]] = None,
    region_codes: Optional[list[str]] = None,
    positioning_codes: Optional[list[str]] = None,
    nova_groups: Optional[list[int]] = None,
    nutriscore_grades: Optional[list[str]] = None,
) -> int:
    if not company_names:
        return count_products(
            text, categories, brands, None, None, None,
            region_codes, positioning_codes, nova_groups, nutriscore_grades,
        )
    df = search_products(
        text, categories, brands, None, None, None,
        region_codes, positioning_codes, nova_groups, nutriscore_grades,
        limit=None,
    )
    resolved = add_resolved_company(df, region_codes)
    return int(resolved["company"].isin(company_names).sum())


def search_products_resolved(
    text: str = "",
    categories: Optional[list[str]] = None,
    brands: Optional[list[str]] = None,
    company_names: Optional[list[str]] = None,
    region_codes: Optional[list[str]] = None,
    positioning_codes: Optional[list[str]] = None,
    nova_groups: Optional[list[int]] = None,
    nutriscore_grades: Optional[list[str]] = None,
    limit: Optional[int] = 1000,
) -> pd.DataFrame:
    if not company_names:
        df = search_products(
            text, categories, brands, None, None, None,
            region_codes, positioning_codes, nova_groups, nutriscore_grades,
            limit=limit,
        )
        return df

    df = search_products(
        text, categories, brands, None, None, None,
        region_codes, positioning_codes, nova_groups, nutriscore_grades,
        limit=None,
    )
    resolved = add_resolved_company(df, region_codes)
    filtered = resolved[resolved["company"].isin(company_names)]
    if limit is not None:
        filtered = filtered.head(limit)
    return filtered


@st.cache_data(show_spinner=False, ttl=600)
def get_market_products(category: str, region_code: str) -> pd.DataFrame:
    """The full product set for one region x one category — the shared
    dataset behind Market Overview's Product Landscape and Product Profile
    Landscape sections (spec section 10: reuse the same cleaned dataset
    used by Product Explorer, no separate analytical source).

    Returns raw per-100g/100ml nutrition fields plus derived per-100kcal
    fields (protein/fiber/satfat/sugars), and the materialized `company`
    column from the current SQLite snapshot.
    Company/brand narrowing happens client-side on this cached frame,
    not via separate SQL calls, since a single region x category
    population is small enough to hold in memory (tens of thousands of
    rows, not millions).
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT p.barcode, p.product_name,
               COALESCE(NULLIF(TRIM(p.normalized_brand), ''), p.primary_brand) AS primary_brand,
               p.primary_brand AS legacy_primary_brand,
               p.normalized_brand, p.brand_entity_raw, p.brand_entity_source,
               p.primary_country, p.image_url,
               p.countries, p.observed_market_region_codes,
               p.resolved_company,
               p.off_categories,
               p.ingredients_text, p.completeness_score,
               p.energy_kcal, p.fat_100g, p.saturated_fat_100g, p.carbs_100g,
               p.sugars_100g, p.fiber_100g, p.protein_100g, p.salt_100g,
               p.nova_group, p.nutriscore_grade,
               p.include_in_product_table, p.include_in_aggregates, p.include_in_charts,
               b.energy_chart_band, b.protein_chart_band, b.fat_chart_band,
               b.saturated_fat_chart_band, b.carbs_chart_band,
               b.sugars_chart_band, b.fiber_chart_band, b.salt_chart_band,
               b.protein_per_kcal_chart_band, b.satfat_per_kcal_chart_band,
               b.fiber_per_kcal_chart_band, b.sugars_per_kcal_chart_band
        FROM products p
        LEFT JOIN market_chart_bands b
          ON b.barcode = p.barcode
         AND b.region_code = ?
         AND b.category = p.query_category
         AND b.snapshot = (SELECT MAX(snapshot) FROM market_chart_bands)
        WHERE p.query_category = ?
          AND p.observed_market_region_codes LIKE ?
          AND p.ingested_at = (SELECT MAX(ingested_at) FROM products)
          AND COALESCE(p.include_in_product_table, 1) = 1
          AND COALESCE(NULLIF(TRIM(p.normalized_brand), ''), p.primary_brand) IS NOT NULL
          AND TRIM(LOWER(COALESCE(NULLIF(TRIM(p.normalized_brand), ''), p.primary_brand))) NOT IN ('unknown', '', 'nan')
    """, conn, params=[region_code, category, f"%{region_code}%"])

    for col in ["energy_kcal", "fat_100g", "saturated_fat_100g", "carbs_100g",
                "sugars_100g", "fiber_100g", "protein_100g", "salt_100g"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Per-100kcal derived metrics. Only defined where energy_kcal is a
    # valid positive number — a product with zero/missing energy cannot
    # receive a per-100kcal metric (spec section 12).
    valid_energy = df["energy_kcal"].notna() & (df["energy_kcal"] > 0)
    kcal = df["energy_kcal"].where(valid_energy)
    df["protein_per_kcal"] = (df["protein_100g"]       / kcal * 100).where(valid_energy)
    df["fiber_per_kcal"]   = (df["fiber_100g"]         / kcal * 100).where(valid_energy)
    df["satfat_per_kcal"]  = (df["saturated_fat_100g"] / kcal * 100).where(valid_energy)
    df["sugars_per_kcal"]  = (df["sugars_100g"]        / kcal * 100).where(valid_energy)

    if category == "beverages":
        df["beverage_view_segment"] = [
            beverage_view_segment(category, name, off_categories)
            for name, off_categories in df[
                ["product_name", "off_categories"]
            ].itertuples(index=False, name=None)
        ]
    else:
        df["beverage_view_segment"] = "not_beverage"

    df = _apply_display_brand(df)
    df = _apply_reviewed_product_overrides_for_display(df, [region_code])
    if "query_category" in df.columns:
        df = df[df["query_category"].fillna("").eq(category)].copy()
    return df


@st.cache_data(show_spinner=False, ttl=600)
def get_region_category_benchmarks() -> pd.DataFrame:
    """All 12 region x category rows for the latest snapshot, for By
    Region. Lookup only — computed by
    pipeline/compute_region_benchmarks.py. Empty DataFrame if the table
    doesn't exist yet or no snapshot is found."""
    conn = get_connection()
    try:
        snapshot = conn.execute(
            "SELECT MAX(snapshot) FROM region_category_benchmarks"
        ).fetchone()[0]
        if snapshot is None:
            return pd.DataFrame()
        return pd.read_sql_query(
            "SELECT * FROM region_category_benchmarks WHERE snapshot = ?",
            conn, params=[snapshot],
        )
    except Exception as exc:
        print(f"[get_region_category_benchmarks] query failed: {exc}")
        return pd.DataFrame()


@st.cache_data(show_spinner=False, ttl=600)
def get_profile_intersections(region_code: str, category: str,
                               full_subset_key: str) -> dict[str, tuple[int, int]]:
    """Lookup, not calculation — reads pipeline/compute_profile_intersections.py's
    precomputed table for the latest snapshot. Returns
    {sub_collection_key: (eligible_count, matching_count)} for every
    sub_collection stored under this full_subset_key. Empty dict if the
    table doesn't exist yet (script not run) or no snapshot is found."""
    conn = get_connection()
    try:
        snapshot = conn.execute(
            "SELECT MAX(snapshot) FROM profile_intersections"
        ).fetchone()[0]
        if snapshot is None:
            return {}
        rows = conn.execute("""
            SELECT sub_collection_key, eligible_count, matching_count
            FROM profile_intersections
            WHERE snapshot = ? AND region_code = ? AND category = ?
              AND full_subset_key = ?
        """, (snapshot, region_code, category, full_subset_key)).fetchall()
        return {r[0]: (r[1], r[2]) for r in rows}
    except Exception as exc:
        print(f"[get_profile_intersections] query failed: {exc}")
        return {}


@st.cache_data(show_spinner=False, ttl=600)
def get_category_region_averages() -> dict:
    """Precompute IS-table nutritional averages by (query_category, region).
    metric keys: energy_kcal, protein_per_kcal, fiber_per_kcal,
                 satfat_per_kcal, sugars_per_kcal
    """
    conn = get_connection()
    metrics = ['energy_kcal', 'protein_per_kcal', 'fiber_per_kcal',
               'satfat_per_kcal', 'sugars_per_kcal',
               'sugars_100g', 'salt_100g']
    result: dict = {}
    try:
        snapshot = conn.execute(
            "SELECT MAX(snapshot) FROM category_region_averages"
        ).fetchone()[0]
        if snapshot is None:
            return {}
        rows = conn.execute(
            """
            SELECT query_category, region, energy_kcal, protein_per_kcal,
                   fiber_per_kcal, satfat_per_kcal, sugars_per_kcal,
                   sugars_100g, salt_100g
            FROM category_region_averages
            WHERE snapshot = ?
            """,
            (snapshot,),
        ).fetchall()
    except Exception as exc:
        print(f"[get_category_region_averages] lookup failed: {exc}")
        return {}

    for row in rows:
        cat, region = str(row[0]), str(row[1])
        result[(cat, region)] = {
            metric: float(value)
            for metric, value in zip(metrics, row[2:])
            if value is not None
        }

    return result


@st.cache_data(show_spinner=False, ttl=600)
def get_axis_range_config() -> pd.DataFrame:
    """Latest precomputed Market Overview chart bounds."""
    conn = get_connection()
    try:
        snapshot = conn.execute(
            "SELECT MAX(snapshot) FROM axis_range_config"
        ).fetchone()[0]
        if snapshot is None:
            return pd.DataFrame()
        return pd.read_sql_query(
            """
            SELECT region_code, category, beverage_view_segment, metric_key,
                   p03, p97, n_valid, n_below_p03, n_above_p97, n_trimmed
            FROM axis_range_config
            WHERE snapshot = ?
            """,
            conn,
            params=[snapshot],
        )
    except Exception as exc:
        print(f"[get_axis_range_config] lookup failed: {exc}")
        return pd.DataFrame()
