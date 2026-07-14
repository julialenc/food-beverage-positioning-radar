"""
Product Explorer — the main product per the brief.

Two halves: a filterable product table with CSV export, and a detail
card for whichever row is selected. All claim/flag display text is
resolved through shared/labels.py (UI_LABELS.md) — no stored code
should ever reach st.write/st.markdown directly. See docs/UI_LABELS.md
and the project's no-blame principle (docs/ADR.md, docs/METHODOLOGY.md).

Phase 2 filters implemented: Company / owner, Market / region.
Both use CSV reference files and the pipeline-derived
observed_market_region_codes column (see docs/ADR.md).
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

# Completeness threshold below which a per-product warning is shown.
# Above this level the progress bar is suppressed — users don't need
# to see "100% complete" on every product (see feedback IV-C).
COMPLETENESS_WARNING_THRESHOLD = 80


def _missing(value) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        # pd.isna() raises on array-likes rather than returning a bool —
        # not expected here (callers always pass a scalar from a row
        # dict), but guarded defensively rather than letting it propagate.
        pass
    if isinstance(value, str) and value.strip().lower() in ("", "nan", "none"):
        return True
    return False


def _fmt_num(value, unit: str = "", decimals: int = 1) -> str:
    if _missing(value):
        return "Not reported"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "Not reported"
    return f"{num:.{decimals}f}{unit}"


def _to_float(value) -> float | None:
    """Safe float conversion for values from SQLite/pandas that may arrive
    as strings ('18.0', '100.0') even when the column is typed numeric."""
    if _missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> int | None:
    num = _to_float(value)
    return int(num) if num is not None else None


def _fmt_nova(value) -> str:
    """Human-readable NOVA label for the product table.
    Shows '4 — Ultra-processed foods' rather than bare '4' so junior
    users don't need to remember the NOVA scale."""
    if _missing(value):
        return "Not tested"
    try:
        nova_int = int(float(value))
    except (TypeError, ValueError):
        return "—"
    return f"{nova_int} — {NOVA_DESCRIPTIONS.get(nova_int, 'Unclassified')}"


def claim_evidence_caption(product: dict) -> str:
    """Four distinct states — see merge_scores.py for the pipeline logic:
    get_pack_claims_found() returns '' (not None) when vision succeeded
    but found zero claims, and tag_claims.py sets claim_source='vision'
    for any non-null pack_claims_found, including that empty string. So
    claim_source=='vision' does NOT by itself mean claims were found.
    Separately, a product can have pack_analysis_attempted=1 and
    claim_source=='ingredient_text_only' because OCR/LLM failed outright
    — that is a different state from "vision succeeded, zero claims"."""
    attempted = product.get("pack_analysis_attempted")
    source = product.get("claim_source")
    pack_claims = product.get("pack_claims_found")

    if _missing(attempted) or not bool(attempted):
        return (
            "Pack-image claim extraction is not available for this product; "
            "signals are derived from product name and ingredient-list information."
        )
    if source == "vision":
        if _missing(pack_claims) or str(pack_claims).strip() == "":
            return "Pack image analyzed; no front-of-pack claim was identified."
        return "Based on front-of-pack image analysis."

    return (
        "Pack-image claim extraction is not available for this product; "
        "signals are derived from product name and ingredient-list information."
    )


