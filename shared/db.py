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
COMPANY_MANUAL_REVIEW_LABEL = "Manual review"


def database_exists() -> bool:
    return DB_PATH.exists()


@st.cache_resource(show_spinner=False)
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
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
                "country_tags_include": row.get("country_tags_include", "").strip(),
                "country_tags_exclude": row.get("country_tags_exclude", "").strip(),
                "region_codes_include": row.get("region_codes_include", "").strip(),
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
            if r["status"] == "direct"
            and r["parent_company"].lower() != COMPANY_MANUAL_REVIEW_LABEL.lower()
        ]
        scoped_or_review = [
            r for r in brand_rows
            if r["status"] in {"market_scoped", "manual_review"}
            or r["parent_company"].lower() == COMPANY_MANUAL_REVIEW_LABEL.lower()
        ]

        if not scoped_or_review and len(direct_rows) == 1:
            mapping[direct_rows[0]["parent_company"]].add(brand)
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
    return sorted({row["parent_company"] for row in get_company_mapping_rows()})


def _split_scope_values(value: str) -> list[str]:
    return [v.strip() for v in str(value or "").split("|") if v.strip()]


def _any_token_match(source_value: str, tokens: list[str]) -> bool:
    if not tokens:
        return False
    source_tokens = {v.strip().lower() for v in str(source_value or "").split("|") if v.strip()}
    return any(token.lower() in source_tokens for token in tokens)


def _row_scope_matches(row: dict[str, str], countries: str, region_codes: str) -> bool:
    include_regions = _split_scope_values(row.get("region_codes_include", ""))
    include_countries = _split_scope_values(row.get("country_tags_include", ""))
    exclude_countries = _split_scope_values(row.get("country_tags_exclude", ""))

    # A market-scoped row with no structured scope is a documented caveat,
    # not a resolvable rule. Keep it out of automatic attribution.
    if not include_regions and not include_countries:
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

    scoped = [r for r in rows if r["status"] == "market_scoped"]
    manual = [
        r for r in rows
        if r["status"] == "manual_review"
        or r["parent_company"].lower() == COMPANY_MANUAL_REVIEW_LABEL.lower()
    ]
    direct = [
        r for r in rows
        if r["status"] == "direct"
        and r["parent_company"].lower() != COMPANY_MANUAL_REVIEW_LABEL.lower()
    ]

    if scoped:
        matches = [r for r in scoped if _row_scope_matches(r, countries, region_codes)]
        companies = sorted({r["parent_company"] for r in matches})
        if len(companies) == 1:
            return companies[0]
        return COMPANY_MANUAL_REVIEW_LABEL if manual or scoped else COMPANY_OTHER_LABEL

    if len(direct) == 1:
        return direct[0]["parent_company"]
    if len(direct) > 1 or manual:
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
    return out


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
    return str(b or "").strip().lower().replace("-", " ")


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
    limit: Optional[int] = 1000,
) -> pd.DataFrame:
    conn = get_connection()
    where_sql, params = _build_where(
        text, categories, brands, company_brands, exclude_company_brands,
        region_codes, positioning_codes, nova_groups, nutriscore_grades
    )
    limit_sql = "LIMIT ?" if limit is not None else ""
    query_params = [*params, limit] if limit is not None else params
    df = pd.read_sql_query(f"""
        SELECT p.*, a.*
        FROM products p
        LEFT JOIN product_analysis a ON a.barcode = p.barcode
        {where_sql}
        ORDER BY p.product_name ASC
        {limit_sql}
    """, conn, params=query_params)
    df = df.loc[:, ~df.columns.duplicated()]
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
            text, categories, brands, None, None,
            region_codes, positioning_codes, nova_groups, nutriscore_grades,
        )
    df = search_products(
        text, categories, brands, None, None,
        region_codes, positioning_codes, nova_groups, nutriscore_grades,
        limit=None,
    )
    return len(filter_products_by_company(df, company_names, region_codes))


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
            text, categories, brands, None, None,
            region_codes, positioning_codes, nova_groups, nutriscore_grades,
            limit=limit,
        )
        return add_resolved_company(df, region_codes)

    df = search_products(
        text, categories, brands, None, None,
        region_codes, positioning_codes, nova_groups, nutriscore_grades,
        limit=None,
    )
    filtered = filter_products_by_company(df, company_names, region_codes)
    return filtered.head(limit) if limit is not None else filtered


@st.cache_data(show_spinner=False, ttl=600)
def get_market_products(category: str, region_code: str) -> pd.DataFrame:
    """The full product set for one region x one category — the shared
    dataset behind Market Overview's Product Landscape and Product Profile
    Landscape sections (spec section 10: reuse the same cleaned dataset
    used by Product Explorer, no separate analytical source).

    Returns raw per-100g/100ml nutrition fields plus derived per-100kcal
    fields (protein/fiber/satfat/sugars), and a derived `company` column
    from the company/brand mapping (COMPANY_OTHER_LABEL when unmapped).
    Company/brand narrowing happens client-side on this cached frame,
    not via separate SQL calls, since a single region x category
    population is small enough to hold in memory (tens of thousands of
    rows, not millions).
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT barcode, product_name, primary_brand, primary_country, image_url,
               countries, observed_market_region_codes,
               ingredients_text, completeness_score,
               energy_kcal, fat_100g, saturated_fat_100g, carbs_100g,
               sugars_100g, fiber_100g, protein_100g, salt_100g,
               nova_group, nutriscore_grade
        FROM products
        WHERE query_category = ?
          AND observed_market_region_codes LIKE ?
          AND primary_brand IS NOT NULL
          AND TRIM(LOWER(primary_brand)) NOT IN ('unknown', '', 'nan')
    """, conn, params=[category, f"%{region_code}%"])

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

    # Company / owner: resolved by distinct brand/country keys so large
    # market bases do not pay a resolver call for every product row.
    key_cols = ["primary_brand", "countries"]
    unique_keys = df[key_cols].drop_duplicates()
    resolved = {
        tuple(row): resolve_company_owner(row[0], countries=row[1], region_codes=region_code)
        for row in unique_keys.itertuples(index=False, name=None)
    }
    df["company"] = [
        resolved.get((brand, countries), COMPANY_OTHER_LABEL)
        for brand, countries in df[key_cols].itertuples(index=False, name=None)
    ]

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
