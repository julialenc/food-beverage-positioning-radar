"""
Product Explorer — main product page.

IS/TELLS architecture:
- IS columns: per-kcal nutritional metrics indexed vs country-category average
- TELLS column: on-pack claims detected by OCR/LLM (vision products only)
- Claim area / Claim focus removed — ingredient-derived taxonomy was
  unreliable (ferments lactiques in cheese → gut health false positive).
  Replaced by vision-only Positioning filter and TELLS column.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from shared import components, db, labels

NOVA_DESCRIPTIONS = {
    1: "Unprocessed / minimally processed",
    2: "Processed culinary ingredients",
    3: "Processed foods",
    4: "Ultra-processed foods",
}

COMPLETENESS_WARNING_THRESHOLD = 80

# Claim codes → friendly display names (TELLS column + card + Positioning filter)
_CLAIM_NAMES: dict[str, str] = {
    "protein_claim": "Protein", "protein": "Protein",
    "fibre_claim": "Fibre", "fiber_claim": "Fibre",
    "fiber": "Fibre", "fibre": "Fibre",
    "prebiotic_claim": "Prebiotic", "probiotic_claim": "Probiotic",
    "immune_claim": "Immune support",
    "fortification_claim": "Vitamins & minerals",
    "vitalite_concept": "Vitamins & minerals",
    "vitamin_claim": "Vitamins & minerals", "vitamins": "Vitamins & minerals",
    "energy_claim": "Energy", "energy": "Energy",
    "no_added_sugar_claim": "No added sugar", "no_added_sugar": "No added sugar",
    "sugar_reduction_claim": "Reduced sugar",
    "low_fat_claim": "Low fat", "fat_free_claim": "Fat free",
    "natural_claim": "Natural", "natural": "Natural",
    "organic_claim": "Organic", "organic": "Organic",
    "plant_based_claim": "Plant-based",
    "vegan_claim": "Vegan", "gluten_free_claim": "Gluten free",
    "lactose_free_claim": "Lactose free",
    "high_protein_claim": "High protein",
    "heritage_claim": "Heritage", "heritage": "Heritage",
    "origin_quality_claim": "Origin / provenance",
    "reformulation_claim": "New recipe / reformulation",
    "comparative_claim": "Comparative claim",
    "no_palm_oil": "No palm oil", "no_artificial": "No artificial ingredients",
    "clean_label_claim": "Clean label",
    "minimal_ingredients_claim": "Minimal ingredients",
    "sustainability_halo": "Sustainability",
    "glp1_positioning": "Satiety / GLP-1",
    "gender_targeting_claim": "Gender-targeted",
}

# All table columns: display_name → (source_col_or_None, is_default)
_ALL_COLS: dict[str, tuple] = {
    "Category":              ("query_category",     True),
    "Brand":                 ("primary_brand",      True),
    "Product":               ("product_name",       True),
    "Energy, kcal/100g":     ("_energy",            True),
    "Protein, g/100 kcal":   ("_protein_is",        True),
    "Fibre, g/100 kcal":     ("_fiber_is",           True),
    "Saturated fat, g/100 kcal": ("_satfat_is",       True),
    "NOVA":                  ("_nova_str",           True),
    "Positioning":           ("_positioning",        True),
    # Optional
    "Nutri-Score":           ("_nutriscore_str",     False),
    "Protein, g/100g":       ("protein_100g",        False),
    "Fat, g/100g":           ("fat_100g",            False),
    "Saturated fat, g/100g": ("saturated_fat_100g",  False),
    "Carbohydrate, g/100g":  ("carbs_100g",          False),
    "Total sugars, g/100g":  ("sugars_100g",         False),
    "Added sugar, g/100g":   (None,                  False),
    "Fibre, g/100g":         ("fiber_100g",          False),
    "Salt, g/100g":          ("salt_100g",           False),
}
_DEFAULT_COLS = [k for k, (_, d) in _ALL_COLS.items() if d]

# Status filter options
_STATUS_OPTS = ["All", "↑ Above average", "≈ Parity", "↓ Below average"]


def _missing(value) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(value, str) and value.strip().lower() in ("", "nan", "none"):
        return True
    return False


def _to_float(value) -> float | None:
    if _missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> int | None:
    num = _to_float(value)
    return int(num) if num is not None else None


def _fmt_num(value, unit: str = "", decimals: int = 1) -> str:
    if _missing(value):
        return "Not reported"
    try:
        return f"{float(value):.{decimals}f}{unit}"
    except (TypeError, ValueError):
        return "Not reported"


def _fmt_nova(value) -> str:
    if _missing(value):
        return "—"
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return "—"
    return f"{n} — {NOVA_DESCRIPTIONS.get(n, 'Unclassified')}"


def _fmt_is(value, category: str, region: str, metric: str,
            decimals: int = 1) -> str:
    """Format IS metric: <number> <arrow>, indexed vs country-category average.

    Arrow shows position vs average only (↑ above / ≈ parity / ↓ below) —
    no colour, no favourability judgment. The number is right-justified to
    a fixed width so that plain text sort (as used by st.dataframe's
    column-header click) matches numeric sort order.
    """
    if _missing(value):
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    width = 4 if decimals == 0 else 5
    num_str = f"{num:>{width}.{decimals}f}"
    avg = (
        _AVG.get((category, region), {}).get(metric)
        or _AVG.get((category, "ALL"), {}).get(metric)
    )
    if avg is None or avg == 0:
        return num_str
    try:
        idx = num / avg * 100
    except (TypeError, ZeroDivisionError):
        return num_str
    if idx > 110:
        arrow = "↑"
    elif idx >= 90:
        arrow = "≈"
    else:
        arrow = "↓"
    return f"{num_str} {arrow}"


def _metric_index(value, category: str, region: str, metric: str) -> float | None:
    """Raw index (0-∞) for a metric vs country-category average."""
    avg = (
        _AVG.get((category, region), {}).get(metric)
        or _AVG.get((category, "ALL"), {}).get(metric)
    )
    if _missing(value) or avg is None or avg == 0:
        return None
    try:
        return float(value) / avg * 100
    except (TypeError, ZeroDivisionError):
        return None


def _build_is_col(df: pd.DataFrame, val_col: str, metric_key: str,
                  decimals: int = 1) -> list[str]:
    out = []
    for _, row in df.iterrows():
        cat    = str(row.get("query_category") or "")
        region = str(row.get("_region") or "OTHER")
        out.append(_fmt_is(row.get(val_col), cat, region,
                            metric_key, decimals))
    return out


def _fmt_positioning(pack_claims_val, claim_source: str) -> str:
    if claim_source != "vision":
        return "Not tested"
    if _missing(pack_claims_val) or not str(pack_claims_val).strip():
        return "No claims on pack"
    claims = [c.strip() for c in str(pack_claims_val).split("|") if c.strip()]
    seen: list[str] = []
    for c in claims:
        label = _CLAIM_NAMES.get(
            c.lower(),
            c.replace("_claim", "").replace("_", " ").title()
        )
        if label not in seen:
            seen.append(label)
    return " · ".join(seen) if seen else "No claims on pack"


def _apply_status_filter(df: pd.DataFrame, col: str, metric: str,
                         status: str) -> pd.DataFrame:
    """Post-query filter: keep rows matching the selected status tier."""
    if status == "All" or df.empty:
        return df
    indices = []
    for _, row in df.iterrows():
        cat    = str(row.get("query_category") or "")
        region = str(row.get("_region") or "OTHER")
        idx    = _metric_index(row.get(col), cat, region, metric)
        if idx is None:
            continue
        if status == "↑ Above average" and idx > 110:
            indices.append(row.name)
        elif status == "≈ Parity" and 90 <= idx <= 110:
            indices.append(row.name)
        elif status == "↓ Below average" and idx < 90:
            indices.append(row.name)
    return df.loc[indices] if indices else df.iloc[0:0]


# ── Product card ──────────────────────────────────────────────────────────────

def render_product_card(product: dict) -> None:
    st.divider()

    # 1. Header
    img_col, info_col = st.columns([1, 2.4])
    with img_col:
        image_url = components.product_image_url(product.get("image_url"))
        components.render_product_pack_image(
            image_url, product_name=product.get("product_name") or ""
        )
        if image_url:
            st.link_button("Open full image ↗", image_url)

    with info_col:
        st.markdown(f"### {product.get('product_name') or 'Unnamed product'}")
        meta_parts = []
        if not _missing(product.get("primary_brand")):
            meta_parts.append(f"**Brand:** {product['primary_brand']}")
        if not _missing(product.get("query_category")):
            meta_parts.append(f"**Category:** {product['query_category']}")
        if meta_parts:
            st.markdown(" · ".join(meta_parts))
        if not _missing(product.get("quantity")):
            st.markdown(f"**Pack size:** {product['quantity']}")
        completeness_int = _to_int(product.get("completeness_score"))
        if completeness_int is not None and completeness_int < COMPLETENESS_WARNING_THRESHOLD:
            st.warning(
                f"Some source fields are missing for this product "
                f"(completeness: {completeness_int}%), so interpretation may be incomplete.",
                icon="⚠️",
            )

    # 2. Badges
    badge_html = ""
    if not _missing(product.get("nutriscore_grade")):
        badge_html += components.render_badge(
            f"Nutri-Score&nbsp;<b>{str(product['nutriscore_grade']).upper()}</b>"
        )
    nova = product.get("nova_group")
    if not _missing(nova):
        nova_int = _to_int(nova)
        if nova_int is not None:
            badge_html += components.render_badge(
                f"NOVA {nova_int} — {NOVA_DESCRIPTIONS.get(nova_int, 'Unclassified')}"
            )
    if badge_html:
        st.markdown(badge_html, unsafe_allow_html=True)
        components.caption(
            "Nutri-Score and NOVA come from Open Food Facts. External reference "
            "classifications, not this tool's own assessment."
        )

    # 3. Nutrition grid
    components.section_label("Nutrition (per 100g / 100ml)")
    nutrition_cols = st.columns(4)
    nutrition_fields = [
        ("Energy",        product.get("energy_kcal"),       " kcal", 0),
        ("Protein",       product.get("protein_100g"),       " g",    1),
        ("Fat",           product.get("fat_100g"),           " g",    1),
        ("Carbohydrates", product.get("carbs_100g"),         " g",    1),
        ("Salt",          product.get("salt_100g"),          " g",    2),
        ("Fibre",         product.get("fiber_100g"),         " g",    1),
        ("Saturated fat", product.get("saturated_fat_100g"), " g",    1),
        ("Sugars",        product.get("sugars_100g"),        " g",    1),
    ]
    for i, (label_text, value, unit, decimals) in enumerate(nutrition_fields):
        with nutrition_cols[i % 4]:
            st.metric(label_text, _fmt_num(value, unit, decimals))

    # 4. Claim & positioning signals — vision only; "Not tested" otherwise
    components.section_label("Claim & positioning signals")
    claim_source = product.get("claim_source", "")
    pack_claims  = product.get("pack_claims_found")

    if claim_source != "vision":
        st.markdown(
            '<div class="fbpr-empty-note">Not tested — pack image not analyzed '
            "by OCR/LLM for this product.</div>",
            unsafe_allow_html=True,
        )
    else:
        if not _missing(pack_claims) and str(pack_claims).strip():
            claim_codes   = [c.strip() for c in str(pack_claims).split("|") if c.strip()]
            friendly_list = []
            for c in claim_codes:
                label = _CLAIM_NAMES.get(
                    c.lower(), c.replace("_claim", "").replace("_", " ").title()
                )
                if label not in friendly_list:
                    friendly_list.append(label)
            components.render_chips(friendly_list, kind="claim")
            components.caption(
                f"{len(claim_codes)} claim{'s' if len(claim_codes) != 1 else ''} detected "
                "on front-of-pack image (OCR + LLM extraction)."
            )
        else:
            st.markdown(
                '<div class="fbpr-empty-note">No claims identified on pack image.</div>',
                unsafe_allow_html=True,
            )
            components.caption("Pack image analyzed; no front-of-pack claims were identified.")

    # 5. Full ingredient list
    ingredients = product.get("ingredients_text")
    if not _missing(ingredients) and str(ingredients).strip():
        with st.expander("Full ingredient list"):
            st.write(str(ingredients))
    else:
        with st.expander("Full ingredient list"):
            st.write("Not available for this product.")


# ── Page body ─────────────────────────────────────────────────────────────────

components.inject_base_css()
components.render_header(
    "Product Explorer",
    "Search products, filter by positioning signals, and inspect the evidence behind each product.",
)

if not db.database_exists():
    st.info(
        "No local database found yet at `database/positioning_radar.db`. "
        "Run the pipeline first — see the README."
    )
    st.stop()

# Load averages once (cached)
_AVG     = db.get_category_region_averages()
_COUNTRY_REGION = {
    'France': 'FRANCE', 'United Kingdom': 'UK_IE', 'Great Britain': 'UK_IE',
    'Ireland': 'UK_IE', 'England': 'UK_IE', 'Scotland': 'UK_IE',
    'United States': 'US_CANADA', 'Canada': 'US_CANADA',
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Filters")
    text = st.text_input("Search product or brand")
    options          = db.get_filter_options()
    company_brand_map = db.get_company_brand_map()

    # 1. Category
    categories = st.multiselect("Category", options["query_category"])

    # 2. Market / region
    region_options      = db.get_region_options()
    region_label_to_code = {label: code for code, label in region_options}
    selected_region_labels = st.multiselect(
        "Market / region",
        [label for _, label in region_options],
        help=(
            "Filters to products sold in this market. Only markets with "
            "full-coverage downloads are shown. Current scope: France, "
            "UK & Ireland, US & Canada."
        ),
    )
    selected_region_codes = [region_label_to_code[l] for l in selected_region_labels]

    # 3. Company / owner
    all_companies     = sorted(company_brand_map.keys())
    selected_companies = st.multiselect(
        "Company / owner",
        all_companies + [db.COMPANY_OTHER_LABEL],
        help=(
            "Filter by parent company. Selecting a company pre-fills the "
            "Brand dropdown. 'Other / not mapped' shows unmatched brands."
        ),
    )
    other_selected = db.COMPANY_OTHER_LABEL in selected_companies
    real_companies  = [c for c in selected_companies if c != db.COMPANY_OTHER_LABEL]

    # 4. Brand (dependent on Company + Category)
    if real_companies and not other_selected:
        company_pool = sorted({b for c in real_companies for b in company_brand_map.get(c, [])})
        brand_selection = st.multiselect(
            "Brand", company_pool,
            help="Brands belonging to the selected company.",
        )
        selected_company_brands: list[str] = brand_selection if brand_selection else company_pool
        exclude_company_brands: list[str]  = []
        direct_brands: list[str]           = []
    elif other_selected:
        all_mapped = [b for bl in company_brand_map.values() for b in bl]
        selected_company_brands = []
        exclude_company_brands  = all_mapped
        direct_brands = st.multiselect(
            "Brand", db.get_brand_options(tuple(categories)),
            help="Select from brands not mapped to any company.",
        )
    else:
        selected_company_brands = []
        exclude_company_brands  = []
        direct_brands = st.multiselect("Brand", db.get_brand_options(tuple(categories)))

    # 5. Positioning (vision-analyzed products only)
    pos_codes_raw   = db.get_positioning_options()
    pos_code_to_label = {
        code: _CLAIM_NAMES.get(code.lower(),
               code.replace("_claim", "").replace("_", " ").title())
        for code in pos_codes_raw
    }
    pos_label_to_code = {v: k for k, v in pos_code_to_label.items()}
    pos_labels_unique = sorted(set(pos_code_to_label.values()))
    selected_pos_labels = st.multiselect(
        "Positioning",
        pos_labels_unique,
        help=(
            "Filter by claims detected on pack by OCR/LLM. Only applies to "
            "vision-analyzed products (~5,200 in this dataset). "
            "Selecting multiple claims shows products with ANY of them."
        ),
    )
    # Reverse-map: a friendly name may map to multiple raw codes
    selected_pos_codes: list[str] = []
    for label in selected_pos_labels:
        for code, lbl in pos_code_to_label.items():
            if lbl == label and code not in selected_pos_codes:
                selected_pos_codes.append(code)

    # 6. Status vs country-category average
    st.markdown(
        "**Status vs country-category average**  "
        "<span title='Compares each product to the average for its own "
        "category and market (e.g. France Dairies). Averages are "
        "pre-computed from the full dataset and do not change with filters. "
        "Applies to the visible results — use category and market filters "
        "first for the most meaningful comparison.' "
        "style='cursor:help; color:#8A8F8A;'>ℹ️</span>",
        unsafe_allow_html=True,
    )
    protein_status = st.selectbox("Protein, g/100 kcal", _STATUS_OPTS)
    fibre_status   = st.selectbox("Fibre, g/100 kcal",   _STATUS_OPTS)
    satfat_status  = st.selectbox("Saturated fat, g/100 kcal", _STATUS_OPTS)
    sugars_status  = st.selectbox("Sugars, g/100 kcal",  _STATUS_OPTS)

    # 7. Nutri-Score
    _NUTRISCORE_LABELS = {
        "a": "A — Most favourable profile", "b": "B", "c": "C", "d": "D",
        "e": "E — Least favourable profile",
        "unknown": "UNKNOWN", "not-applicable": "NOT APPLICABLE",
        "not_applicable": "NOT APPLICABLE",
    }
    selected_nutriscore = st.multiselect(
        "Nutri-Score",
        options.get("nutriscore_grade", []),
        format_func=lambda g: _NUTRISCORE_LABELS.get(str(g).lower(), str(g).upper()),
        help="A = most favourable; E = least favourable. From Open Food Facts.",
    )

    # 8. NOVA group
    nova_choices = st.multiselect(
        "NOVA group", [1, 2, 3, 4],
        format_func=lambda n: f"{n} — {NOVA_DESCRIPTIONS[n]}",
        help="Processing level from Open Food Facts. Not this tool's assessment.",
    )

    # column selector moved to main area above table

# ── Query ─────────────────────────────────────────────────────────────────────
total = db.count_products(
    text, categories, direct_brands,
    selected_company_brands, exclude_company_brands,
    selected_region_codes, selected_pos_codes,
    nova_choices, selected_nutriscore,
)

if total == 0:
    st.warning("No products match these filters.")
    st.stop()

results = db.search_products(
    text, categories, direct_brands,
    selected_company_brands, exclude_company_brands,
    selected_region_codes, selected_pos_codes,
    nova_choices, selected_nutriscore,
    limit=1000,
)
shown = len(results)

# ── Match count + instruction ──────────────────────────────────────────────────
if total > shown:
    st.caption(
        f"{total:,} products match — showing the first {shown} rows. "
        "Narrow your filters to inspect a smaller set."
    )
else:
    st.caption(f"{total:,} product{'s' if total != 1 else ''} match.")
st.markdown(
    "Tick one row in the table to view full product details below. "
    "Click column headers to sort. "
    "Hover column headers marked **ℹ️** to see what the colours mean."
)

# ── Column selector — above table so users see it immediately ────────────────
selected_col_names: list[str] = st.multiselect(
    "Table columns",
    list(_ALL_COLS.keys()),
    default=_DEFAULT_COLS,
    help=(
        "Add or remove columns. Columns with ↑ ≈ ↓ are indexed vs the "
        "country-category average — hover any column header for details. "
        "Additional columns show absolute values per 100g."
    ),
)

# ── Build computed columns ────────────────────────────────────────────────────
display_df = results.copy()
display_df["_region"] = (
    display_df["primary_country"].map(_COUNTRY_REGION).fillna("OTHER")
)

# Per-kcal ratios
_kcal   = display_df["energy_kcal"].apply(_to_float)
_prot   = display_df["protein_100g"].apply(_to_float)
_fib    = display_df["fiber_100g"].apply(_to_float)
_satfat = display_df["saturated_fat_100g"].apply(_to_float)
_sugars = display_df["sugars_100g"].apply(_to_float)

display_df["_protein_per_kcal"] = _prot   / _kcal.where(_kcal > 0) * 100
display_df["_fiber_per_kcal"]   = _fib    / _kcal.where(_kcal > 0) * 100
display_df["_satfat_per_kcal"]  = _satfat / _kcal.where(_kcal > 0) * 100
display_df["_sugars_per_kcal"]  = _sugars / _kcal.where(_kcal > 0) * 100

# ── Apply post-query status filters ──────────────────────────────────────────
display_df = _apply_status_filter(display_df, "_protein_per_kcal", "protein_per_kcal", protein_status)
display_df = _apply_status_filter(display_df, "_fiber_per_kcal",   "fiber_per_kcal",   fibre_status)
display_df = _apply_status_filter(display_df, "_satfat_per_kcal",  "satfat_per_kcal",  satfat_status)
display_df = _apply_status_filter(display_df, "_sugars_per_kcal",  "sugars_per_kcal",  sugars_status)

if display_df.empty:
    st.info("No products match the selected status filters.")
    st.stop()

# ── IS display columns ────────────────────────────────────────────────────────
# Energy, Protein, Fibre, Sat fat — arrow shows position vs country-category average
# only (↑/≈/↓); no favourability judgment is encoded in formatting.
display_df["_energy"] = _build_is_col(
    display_df, "energy_kcal",       "energy_kcal",      0)
display_df["_protein_is"] = _build_is_col(
    display_df, "_protein_per_kcal", "protein_per_kcal", 1)
display_df["_fiber_is"]   = _build_is_col(
    display_df, "_fiber_per_kcal",   "fiber_per_kcal",   1)
display_df["_satfat_is"]  = _build_is_col(
    display_df, "_satfat_per_kcal",  "satfat_per_kcal",  1)
display_df["_nova_str"]        = display_df["nova_group"].apply(_fmt_nova)
display_df["_nutriscore_str"]  = display_df["nutriscore_grade"].apply(
    lambda g: str(g).upper() if not _missing(g) else "—"
)
display_df["_positioning"] = display_df.apply(
    lambda row: _fmt_positioning(
        row.get("pack_claims_found"), row.get("claim_source", "")
    ), axis=1,
)

# Optional absolute columns
_ABS_COLS = {
    "Protein, g/100g":       ("protein_100g",       1),
    "Fat, g/100g":           ("fat_100g",            1),
    "Saturated fat, g/100g": ("saturated_fat_100g",  1),
    "Carbohydrate, g/100g":  ("carbs_100g",          1),
    "Total sugars, g/100g":  ("sugars_100g",         1),
    "Added sugar, g/100g":   (None,                  1),
    "Fibre, g/100g":         ("fiber_100g",          1),
    "Salt, g/100g":          ("salt_100g",           1),
    "Nutri-Score":           ("_nutriscore_str",     0),
}
# Optional columns shown indexed vs country-category average (↑/≈/↓ arrow, no colour)
_INDEXED_OPT = {
    "Total sugars, g/100g": ("sugars_100g", "sugars_100g", 1),
    "Salt, g/100g":         ("salt_100g",   "salt_100g",   1),
}

for col_name in selected_col_names:
    if col_name not in _DEFAULT_COLS and col_name in _ABS_COLS:
        if col_name in _INDEXED_OPT:
            # Indexed optional column (arrow vs country-category average)
            df_col, avg_metric, decimals = _INDEXED_OPT[col_name]
            display_df[col_name] = _build_is_col(
                display_df, df_col, avg_metric, decimals
            )
        else:
            db_col, decimals = _ABS_COLS[col_name]
            if db_col is None:
                display_df[col_name] = "Not declared"
            elif db_col.startswith("_"):
                pass  # already computed above (_nutriscore_str)
            elif db_col in display_df.columns:
                display_df[col_name] = display_df[db_col].apply(
                    lambda v, d=decimals: f"{float(v):.{d}f}" if not _missing(v) else "—"
                )
            else:
                display_df[col_name] = "—"

# ── Export CSV (numeric, no emoji) ────────────────────────────────────────────
export_cols = {
    "query_category":     "Category",
    "primary_brand":      "Brand",
    "product_name":       "Product",
    "energy_kcal":        "Energy, kcal/100g",
    "_protein_per_kcal":  "Protein, g/100 kcal",
    "_fiber_per_kcal":    "Fibre, g/100 kcal",
    "_satfat_per_kcal":   "Saturated fat, g/100 kcal",
    "_sugars_per_kcal":   "Sugars, g/100 kcal",
    "nova_group":         "NOVA group",
    "nutriscore_grade":   "Nutri-Score",
    "_positioning":       "Positioning (pack claims)",
}
export_df = (
    display_df[[c for c in export_cols if c in display_df.columns]]
    .rename(columns=export_cols)
)
csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Download visible rows as CSV", csv_bytes,
    file_name="food_positioning_radar_filtered_products.csv",
    mime="text/csv",
    help="Exports numeric values (no emoji) for analysis in Excel or Python.",
)
st.caption(
    "Source data: Open Food Facts (ODbL). Export for analysis — please attribute."
)

# ── Table ─────────────────────────────────────────────────────────────────────
col_rename = {
    "query_category":     "Category",
    "primary_brand":      "Brand",
    "product_name":       "Product",
    "_energy":            "Energy, kcal/100g",
    "_nova_str":          "NOVA",
    "_positioning":       "Positioning",
    "_nutriscore_str":    "Nutri-Score",
}

table_src_cols = []
table_disp_cols = []
for col_name in selected_col_names:
    if col_name in _ALL_COLS:
        src, _ = _ALL_COLS[col_name]
        if src is None:
            display_df[col_name] = display_df.get(col_name, "Not declared")
            src = col_name
        # For optional columns, the formatted (emoji+number) string is stored
        # under col_name. For default IS columns, it's stored under the internal
        # src key (e.g. "_energy", "_protein_is"). Prefer col_name if it exists.
        effective_src = col_name if col_name in display_df.columns else src
        if effective_src in display_df.columns:
            table_src_cols.append(effective_src)
            table_disp_cols.append(col_name)
    elif col_name in display_df.columns:
        table_src_cols.append(col_name)
        table_disp_cols.append(col_name)

if not table_src_cols:
    st.info("Select at least one column to display.")
    st.stop()

table_view = display_df[table_src_cols].copy()
table_view.columns = table_disp_cols

# Column help text: explain the arrow — same neutral meaning for every
# indexed metric, no favourability judgment.
_ARROW_HELP = (
    "↑ above country-category average    ≈ within ±10% of country-category average    "
    "↓ below country-category average"
)
_COL_HELP = {
    "Energy, kcal/100g":         _ARROW_HELP,
    "Protein, g/100 kcal":       _ARROW_HELP,
    "Fibre, g/100 kcal":         _ARROW_HELP,
    "Saturated fat, g/100 kcal": _ARROW_HELP,
    "Total sugars, g/100g":      _ARROW_HELP,
    "Salt, g/100g":              _ARROW_HELP,
}
col_cfg = {
    col: st.column_config.TextColumn(col, help=help_text)
    for col, help_text in _COL_HELP.items()
    if col in table_disp_cols
}
event = st.dataframe(
    table_view,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    column_config=col_cfg if col_cfg else None,
)
selected_rows = event.selection["rows"]

if not selected_rows:
    st.info("Tick one row above to view full product details.")
else:
    # Map back to original results index
    original_idx = display_df.index[selected_rows[0]]
    selected_product = results.loc[original_idx].to_dict()
    render_product_card(selected_product)
