"""
Read-only SQLite access for the Streamlit app.

Connects to database/positioning_radar.db — gitignored, built locally
by running the pipeline (see README "How to run"). This app never
writes to the database; the connection is opened read-only (mode=ro)
so a bug here can't accidentally corrupt pipeline output.
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

# Regions for which we have full-coverage data (bootstrapped from OFF bulk export
# filtered to these markets). Only these appear in the Market / region filter.
# When adding a new market (e.g. DACH after a German bootstrap run), add the
# region code here — nothing else in the UI needs to change.
DOWNLOAD_SCOPE_REGIONS = {"FRANCE", "UK_IE", "US_CANADA"}

# Sentinel label for brands not mapped to any parent company.
COMPANY_OTHER_LABEL = "Other / not mapped to a company"


def database_exists() -> bool:
    return DB_PATH.exists()


@st.cache_resource(show_spinner=False)
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(show_spinner=False)
def get_company_brand_map() -> dict[str, list[str]]:
    """Load company_brand_mapping.csv → {parent_company: [primary_brand_db, ...]}."""
    import csv
    from collections import defaultdict
    mapping: dict[str, list[str]] = defaultdict(list)
    if not COMPANY_MAP_PATH.exists():
        print(f"[get_company_brand_map] file not found: {COMPANY_MAP_PATH}")
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
    """Return (region_code, label) tuples ordered by ui_order,
    restricted to DOWNLOAD_SCOPE_REGIONS so the UI only offers markets
    for which we have full coverage. Products sold in other markets still
    exist in the DB — they just aren't filterable by region."""
    import csv
    seen: dict[str, tuple[str, int]] = {}
    if not REGION_MAP_PATH.exists():
        print(f"[get_region_options] file not found: {REGION_MAP_PATH}")
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
    """Distinct values for claim area, claim focus, and Nutri-Score filters.
    Brand and Category are handled by get_brand_options() since brand
    options are now category-dependent.
    """
    conn = get_connection()
    queries = {
        "query_category": """
            SELECT DISTINCT query_category FROM products
            WHERE query_category IS NOT NULL AND TRIM(query_category) != ''
            ORDER BY 1
        """,
        "claim_category_1": """
            SELECT DISTINCT claim_category_1 FROM product_analysis
            WHERE claim_category_1 IS NOT NULL AND TRIM(claim_category_1) != ''
            ORDER BY 1
        """,
        "claim_category_2": """
            SELECT DISTINCT claim_category_2 FROM product_analysis
            WHERE claim_category_2 IS NOT NULL
              AND TRIM(claim_category_2) != ''
              AND TRIM(LOWER(claim_category_2)) NOT IN ('none', 'nan')
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
    """Brands present in the DB, optionally filtered to selected categories.
    Uses tuple (not list) so Streamlit can hash it as a cache key.
    Called with the current category selection so the Brand dropdown only
    shows brands that exist in the chosen categories."""
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
        return [row[0] for row in rows]
    except Exception as exc:
        print(f"[get_brand_options] query failed: {exc}")
        return []


def _qmarks(values: list) -> str:
    return ",".join("?" for _ in values)


def _normalize_brand(b: str) -> str:
    """Canonical form for brand comparison: lowercase, hyphens → spaces."""
    return b.lower().replace("-", " ")


def _build_where(
    text: str,
    categories: Optional[list[str]],
    brands: Optional[list[str]],
    company_brands: Optional[list[str]],
    exclude_company_brands: Optional[list[str]],
    region_codes: Optional[list[str]],
    claim_areas: Optional[list[str]],
    claim_focuses: Optional[list[str]],
    nova_groups: Optional[list[int]],
    nutriscore_grades: Optional[list[str]],
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []

    # Always exclude products with no usable brand — these are typically
    # unbranded, private-label-unlabelled, or contributor-entry artefacts
    # where primary_brand is NULL or the literal string 'unknown' (written
    # by clean.py when the OFF brands field was empty). They have no
    # analytical value in the Product Explorer but are retained in the DB
    # for Ozempic tracker and other aggregate computations that read the
    # full products table directly.
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
        # Direct brand filter (used when no company context, or under "Other")
        clauses.append(f"p.primary_brand IN ({_qmarks(brands)})")
        params.extend(brands)
    if company_brands:
        # Company-expanded brand filter — normalized to handle hyphen variants
        normalized = [_normalize_brand(b) for b in company_brands]
        clauses.append(
            f"LOWER(REPLACE(p.primary_brand, '-', ' ')) IN ({_qmarks(normalized)})"
        )
        params.extend(normalized)
    if exclude_company_brands:
        # "Other" bucket: products whose brand is NOT mapped to any company
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
    if claim_areas:
        clauses.append(f"a.claim_category_1 IN ({_qmarks(claim_areas)})")
        params.extend(claim_areas)
    if claim_focuses:
        clauses.append(f"a.claim_category_2 IN ({_qmarks(claim_focuses)})")
        params.extend(claim_focuses)
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
    claim_areas: Optional[list[str]] = None,
    claim_focuses: Optional[list[str]] = None,
    nova_groups: Optional[list[int]] = None,
    nutriscore_grades: Optional[list[str]] = None,
) -> int:
    conn = get_connection()
    where_sql, params = _build_where(
        text, categories, brands, company_brands, exclude_company_brands,
        region_codes, claim_areas, claim_focuses, nova_groups, nutriscore_grades
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
    claim_areas: Optional[list[str]] = None,
    claim_focuses: Optional[list[str]] = None,
    nova_groups: Optional[list[int]] = None,
    nutriscore_grades: Optional[list[str]] = None,
    limit: int = 200,
) -> pd.DataFrame:
    """Products matching all filters, left-joined with their analysis row.
    Capped at `limit` rows — pair with count_products() to show totals."""
    conn = get_connection()
    where_sql, params = _build_where(
        text, categories, brands, company_brands, exclude_company_brands,
        region_codes, claim_areas, claim_focuses, nova_groups, nutriscore_grades
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
    """
    Precompute IS-table nutritional averages by (query_category, region)
    and (query_category, 'ALL') as fallback. Called once per session,
    cached for 10 minutes. Excludes unknown/null-brand products so averages
    reflect the same universe shown in the table.

    Returns {(category, region_or_ALL): {metric_key: float_avg}}.
    metric keys: energy_kcal, protein_per_kcal, fiber_per_kcal, satfat_per_kcal
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT query_category, primary_country,
               energy_kcal, protein_100g, fiber_100g, saturated_fat_100g
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

    for col in ['energy_kcal', 'protein_100g', 'fiber_100g', 'saturated_fat_100g']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    kcal = df['energy_kcal']
    df['protein_per_kcal'] = df['protein_100g'] / kcal * 100
    df['fiber_per_kcal']   = df['fiber_100g']   / kcal * 100
    df['satfat_per_kcal']  = df['saturated_fat_100g'] / kcal * 100

    metrics = ['energy_kcal', 'protein_per_kcal', 'fiber_per_kcal', 'satfat_per_kcal']
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