def render_product_card(product: dict) -> None:
    st.divider()

    # ── 1. Header: image + metadata ─────────────────────────────────
    img_col, info_col = st.columns([1, 2.4])

    with img_col:
        image_url = components.product_image_url(product.get("image_url"))
        components.render_product_pack_image(
            image_url,
            product_name=product.get("product_name") or "",
        )
        if image_url:
            st.link_button("Open full image ↗", image_url)

    with info_col:
        st.markdown(f"### {product.get('product_name') or 'Unnamed product'}")

        brand = product.get("primary_brand")
        category = product.get("query_category")
        meta_parts = []
        if brand and not _missing(brand):
            meta_parts.append(f"**Brand:** {brand}")
        if category and not _missing(category):
            meta_parts.append(f"**Category:** {category}")
        if meta_parts:
            st.markdown(" · ".join(meta_parts))

        if not _missing(product.get("quantity")):
            st.markdown(f"**Pack size:** {product['quantity']}")

        completeness = product.get("completeness_score")
        completeness_int = _to_int(completeness)
        if completeness_int is not None and completeness_int < COMPLETENESS_WARNING_THRESHOLD:
            st.warning(
                f"Some source fields are missing for this product "
                f"(completeness: {completeness_int}%), so interpretation may be incomplete.",
                icon="⚠️",
            )

    # ── 2. Nutri-Score + NOVA badges ────────────────────────────────
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
            "Nutri-Score and NOVA come from Open Food Facts. They are external reference "
            "classifications, not this tool's own assessment. See the Methodology tab for details."
        )

    # ── 3. Nutrition grid ───────────────────────────────────────────
    components.section_label("Nutrition (per 100g / 100ml)")
    nutrition_cols = st.columns(4)
    nutrition_fields = [
        # Row 1: high-interest values first
        ("Energy",        product.get("energy_kcal"),       " kcal", 0),
        ("Protein",       product.get("protein_100g"),       " g",    1),
        ("Fat",           product.get("fat_100g"),           " g",    1),
        ("Carbohydrates", product.get("carbs_100g"),         " g",    1),
        # Row 2: fat/sugar detail + salt
        ("Salt",          product.get("salt_100g"),          " g",    2),
        ("Fibre",         product.get("fiber_100g"),         " g",    1),
        ("Saturated fat", product.get("saturated_fat_100g"), " g",    1),
        ("Sugars",        product.get("sugars_100g"),        " g",    1),
    ]
    for i, (label_text, value, unit, decimals) in enumerate(nutrition_fields):
        with nutrition_cols[i % 4]:
            st.metric(label_text, _fmt_num(value, unit, decimals))

    # ── 4. Ingredient-processing markers ────────────────────────────
    components.section_label("Ingredient-processing markers")
    band = product.get("composition_marker_band")
    score = product.get("composition_marker_score")
    if _missing(band) or _missing(score):
        st.markdown(
            '<div class="fbpr-empty-note">Not available for this product.</div>',
            unsafe_allow_html=True,
        )
    else:
        score_num = _to_float(score)
        if score_num is not None:
            st.markdown(
                f'<span class="fbpr-mono">{band} ({score_num:.0f}/40)</span>',
                unsafe_allow_html=True,
            )
            components.caption(
            "Based only on the ingredient list. Higher marker levels mean more detected "
            "ingredient-processing signals, such as emulsifiers, sweeteners, syrups, or "
            "modified starches. This is not a health verdict."
        )

    # ── 5. Claim & positioning signals ──────────────────────────────
    components.section_label("Claim & positioning signals")
    claim_cat_1 = product.get("claim_category_1")
    claim_cat_2 = product.get("claim_category_2")
    claim_chip_labels = []
    if not _missing(claim_cat_1):
        chip = labels.safe_label_for("claim_category_1", claim_cat_1)
        if chip != "—":
            claim_chip_labels.append(chip)
    if not _missing(claim_cat_2) and str(claim_cat_2).strip().lower() not in ("none", "nan", ""):
        chip = labels.safe_label_for("claim_category_2", claim_cat_2)
        if chip != "—":
            claim_chip_labels.append(chip)
    components.render_chips(
        claim_chip_labels, kind="claim", empty_text="No positioning signal identified"
    )
    components.caption(
        "Shows the broad claim area and more specific claim focus detected for this product. "
        "Where pack-image analysis is not available, this may rely on product-name or "
        "ingredient-list signals."
    )
    components.caption(claim_evidence_caption(product))

    pack_claims = product.get("pack_claims_found")
    if not _missing(pack_claims) and str(pack_claims).strip():
        claim_count = len([c for c in str(pack_claims).split("|") if c.strip()])
        st.caption(
            f"{claim_count} individual claim{'s' if claim_count != 1 else ''} detected on pack."
        )

    # ── 6. Nutrition reference flags ────────────────────────────────
    components.section_label("Nutrition reference flags")
    flag_labels = labels.safe_labels_for_pipe_list(
        "nutrition_benchmark_flags", product.get("nutrition_benchmark_flags")
    )
    components.render_chips(
        flag_labels,
        kind="benchmark",
        empty_text="No sugar, fat, saturated fat, or salt value above the selected reference threshold.",
    )
    components.caption(
        "Uses UK front-of-pack nutrition thresholds as a comparison reference across products. "
        "These flags are not a legal assessment, health-risk assessment, or product recommendation."
    )

    # ── 7. Claim–reference intersections (only when present) ────────
    intersections_raw = product.get("claim_benchmark_intersections")
    if not _missing(intersections_raw) and str(intersections_raw).strip():
        components.section_label("Claim–reference intersections")
        intersection_list = [s.strip() for s in str(intersections_raw).split("|") if s.strip()]
        components.render_chips(intersection_list, kind="neutral")
        components.caption(
            "Shows where a detected claim or positioning signal co-occurs with a nutrition, "
            "ingredient, or processing reference point. Co-occurrence only; it does not mean "
            "the claim is false or misleading."
        )

    # ── 8. Positioning signal score ─────────────────────────────────
    components.section_label("Positioning signal score")
    gap = product.get("positioning_composition_gap")
    gap_band = product.get("positioning_composition_gap_band")
    if _missing(gap) or _missing(gap_band):
        st.markdown(
            '<div class="fbpr-empty-note">Not available for this product because pack-image '
            "claim extraction is not available or did not produce a usable result.</div>",
            unsafe_allow_html=True,
        )
    else:
        gap_num = _to_float(gap)
        if gap_num is not None:
            st.markdown(
                f'<span class="fbpr-mono">{gap_band} ({gap_num:.0f}/100)</span>',
                unsafe_allow_html=True,
            )
        with st.expander("How to read this score"):
            st.markdown(
                "This score combines three components:\n\n"
                "1. **Ingredient-processing markers** — computed from the ingredient list "
                "regardless of any claim on pack. A product with a high-marker ingredient "
                "list contributes to this score even if it makes no front-of-pack claims.\n\n"
                "2. **Positioning weight** — the strength of detected front-of-pack claims, "
                "where available. No claims found means this component is zero.\n\n"
                "3. **Composition context** — only active when claims are present; combines "
                "Nutri-Score tier and processing-level signals to assess whether the claimed "
                "positioning aligns with the broader nutritional and processing profile.\n\n"
                "**What this score is not:** It is not a claim-verification tool, a health "
                "verdict, a misleadingness score, or a legal compliance indicator. A high "
                "score means the product has strong ingredient-processing signals and/or "
                "significant front-of-pack positioning — not that it is misleading. "
                "Interpretation requires reading all three components separately. "
                "See the Methodology tab for the full formula and known limitations."
            )


