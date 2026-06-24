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

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH            = REPO_ROOT / "database" / "positioning_radar.db"
COMPANY_MAP_PATH   = REPO_ROOT / "data" / "reference" / "company_brand_mapping.csv"
REGION_MAP_PATH    = REPO_ROOT / "data" / "country_region_mapping.csv"


def database_exists() -> bool:
    return DB_PATH.exists()


@st.cache_resource(show_spinner=False)
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(show_spinner=False)
def get_company_brand_map() -> dict[str, list[str]]:
    """Load data/reference/company_brand_mapping.csv into
    {parent_company: [primary_brand_db, ...]} — used to translate a
    company-level filter selection into a set of brand-level IN-clause
    values. Cached permanently (no TTL) because the file only changes
    when a new company_brand_mapping.csv is committed."""
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
    """Load data/country_region_mapping.csv and return a list of
    (region_code, region_filter_label) tuples, ordered by ui_order,
    for use in the Market / region sidebar multiselect.
    OTHER_MIXED is included last so users can filter for it explicitly."""
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
            if code and code not in seen:
                seen[code] = (label, order)
    return [(code, label) for code, (label, order) in
            sorted(seen.items(), key=lambda x: x[1][1])]


@st.cache_data(show_spinner=False, ttl=600)
def get_filter_options() -> dict[str, list]:
    """Distinct values for sidebar filter widgets. Cached for 10 minutes
    — fine since this dataset changes when a pipeline run completes,
    not on user interaction.

    Country filter is intentionally absent: it is replaced by the
    Market / region filter in Phase 2 (which groups OFF country tags
    into named regions via data/country_region_mapping.csv).
    claim_category_2 excludes 'none' (the explicit "no subcategory"
    code) — filtering for "no subcategory" is not meaningful in a
    multiselect context.
    """
    conn = get_connection()
    queries = {
        "query_category": """
            SELECT DISTINCT query_category FROM products
            WHERE query_category IS NOT NULL AND TRIM(query_category) != ''
            ORDER BY 1
        """,
        "primary_brand": """
            SELECT DISTINCT primary_brand FROM products
            WHERE primary_brand IS NOT NULL AND TRIM(primary_brand) != ''
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
            # One failing query (e.g. column doesn't exist in an older DB
            # build, or a schema mismatch) should show an empty filter
            # rather than crashing the whole page. Log so it's visible in
            # the terminal without surfacing a red box in the UI.
            print(f"[get_filter_options] '{key}' query failed: {exc}")
            results[key] = []
    return results


def _qmarks(values: list) -> str:
    return ",".join("?" for _ in values)


def _build_where(
    text: str,
    categories: Optional[list[str]],
    brands: Optional[list[str]],
    company_brands: Optional[list[str]],
    region_codes: Optional[list[str]],
    claim_areas: Optional[list[str]],
    claim_focuses: Optional[list[str]],
    nova_groups: Optional[list[int]],
    nutriscore_grades: Optional[list[str]],
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []

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
        # Normalize both sides: lowercase + remove hyphens so that
        # 'coca-cola' in the mapping CSV matches 'coca cola' in the DB.
        # Remaining mismatches (e.g. 'coca-cola company' vs 'coca-cola')
        # are a mapping coverage gap — see brand coverage report / C-fix.
        normalized_brands = [b.lower().replace("-", " ") for b in company_brands]
        clauses.append(
            f"LOWER(REPLACE(p.primary_brand, '-', ' ')) IN ({_qmarks(normalized_brands)})"
        )
        params.extend(normalized_brands)
    if region_codes:
        # LIKE '%CODE%' is safe here: no region code is a substring of
        # another (confirmed against country_region_mapping.csv). OR
        # semantics: a product matching ANY selected region is included.
        region_clause = " OR ".join(
            f"p.observed_market_region_codes LIKE ?" for _ in region_codes
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
        # Normalize to lowercase for comparison — stored values may vary
        # in case across different pipeline runs or OFF source records.
        clauses.append(f"LOWER(p.nutriscore_grade) IN ({_qmarks(nutriscore_grades)})")
        params.extend([g.lower() for g in nutriscore_grades])

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def count_products(
    text: str = "",
    categories: Optional[list[str]] = None,
    brands: Optional[list[str]] = None,
    company_brands: Optional[list[str]] = None,
    region_codes: Optional[list[str]] = None,
    claim_areas: Optional[list[str]] = None,
    claim_focuses: Optional[list[str]] = None,
    nova_groups: Optional[list[int]] = None,
    nutriscore_grades: Optional[list[str]] = None,
) -> int:
    conn = get_connection()
    where_sql, params = _build_where(
        text, categories, brands, company_brands, region_codes,
        claim_areas, claim_focuses, nova_groups, nutriscore_grades
    )
    query = f"""
        SELECT COUNT(*)
        FROM products p
        LEFT JOIN product_analysis a ON a.barcode = p.barcode
        {where_sql}
    """
    return conn.execute(query, params).fetchone()[0]


def search_products(
    text: str = "",
    categories: Optional[list[str]] = None,
    brands: Optional[list[str]] = None,
    company_brands: Optional[list[str]] = None,
    region_codes: Optional[list[str]] = None,
    claim_areas: Optional[list[str]] = None,
    claim_focuses: Optional[list[str]] = None,
    nova_groups: Optional[list[int]] = None,
    nutriscore_grades: Optional[list[str]] = None,
    limit: int = 200,
) -> pd.DataFrame:
    """One row per matching product, left-joined with its analysis row
    (a product may not have an analysis row yet if the pipeline hasn't
    reached it). Capped at `limit` rows — callers should pair this with
    count_products() to show 'X matches, showing first N' when truncated.

    Results are returned ordered by product_name ASC. Column-level sorting
    is handled by Streamlit's interactive dataframe widget (users click
    column headers); this function does not expose a sort parameter to
    the UI layer, which would compete with that affordance.
    """
    conn = get_connection()
    where_sql, params = _build_where(
        text, categories, brands, company_brands, region_codes,
        claim_areas, claim_focuses, nova_groups, nutriscore_grades
    )
    query = f"""
        SELECT p.*, a.*
        FROM products p
        LEFT JOIN product_analysis a ON a.barcode = p.barcode
        {where_sql}
        ORDER BY p.product_name ASC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=[*params, limit])
    # SELECT p.*, a.* duplicates the `barcode` join column; keep the
    # first occurrence and drop the rest so column lookups stay unambiguous.
    df = df.loc[:, ~df.columns.duplicated()]
    return df
