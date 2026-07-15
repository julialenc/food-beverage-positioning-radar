"""
Read-only SQLite access for the Streamlit app.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

REPO_ROOT        = Path(__file__).resolve().parent.parent
DB_PATH          = REPO_ROOT / "database" / "positioning_radar.db"
COMPANY_MAP_PATH = REPO_ROOT / "data" / "reference" / "company_brand_mapping.csv"
REGION_MAP_PATH  = REPO_ROOT / "data" / "country_region_mapping.csv"

DOWNLOAD_SCOPE_REGIONS = {"FRANCE", "UK_IE", "US_CANADA"}
COMPANY_OTHER_LABEL    = "Other / not mapped to a company"


def database_exists() -> bool:
    return DB_PATH.exists()


@st.cache_resource(show_spinner=False)
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(show_spinner=False)
def get_company_brand_map() -> dict[str, list[str]]:
    import csv
    from collections import defaultdict
    mapping: dict[str, list[str]] = defaultdict(list)
    if not COMPANY_MAP_PATH.exists():
        return {}
    with open(COMPANY_MAP_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            company = row.get("parent_company", "").strip()
            brand   = row.get("primary_brand_db", "").strip()
            if company and brand:
                mapping[company].append(brand)
    return dict(mapping)


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
            WHERE query_category IS NOT NULL AND TRIM(query_category) != ''
            ORDER BY 1
        """,
        "nutriscore_grade": """
            SELECT DISTINCT LOWER(nutriscore_grade) FROM products
            WHERE nutriscore_grade IS NOT NULL AND TRIM(nutriscore_grade) != ''
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
                SELECT DISTINCT primary_brand FROM products
                WHERE primary_brand IS NOT NULL AND TRIM(primary_brand) != ''
                AND query_category IN ({placeholders})
                ORDER BY 1
            """, list(categories)).fetchall()
        else:
            rows = conn.execute("""
                SELECT DISTINCT primary_brand FROM products
                WHERE primary_brand IS NOT NULL AND TRIM(primary_brand) != ''
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


def _normalize_brand(b: str) -> str:
    return b.lower().replace("-", " ")


def _build_where(
    text: str,
    categories: Optional[list[str]],
    brands: Optional[list[str]],
    company_brands: Optional[list[str]],
    exclude_company_brands: Optional[list[str]],
    region_codes: Optional[list[str]],
    positioning_codes: Optional[list[str]],
    nova_groups: Optional[list[int]],
    nutriscore_grades: Optional[list[str]],
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []

    # Permanent: exclude no-brand and unknown-brand products
    clauses.append(
        "p.primary_brand IS NOT NULL"
        " AND TRIM(LOWER(p.primary_brand)) NOT IN ('unknown', '', 'nan')"
    )

    if text:
        clauses.append("(LOWER(p.product_name) LIKE LOWER(?) OR LOWER(p.brands) LIKE LOWER(?))")
        like = f"%{text}%"
        params.extend([like, like])
    if categories:
        clauses.append(f"p.query_category IN ({_qmarks(categories)})")
        params.extend(categories)
    if brands:
        clauses.append(f"p.primary_brand IN ({_qmarks(brands)})")
        params.extend(brands)
    if company_brands:
        normalized = [_normalize_brand(b) for b in company_brands]
        clauses.append(
            f"LOWER(REPLACE(p.primary_brand, '-', ' ')) IN ({_qmarks(normalized)})"
        )
        params.extend(normalized)
    if exclude_company_brands:
        normalized = [_normalize_brand(b) for b in exclude_company_brands]
        clauses.append(
            f"LOWER(REPLACE(p.primary_brand, '-', ' ')) NOT IN ({_qmarks(normalized)})"
        )
        params.extend(normalized)
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
    region_codes: Optional[list[str]] = None,
    positioning_codes: Optional[list[str]] = None,
    nova_groups: Optional[list[int]] = None,
    nutriscore_grades: Optional[list[str]] = None,
) -> int:
    conn = get_connection()
    where_sql, params = _build_where(
        text, categories, brands, company_brands, exclude_company_brands,
        region_codes, positioning_codes, nova_groups, nutriscore_grades
    )
    return conn.execute(f"""
        SELECT COUNT(*)
        FROM products p
        LEFT JOIN product_analysis a ON a.barcode = p.barcode
        {where_sql}
    """, params).fetchone()[0]


def search_products(
    text: str = "",
    categories: Optional[list[str]] = None,
    brands: Optional[list[str]] = None,
    company_brands: Optional[list[str]] = None,
    exclude_company_brands: Optional[list[str]] = None,
    region_codes: Optional[list[str]] = None,
    positioning_codes: Optional[list[str]] = None,
    nova_groups: Optional[list[int]] = None,
    nutriscore_grades: Optional[list[str]] = None,
    limit: int = 1000,
) -> pd.DataFrame:
    conn = get_connection()
    where_sql, params = _build_where(
        text, categories, brands, company_brands, exclude_company_brands,
        region_codes, positioning_codes, nova_groups, nutriscore_grades
    )
    df = pd.read_sql_query(f"""
        SELECT p.*, a.*
        FROM products p
        LEFT JOIN product_analysis a ON a.barcode = p.barcode
        {where_sql}
        ORDER BY p.product_name ASC
        LIMIT ?
    """, conn, params=[*params, limit])
    df = df.loc[:, ~df.columns.duplicated()]
    return df


@st.cache_data(show_spinner=False, ttl=600)
def get_category_region_averages() -> dict:
    """Precompute IS-table nutritional averages by (query_category, region).
    metric keys: energy_kcal, protein_per_kcal, fiber_per_kcal,
                 satfat_per_kcal, sugars_per_kcal
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT query_category, primary_country,
               energy_kcal, protein_100g, fiber_100g,
               saturated_fat_100g, sugars_100g, salt_100g
        FROM products
        WHERE primary_brand IS NOT NULL
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
          AND energy_kcal IS NOT NULL
          AND CAST(energy_kcal AS REAL) > 0
    """, conn)

    _COUNTRY_REGION = {
        'France': 'FRANCE',
        'United Kingdom': 'UK_IE', 'Great Britain': 'UK_IE',
        'Ireland': 'UK_IE', 'England': 'UK_IE', 'Scotland': 'UK_IE',
        'United States': 'US_CANADA', 'Canada': 'US_CANADA',
    }
    df['region'] = df['primary_country'].map(_COUNTRY_REGION).fillna('OTHER')

    for col in ['energy_kcal', 'protein_100g', 'fiber_100g',
                'saturated_fat_100g', 'sugars_100g', 'salt_100g']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    kcal = df['energy_kcal']
    df['protein_per_kcal'] = df['protein_100g']       / kcal * 100
    df['fiber_per_kcal']   = df['fiber_100g']         / kcal * 100
    df['satfat_per_kcal']  = df['saturated_fat_100g'] / kcal * 100
    df['sugars_per_kcal']  = df['sugars_100g']        / kcal * 100

    metrics = ['energy_kcal', 'protein_per_kcal', 'fiber_per_kcal',
               'satfat_per_kcal', 'sugars_per_kcal',
               'sugars_100g', 'salt_100g']
    result: dict = {}

    for (cat, region), grp in df.groupby(['query_category', 'region']):
        avgs = {}
        for m in metrics:
            valid = grp[m].dropna()
            if len(valid) >= 10:
                avgs[m] = float(valid.mean())
        result[(str(cat), str(region))] = avgs

    for cat, grp in df.groupby('query_category'):
        avgs = {}
        for m in metrics:
            valid = grp[m].dropna()
            if len(valid) >= 10:
                avgs[m] = float(valid.mean())
        result[(str(cat), 'ALL')] = avgs

    return result