# ─────────────────────────────────────────────────────────────────────
# Page body
# ─────────────────────────────────────────────────────────────────────

components.inject_base_css()
components.render_header(
    "Product Explorer",
    "Search products, filter by positioning signals, and inspect the evidence behind each product.",
)

if not db.database_exists():
    st.info(
        "No local database found yet at `database/positioning_radar.db`. Run the "
        "core pipeline first — see the README's \"How to run\" section "
        "(`ingest.py` → `clean.py` → `analyze.py` → `load.py`, then `tag_claims.py` "
        "for the claim taxonomy this page uses)."
    )
    st.stop()

# ── Sidebar filters ──────────────────────────────────────────────────
# Order follows CPG professional mental model:
# Category → Market → Company → Brand → Claim signals → Nutrition
with st.sidebar:
    st.subheader("Filters")

    text = st.text_input("Search product or brand")
    options = db.get_filter_options()
    company_brand_map = db.get_company_brand_map()

    # ── 1. Category ───────────────────────────────────────────────────
    categories = st.multiselect("Category", options["query_category"])

    # ── 2. Market / region ────────────────────────────────────────────
    # Only shows markets for which we have full-coverage downloads.
    # Adding a new market = add its region code to DOWNLOAD_SCOPE_REGIONS
    # in shared/db.py and re-run bootstrap.py for that market.
    region_options = db.get_region_options()
    region_label_to_code = {label: code for code, label in region_options}
    selected_region_labels = st.multiselect(
        "Market / region",
        [label for _, label in region_options],
        help=(
            "Filters to products sold in this market, based on Open Food Facts "
            "country tags. Only markets with full-coverage downloads are shown. "
            "Current scope: France, UK & Ireland, US & Canada."
        ),
    )
    selected_region_codes = [
        region_label_to_code[label] for label in selected_region_labels
    ]

    # ── 3. Company / owner ────────────────────────────────────────────
    # Selecting a company narrows the Brand dropdown to that company's
    # known brands. "Other" shows brands not mapped to any company.
    # Brand can always be used independently without selecting a company.
    all_companies = sorted(company_brand_map.keys())
    selected_companies = st.multiselect(
        "Company / owner",
        all_companies + [db.COMPANY_OTHER_LABEL],
        help=(
            "Filter by parent company. Selecting a company pre-fills the "
            "Brand dropdown with that company's known brands. "
            "'Other / not mapped' shows brands without a company match. "
            "Based on data/reference/company_brand_mapping.csv."
        ),
    )

    other_selected = db.COMPANY_OTHER_LABEL in selected_companies
    real_companies  = [c for c in selected_companies if c != db.COMPANY_OTHER_LABEL]

    # ── 4. Brand ──────────────────────────────────────────────────────
    # Options depend on both Category and Company selection:
    # - Company selected  → show only that company's mapped brands
    # - "Other" selected  → show all brands (user picks from unmapped ones)
    # - No company        → show all brands filtered by selected categories
    if real_companies and not other_selected:
        company_pool = sorted({
            b for c in real_companies for b in company_brand_map.get(c, [])
        })
        brand_selection = st.multiselect(
            "Brand",
            company_pool,
            help="Brands belonging to the selected company. Select to refine further.",
        )
        # Use refinement if made; otherwise the company filter covers all company brands
        selected_company_brands: list[str] = brand_selection if brand_selection else company_pool
        exclude_company_brands: list[str] = []
        direct_brands: list[str] = []

    elif other_selected:
        all_mapped = [b for bl in company_brand_map.values() for b in bl]
        selected_company_brands = []
        exclude_company_brands  = all_mapped
        # Show all brands under selected categories — user picks from the unmapped ones
        available_brands = db.get_brand_options(tuple(categories))
        direct_brands = st.multiselect(
            "Brand",
            available_brands,
            help="Select specific brands from the 'Other' (unmapped) pool.",
        )

    else:
        # No company context — show all brands filtered by selected categories
        selected_company_brands = []
        exclude_company_brands  = []
        available_brands = db.get_brand_options(tuple(categories))
        direct_brands = st.multiselect("Brand", available_brands)

    # ── 5. Claim area ─────────────────────────────────────────────────
    claim_code_to_label = labels.all_options("claim_category_1")
    label_to_claim_code = {v: k for k, v in claim_code_to_label.items()}
    available_claim_labels = [
        claim_code_to_label[c]
        for c in options["claim_category_1"]
        if c in claim_code_to_label
    ]
    selected_claim_labels = st.multiselect(
        "Claim area",
        available_claim_labels,
        help=(
            "Broad claim or positioning territory detected for the product. "
            "Based on pack-image analysis where available, otherwise "
            "ingredient/name-derived signals."
        ),
    )
    selected_claim_codes = [label_to_claim_code[l] for l in selected_claim_labels]

    # ── 6. Claim focus ────────────────────────────────────────────────
    focus_code_to_label = labels.all_options("claim_category_2")
    label_to_focus_code = {v: k for k, v in focus_code_to_label.items()}
    available_focus_labels = [
        focus_code_to_label[c]
        for c in options.get("claim_category_2", [])
        if c in focus_code_to_label
    ]
    selected_focus_labels = st.multiselect(
        "Claim focus",
        available_focus_labels,
        help=(
            "More specific claim topic, such as protein, fibre, vitamins, "
            "no added sugar, organic, sustainability, or heritage."
        ),
    )
    selected_focus_codes = [label_to_focus_code[l] for l in selected_focus_labels]

    # ── 7. Nutri-Score ────────────────────────────────────────────────
    _NUTRISCORE_LABELS = {
        "a": "A — Most favourable profile",
        "b": "B",
        "c": "C",
        "d": "D",
        "e": "E — Least favourable profile",
        "unknown": "UNKNOWN",
        "not-applicable": "NOT APPLICABLE",
        "not_applicable": "NOT APPLICABLE",
    }
    selected_nutriscore = st.multiselect(
        "Nutri-Score",
        options.get("nutriscore_grade", []),
        format_func=lambda g: _NUTRISCORE_LABELS.get(
            str(g).lower(), str(g).upper()
        ),
        help=(
            "External nutrition-profile classification from Open Food Facts. "
            "A is the most favourable profile; E is the least favourable. "
            "Not this tool's recommendation."
        ),
    )

    # ── 8. NOVA group ─────────────────────────────────────────────────
    nova_choices = st.multiselect(
        "NOVA group",
        [1, 2, 3, 4],
        format_func=lambda n: f"{n} — {NOVA_DESCRIPTIONS[n]}",
        help=(
            "External processing-level classification from Open Food Facts. "
            "NOVA 1 means unprocessed or minimally processed; "
            "NOVA 4 means ultra-processed. Not this tool's assessment."
        ),
    )

