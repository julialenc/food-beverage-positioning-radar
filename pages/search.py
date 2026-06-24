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
        return "—"
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
with st.sidebar:
    st.subheader("Filters")

    text = st.text_input("Search product or brand")
    options = db.get_filter_options()

    categories = st.multiselect("Category", options["query_category"])
    brands = st.multiselect("Brand", options["primary_brand"])

    # ── Company / owner filter ───────────────────────────────────────
    company_brand_map = db.get_company_brand_map()
    companies_sorted  = sorted(company_brand_map.keys())
    selected_companies = st.multiselect(
        "Company / owner",
        companies_sorted,
        help=(
            "Parent company that owns the brand. One company may own "
            "multiple brands across categories. Based on "
            "data/reference/company_brand_mapping.csv."
        ),
    )
    # Translate selected companies → flat list of primary_brand_db values
    # for the IN clause. Empty list means no company filter applied.
    selected_company_brands: list[str] = []
    for company in selected_companies:
        selected_company_brands.extend(company_brand_map.get(company, []))

    # ── Market / region filter ────────────────────────────────────────
    region_options = db.get_region_options()  # [(code, label), ...]
    region_label_to_code = {label: code for code, label in region_options}
    region_labels = [label for _, label in region_options]
    selected_region_labels = st.multiselect(
        "Market / region",
        region_labels,
        help=(
            "Markets where this product has been observed. A product can "
            "appear in multiple regions. Based on OFF country tags grouped "
            "into regions via data/country_region_mapping.csv."
        ),
    )
    selected_region_codes = [
        region_label_to_code[label] for label in selected_region_labels
    ]

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
    text, categories, brands,
    selected_company_brands, selected_region_codes,
    selected_claim_codes, selected_focus_codes,
    nova_choices, selected_nutriscore,
)

if total == 0:
    st.warning("No products match these filters.")
    st.stop()

results = db.search_products(
    text, categories, brands,
    selected_company_brands, selected_region_codes,
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

# ── Build display columns ─────────────────────────────────────────────
display_df = results.copy()

valid_claim_codes = set(labels.all_options("claim_category_1").keys())
bad_claim_mask = (
    display_df["claim_category_1"].notna()
    & (display_df["claim_category_1"].astype(str).str.strip() != "")
    & ~display_df["claim_category_1"].astype(str).isin(valid_claim_codes)
)
bad_claim_count = int(bad_claim_mask.sum())
if bad_claim_count:
    st.warning(
        f"{bad_claim_count} product row(s) contain an unmapped positioning-category code. "
        "They are shown with a blank display label below. Run "
        "`pipeline/validate_tags.py` and `pipeline/verify_schema.py` before "
        "publishing or exporting final results."
    )

display_df["Claim area"] = display_df["claim_category_1"].apply(
    lambda c: labels.safe_label_for("claim_category_1", c)
)
display_df["Claim focus"] = display_df["claim_category_2"].apply(
    lambda c: (
        "—"
        if _missing(c) or str(c).strip().lower() in ("none", "nan", "")
        else labels.safe_label_for("claim_category_2", c)
    )
)
display_df["Nutri-Score"] = display_df["nutriscore_grade"].apply(
    lambda g: str(g).upper() if not _missing(g) else "—"
)
display_df["NOVA"] = display_df["nova_group"].apply(_fmt_nova)
display_df["Positioning signal"] = display_df["positioning_composition_gap_band"].apply(
    lambda v: v if not _missing(v) else "Not analyzed"
)

# ── Export CSV ────────────────────────────────────────────────────────
export_cols = {
    "query_category": "Category",
    "primary_brand":  "Brand",
    "product_name":   "Product",
    "Claim area":     "Claim area",
    "Claim focus":    "Claim focus",
    "Nutri-Score":    "Nutri-Score",
    "NOVA":           "NOVA",
    "Positioning signal": "Positioning signal",
}
export_df = display_df[list(export_cols.keys())].rename(columns=export_cols)
csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    label="Download visible rows as CSV",
    data=csv_bytes,
    file_name="food_positioning_radar_filtered_products.csv",
    mime="text/csv",
    help="Downloads the currently visible table rows with display-ready labels.",
)
st.caption(
    "Source data: Open Food Facts. Export is for analysis and should be used "
    "with attribution and respect for Open Food Facts licensing terms."
)

# ── Table ─────────────────────────────────────────────────────────────
table_cols = {
    "query_category":    "Category",
    "primary_brand":     "Brand",
    "product_name":      "Product",
    "Claim area":        "Claim area",
    "Claim focus":       "Claim focus",
    "Nutri-Score":       "Nutri-Score",
    "NOVA":              "NOVA",
    "Positioning signal": "Positioning signal",
}
table_view = display_df[list(table_cols.keys())].rename(columns=table_cols)

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