# ── Query ────────────────────────────────────────────────────────────
total = db.count_products(
    text, categories, direct_brands,
    selected_company_brands, exclude_company_brands,
    selected_region_codes,
    selected_claim_codes, selected_focus_codes,
    nova_choices, selected_nutriscore,
)

if total == 0:
    st.warning("No products match these filters.")
    st.stop()

results = db.search_products(
    text, categories, direct_brands,
    selected_company_brands, exclude_company_brands,
    selected_region_codes,
    selected_claim_codes, selected_focus_codes,
    nova_choices, selected_nutriscore,
    limit=200,
)
shown = len(results)

# ── Result count + instruction ───────────────────────────────────────
if total > shown:
    st.caption(
        f"{total:,} products match — showing the first {shown} rows. "
        "Narrow your filters to inspect a smaller set."
    )
else:
    st.caption(f"{total:,} product{'s' if total != 1 else ''} match.")

st.markdown(
    "Tick one row in the table to view full product details below. "
    "Click column headers to sort."
)

# ── IS table helpers ─────────────────────────────────────────────────
# Averages precomputed once per session from the full products table.
# {(category, region_or_ALL): {metric_key: float}}
_AVG = db.get_category_region_averages()

_COUNTRY_REGION = {
    'France': 'FRANCE',
    'United Kingdom': 'UK_IE', 'Great Britain': 'UK_IE',
    'Ireland': 'UK_IE', 'England': 'UK_IE', 'Scotland': 'UK_IE',
    'United States': 'US_CANADA', 'Canada': 'US_CANADA',
}

def _fmt_is(value, category: str, region: str, metric: str,
            higher_is_good: bool, decimals: int = 1) -> str:
    """Format IS metric: colour circle + absolute value.
    Circle is vs country-category average (🟢 >110%, 🟡 90-110%, 🔴 <90%).
    Direction: higher_is_good=True → high index is green, low is red.
    Energy shown without circle (no clear good/bad direction)."""
    if _missing(value):
        return "—"
    try:
        num_val = float(value)
        num_str = f"{num_val:.{decimals}f}"
    except (TypeError, ValueError):
        return "—"
    avg = (
        _AVG.get((category, region), {}).get(metric)
        or _AVG.get((category, "ALL"), {}).get(metric)
    )
    if avg is None or avg == 0:
        return num_str
    try:
        idx = num_val / avg * 100
    except (TypeError, ZeroDivisionError):
        return num_str
    if idx > 110:
        circle = "🟢" if higher_is_good else "🔴"
    elif idx >= 90:
        circle = "🟡"
    else:
        circle = "🔴" if higher_is_good else "🟢"
    return f"{circle} {num_str}"


# TELLS: pack claim codes → friendly display names.
# Source: pack_claims_found field, written by vision_extract.py.
# Only shown for vision-analyzed products (claim_source = 'vision').
_CLAIM_NAMES: dict[str, str] = {
    "protein_claim": "Protein", "protein": "Protein",
    "fibre_claim": "Fibre", "fiber_claim": "Fibre",
    "fiber": "Fibre", "fibre": "Fibre",
    "prebiotic_claim": "Prebiotic", "probiotic_claim": "Probiotic",
    "immune_claim": "Immune support",
    "fortification_claim": "Vitamins", "vitalite_concept": "Vitamins",
    "vitamin_claim": "Vitamins", "vitamins": "Vitamins",
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
}

def _fmt_positioning(pack_claims_val, claim_source: str) -> str:
    """TELLS column: what the product communicates on pack, vision-only."""
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


# Optional selectable columns: display_name → (db_col_or_None, decimals)
# None db_col means the field is not yet ingested; shows "Not declared".
_OPTIONAL_COLS: dict[str, tuple] = {
    "Protein, g/100g":       ("protein_100g",       1),
    "Fat, g/100g":           ("fat_100g",            1),
    "Saturated fat, g/100g": ("saturated_fat_100g",  1),
    "Carbohydrate, g/100g":  ("carbs_100g",          1),
    "Total sugars, g/100g":  ("sugars_100g",         1),
    "Added sugar, g/100g":   (None,                  1),   # not in DB yet — declared separately in US, rare in EU
    "Fibre, g/100g":         ("fiber_100g",          1),
    "Salt, g/100g":          ("salt_100g",           2),
}

# ── Column selector ────────────────────────────────────────────────────
extra_col_names: list[str] = st.multiselect(
    "Add columns",
    list(_OPTIONAL_COLS.keys()),
    help=(
        "Add per-100g nutritional columns. All values from Open Food Facts — "
        "no calculated scores. Columns with 🟢🟡🔴 are indexed vs the "
        "country-category average; additional columns show absolute values."
    ),
)

# ── Build display columns (IS + TELLS) ────────────────────────────────
display_df = results.copy()
display_df["_region"] = (
    display_df["primary_country"].map(_COUNTRY_REGION).fillna("OTHER")
)

# Per-kcal ratios (computed from raw fields, used for IS columns)
_kcal   = display_df["energy_kcal"].apply(_to_float)
_prot   = display_df["protein_100g"].apply(_to_float)
_fib    = display_df["fiber_100g"].apply(_to_float)
_satfat = display_df["saturated_fat_100g"].apply(_to_float)

display_df["_protein_per_kcal"] = _prot   / _kcal.where(_kcal > 0) * 100
display_df["_fiber_per_kcal"]   = _fib    / _kcal.where(_kcal > 0) * 100
display_df["_satfat_per_kcal"]  = _satfat / _kcal.where(_kcal > 0) * 100

def _build_is_col(df: "pd.DataFrame", val_col: str, metric_key: str,
                  higher_is_good: bool, decimals: int) -> list[str]:
    """Build one IS column as a list of circle + value strings."""
    out = []
    for _, row in df.iterrows():
        cat    = str(row.get("query_category") or "")
        region = str(row.get("_region") or "OTHER")
        out.append(
            _fmt_is(row.get(val_col), cat, region, metric_key,
                    higher_is_good, decimals)
        )
    return out

# Energy: absolute only — establishes density, no evaluative direction
display_df["Energy, kcal/100g"]     = _kcal.apply(
    lambda v: f"{v:.0f}" if v is not None else "—"
)
# IS metrics with colour circle
display_df["Protein, g/100 kcal"]  = _build_is_col(
    display_df, "_protein_per_kcal", "protein_per_kcal", True,  1)
display_df["Fibre, g/100 kcal"]    = _build_is_col(
    display_df, "_fiber_per_kcal",   "fiber_per_kcal",   True,  1)
display_df["Sat. fat, g/100 kcal"] = _build_is_col(
    display_df, "_satfat_per_kcal",  "satfat_per_kcal",  False, 1)
display_df["NOVA"] = display_df["nova_group"].apply(_fmt_nova)

# TELLS: what the product says on pack (vision-analyzed products only)
display_df["Positioning"] = display_df.apply(
    lambda row: _fmt_positioning(
        row.get("pack_claims_found"), row.get("claim_source", "")
    ),
    axis=1,
)

# Additional selectable columns (absolute values, no circle)
for col_name in extra_col_names:
    db_col, decimals = _OPTIONAL_COLS[col_name]
    if db_col is None:
        display_df[col_name] = "Not declared"
    elif db_col in display_df.columns:
        display_df[col_name] = display_df[db_col].apply(
            lambda v, d=decimals: (
                f"{float(v):.{d}f}" if not _missing(v) else "—"
            )
        )
    else:
        display_df[col_name] = "—"

# ── Export CSV (numeric, no emoji — clean for Excel / Python) ─────────
export_core = {
    "query_category":      "Category",
    "primary_brand":       "Brand",
    "product_name":        "Product",
    "energy_kcal":         "Energy, kcal/100g",
    "_protein_per_kcal":   "Protein, g/100 kcal",
    "_fiber_per_kcal":     "Fibre, g/100 kcal",
    "_satfat_per_kcal":    "Sat. fat, g/100 kcal",
    "nova_group":          "NOVA group",
    "nutriscore_grade":    "Nutri-Score",
    "Positioning":         "Positioning (pack claims)",
}
export_extra = {n: n for n in extra_col_names if n in display_df.columns}
all_export_cols = {**export_core, **export_extra}
export_df = (
    display_df[[c for c in all_export_cols if c in display_df.columns]]
    .rename(columns=all_export_cols)
)
csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    label="Download visible rows as CSV",
    data=csv_bytes,
    file_name="food_positioning_radar_filtered_products.csv",
    mime="text/csv",
    help="Exports numeric values (no emoji) for analysis in Excel or Python.",
)
st.caption(
    "Source data: Open Food Facts (ODbL). Export for analysis — please attribute."
)

# ── Table ─────────────────────────────────────────────────────────────
default_table_cols = [
    ("query_category",       "Category"),
    ("primary_brand",        "Brand"),
    ("product_name",         "Product"),
    ("Energy, kcal/100g",    "Energy, kcal/100g"),
    ("Protein, g/100 kcal",  "Protein, g/100 kcal"),
    ("Fibre, g/100 kcal",    "Fibre, g/100 kcal"),
    ("Sat. fat, g/100 kcal", "Sat. fat, g/100 kcal"),
    ("NOVA",                 "NOVA"),
    ("Positioning",          "Positioning"),
]
extra_table_cols = [(n, n) for n in extra_col_names if n in display_df.columns]
all_table_cols   = default_table_cols + extra_table_cols

src_cols  = [s for s, _ in all_table_cols if s in display_df.columns]
disp_cols = [d for s, d in all_table_cols if s in display_df.columns]
table_view = display_df[src_cols].copy()
table_view.columns = disp_cols

event = st.dataframe(
    table_view,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
)
selected_rows = event.selection["rows"]

if not selected_rows:
    st.info("Tick one row above to view full product details.")
else:
    selected_product = results.iloc[selected_rows[0]].to_dict()
    render_product_card(selected_product)
