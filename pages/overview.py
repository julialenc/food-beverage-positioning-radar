"""
Market Overview.

MVP scope: a snapshot of the observable product universe, not a sales-,
share-, or trend-reporting tool. Three sections:
  1. Product Landscape         — individual products across nutrition metrics
  2. Product Profile Landscape — cumulative AND-condition funnel
  3. By Region                 — fixed cross-region/category benchmark table

OFF data only. No OCR/LLM/claim data anywhere on this page — that
distinction lives in Product Explorer instead (see docs/ADR.md).

Market scope (Region, Category) is a mandatory, single-select, page-level
filter shared by sections 1 and 2 — deliberately different from Product
Explorer's optional multiselect filters. Mixing regions or categories on
one comparative view doesn't produce a coherent product cloud (nutrition
profiles differ too much by category, and OFF coverage differs too much
by region).

Fixed default view (France x Snacks) on first load, not a remembered
last-session choice — kept deliberately simple per this being a
single/limited-user tool right now, not a commercial product.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from shared import components, db
from shared.beverage_segments import (
    PREPARATION_ALCOHOL_SEGMENT,
    READY_TO_DRINK_SEGMENT,
    SEGMENT_LABELS,
    UNKNOWN_BEVERAGE_SEGMENT,
)

_SNAPSHOT_LABEL = "August 2026"
_CATEGORY_LABELS = {
    "beverages": "Beverages",
    "cereals": "Cereals",
    "dairies": "Dairy",
    "snacks": "Snacks",
}
_COMPANY_OTHER_LABELS = {db.COMPANY_OTHER_LABEL, db.COMPANY_MANUAL_REVIEW_LABEL}
_NUTRITION_COLS = [
    "energy_kcal", "protein_100g", "fiber_100g", "sugars_100g",
    "saturated_fat_100g", "salt_100g",
]
_DRILL_NUTRITION_COLS = [
    "energy_kcal", "protein_100g", "fiber_100g", "sugars_100g",
    "saturated_fat_100g", "salt_100g",
]
_NOVA_DESCRIPTIONS = {
    1: "Unprocessed / minimally processed",
    2: "Processed culinary ingredients",
    3: "Processed foods",
    4: "Ultra-processed foods",
}
_METRIC_LABELS = {
    "energy_kcal": "Energy, kcal/100g",
    "protein_100g": "Protein, g/100g",
    "fiber_100g": "Fibre, g/100g",
    "sugars_100g": "Sugars, g/100g",
    "saturated_fat_100g": "Saturated fat, g/100g",
    "salt_100g": "Salt, g/100g",
}
_REFERENCE_HELP = (
    "↑ above selected country-category reference    "
    "≈ within ±10% of selected country-category reference    "
    "↓ below selected country-category reference"
)
_BEVERAGE_SEGMENT_ALL_LABEL = "All beverages"
_BEVERAGE_SEGMENT_CHOICES = [
    _BEVERAGE_SEGMENT_ALL_LABEL,
    SEGMENT_LABELS[READY_TO_DRINK_SEGMENT],
    SEGMENT_LABELS[PREPARATION_ALCOHOL_SEGMENT],
    SEGMENT_LABELS[UNKNOWN_BEVERAGE_SEGMENT],
]
_BEVERAGE_SEGMENT_BY_LABEL = {
    SEGMENT_LABELS[READY_TO_DRINK_SEGMENT]: READY_TO_DRINK_SEGMENT,
    SEGMENT_LABELS[PREPARATION_ALCOHOL_SEGMENT]: PREPARATION_ALCOHOL_SEGMENT,
    SEGMENT_LABELS[UNKNOWN_BEVERAGE_SEGMENT]: UNKNOWN_BEVERAGE_SEGMENT,
}


def _category_label(category: str) -> str:
    return _CATEGORY_LABELS.get(str(category), str(category).replace("_", " ").title())


def _pct(numerator: int | float, denominator: int | float) -> str:
    if not denominator:
        return "—"
    return f"{numerator / denominator:.0%}"


def _fmt_num(value, decimals: int = 1, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{decimals}f}{suffix}"


def _fmt_indexed(value, reference, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    text = f"{num:.{decimals}f}"
    if reference is None or pd.isna(reference) or reference == 0:
        return text
    idx = num / float(reference) * 100
    if idx > 110:
        arrow = "↑"
    elif idx >= 90:
        arrow = "≈"
    else:
        arrow = "↓"
    return f"{text} {arrow}"


def _nova_label(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        nova = int(float(value))
    except (TypeError, ValueError):
        return "—"
    return f"{nova} - {_NOVA_DESCRIPTIONS.get(nova, 'Not determined')}"


def _coverage_mask(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    if df[col].dtype == object:
        return df[col].notna() & (df[col].astype(str).str.strip() != "")
    return df[col].notna()


def _nutrition_any_mask(df: pd.DataFrame) -> pd.Series:
    available_cols = [c for c in _NUTRITION_COLS if c in df.columns]
    if not available_cols:
        return pd.Series(False, index=df.index)
    return df[available_cols].notna().any(axis=1)


def _mapped_company_mask(df: pd.DataFrame) -> pd.Series:
    return (
        _coverage_mask(df, "company")
        & ~df["company"].isin(_COMPANY_OTHER_LABELS)
    )


def _metric_card(label: str, value: str, help_text: str | None = None) -> None:
    st.metric(label, value, help=help_text)


def _nutriscore_distribution(df: pd.DataFrame) -> str:
    ns = df["nutriscore_grade"].dropna().astype(str).str.upper()
    ns = ns[ns.isin(["A", "B", "C", "D", "E"])]
    if ns.empty:
        return "—"
    counts = ns.value_counts().reindex(["A", "B", "C", "D", "E"]).dropna().astype(int)
    total = counts.sum()
    return " · ".join(f"{grade}: {count / total:.0%}" for grade, count in counts.items())


def _reference_values(df: pd.DataFrame) -> dict[str, float]:
    return {col: df[col].median() for col in _DRILL_NUTRITION_COLS if col in df.columns}


def _column_help_config(columns: list[str]) -> dict:
    return {
        col: st.column_config.TextColumn(col, help=_REFERENCE_HELP)
        for col in columns
        if col in _METRIC_LABELS.values() or col.startswith("Median ")
    }


def _brand_summary(df: pd.DataFrame, references: dict[str, float]) -> pd.DataFrame:
    rows = []
    for (company, brand), grp in df.groupby(["company", "primary_brand"], dropna=False):
        nova_available = grp["nova_group"].notna().sum()
        nova4 = (grp["nova_group"] == 4).sum()
        rows.append({
            "Company / owner": company or "—",
            "Brand": brand or "—",
            "Observed records": len(grp),
            "Median energy, kcal/100g": grp["energy_kcal"].median(),
            "Median protein, g/100g": grp["protein_100g"].median(),
            "Median fibre, g/100g": grp["fiber_100g"].median(),
            "Median sugars, g/100g": grp["sugars_100g"].median(),
            "Median saturated fat, g/100g": grp["saturated_fat_100g"].median(),
            "Median salt, g/100g": grp["salt_100g"].median(),
            "NOVA 4": f"{_pct(nova4, nova_available)} ({nova4:,}/{nova_available:,})",
            "Nutrition data coverage": _pct(_nutrition_any_mask(grp).sum(), len(grp)),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    format_map = {
        "Median energy, kcal/100g": ("energy_kcal", 0),
        "Median protein, g/100g": ("protein_100g", 1),
        "Median fibre, g/100g": ("fiber_100g", 1),
        "Median sugars, g/100g": ("sugars_100g", 1),
        "Median saturated fat, g/100g": ("saturated_fat_100g", 1),
        "Median salt, g/100g": ("salt_100g", 2),
    }
    for display_col, (source_col, decimals) in format_map.items():
        out[display_col] = out[display_col].map(
            lambda v, ref=references.get(source_col), d=decimals: _fmt_indexed(v, ref, d)
        )
    return out.sort_values("Brand", key=lambda s: s.astype(str).str.lower())


def _product_table(df: pd.DataFrame, references: dict[str, float], limit: int = 250) -> pd.DataFrame:
    cols = {
        "product_name": "Product",
        "primary_brand": "Brand",
        "company": "Company / owner",
        "energy_kcal": "Energy, kcal/100g",
        "protein_100g": "Protein, g/100g",
        "fiber_100g": "Fibre, g/100g",
        "sugars_100g": "Sugars, g/100g",
        "saturated_fat_100g": "Saturated fat, g/100g",
        "salt_100g": "Salt, g/100g",
        "nova_group": "NOVA",
        "nutriscore_grade": "Nutri-Score",
    }
    view = df[[c for c in cols if c in df.columns]].head(limit).rename(columns=cols)
    format_map = {
        "Energy, kcal/100g": ("energy_kcal", 0),
        "Protein, g/100g": ("protein_100g", 1),
        "Fibre, g/100g": ("fiber_100g", 1),
        "Sugars, g/100g": ("sugars_100g", 1),
        "Saturated fat, g/100g": ("saturated_fat_100g", 1),
        "Salt, g/100g": ("salt_100g", 2),
    }
    for display_col, (source_col, decimals) in format_map.items():
        if display_col in view.columns:
            view[display_col] = view[display_col].map(
                lambda v, ref=references.get(source_col), d=decimals: _fmt_indexed(v, ref, d)
            )
    if "NOVA" in view.columns:
        view["NOVA"] = view["NOVA"].map(_nova_label)
    if "Nutri-Score" in view.columns:
        view["Nutri-Score"] = view["Nutri-Score"].map(
            lambda v: "—" if pd.isna(v) or str(v).strip() == "" else str(v).upper()
        )
    return view


def _render_product_detail(product: pd.Series) -> None:
    st.markdown("**Selected product details**")
    img_col, info_col = st.columns([1, 2.2])
    with img_col:
        image_url = components.product_image_url(product.get("image_url"))
        components.render_product_pack_image(
            image_url, product_name=product.get("product_name") or ""
        )
    with info_col:
        st.markdown(f"**{product.get('product_name') or 'Unnamed product'}**")
        st.caption(
            f"{product.get('primary_brand') or 'Unknown brand'} · "
            f"{product.get('company') or db.COMPANY_OTHER_LABEL}"
        )
        detail_cols = st.columns(3)
        detail_cols[0].metric("Energy, kcal/100g", _fmt_num(product.get("energy_kcal"), 0))
        detail_cols[1].metric("Protein, g/100g", _fmt_num(product.get("protein_100g"), 1))
        detail_cols[2].metric("Sugars, g/100g", _fmt_num(product.get("sugars_100g"), 1))
        detail_cols = st.columns(3)
        detail_cols[0].metric("Saturated fat, g/100g", _fmt_num(product.get("saturated_fat_100g"), 1))
        detail_cols[1].metric("Salt, g/100g", _fmt_num(product.get("salt_100g"), 2))
        detail_cols[2].metric("NOVA", _nova_label(product.get("nova_group")))
        ns = product.get("nutriscore_grade")
        st.caption(f"Nutri-Score: {'—' if pd.isna(ns) else str(ns).upper()}")
    ingredients = product.get("ingredients_text")
    if ingredients is not None and not pd.isna(ingredients) and str(ingredients).strip():
        with st.expander("Ingredient text"):
            st.write(str(ingredients))


def _brand_company_label(df: pd.DataFrame) -> str:
    companies = [
        str(c) for c in df["company"].dropna().unique()
        if str(c).strip()
    ]
    if not companies:
        return "—"
    companies = sorted(companies, key=lambda c: c.lower())
    if len(companies) <= 2:
        return " · ".join(companies)
    return " · ".join(companies[:2]) + f" · +{len(companies) - 2} more"


def _brand_option_match(brand_options: list[str], preferred: str, fallback_index: int) -> str:
    preferred_norm = preferred.strip().lower()
    for brand in brand_options:
        if str(brand).strip().lower() == preferred_norm:
            return brand
    if not brand_options:
        return ""
    return brand_options[min(fallback_index, len(brand_options) - 1)]


def _brand_compare_product_table(
    df: pd.DataFrame,
    references: dict[str, float],
    limit: int = 100,
) -> pd.DataFrame:
    view = _product_table(df, references, limit=limit)
    return view.drop(
        columns=[c for c in ["Brand", "Company / owner"] if c in view.columns]
    )


def _render_compact_product_detail(product: pd.Series) -> None:
    st.markdown(f"**{product.get('product_name') or 'Unnamed product'}**")
    metric_cols = st.columns(2)
    metric_cols[0].metric("Energy, kcal/100g", _fmt_num(product.get("energy_kcal"), 0))
    metric_cols[1].metric("Protein, g/100g", _fmt_num(product.get("protein_100g"), 1))
    metric_cols = st.columns(2)
    metric_cols[0].metric("Fibre, g/100g", _fmt_num(product.get("fiber_100g"), 1))
    metric_cols[1].metric("Sugars, g/100g", _fmt_num(product.get("sugars_100g"), 1))
    metric_cols = st.columns(2)
    metric_cols[0].metric("Saturated fat, g/100g", _fmt_num(product.get("saturated_fat_100g"), 1))
    metric_cols[1].metric("Salt, g/100g", _fmt_num(product.get("salt_100g"), 2))
    st.caption(
        f"NOVA: {_nova_label(product.get('nova_group'))} · "
        f"Nutri-Score: {'—' if pd.isna(product.get('nutriscore_grade')) else str(product.get('nutriscore_grade')).upper()}"
    )
    ingredients = product.get("ingredients_text")
    if ingredients is not None and not pd.isna(ingredients) and str(ingredients).strip():
        with st.expander("Ingredient text"):
            st.write(str(ingredients))


def _render_brand_compare_panel(
    label: str,
    company_options: list[str],
    default_brand: str,
    df_market: pd.DataFrame,
    references: dict[str, float],
) -> None:
    key_base = label.lower().replace(" ", "_")
    all_companies_label = "All companies / owners"
    select_brand_label = "Select a brand"

    company_key = f"bc_company_{key_base}"
    brand_key = f"bc_brand_{key_base}"

    if st.session_state.get(company_key) not in ([all_companies_label] + company_options):
        st.session_state[company_key] = all_companies_label

    company = st.selectbox(
        f"{label}: Company / owner — optional",
        [all_companies_label] + company_options,
        key=company_key,
    )

    if company == all_companies_label:
        brand_base = df_market
    else:
        brand_base = df_market[df_market["company"] == company]

    brand_options = sorted(
        brand_base["primary_brand"].dropna().unique(),
        key=lambda b: str(b).lower(),
    )

    brand_choices = brand_options if company == all_companies_label else [select_brand_label] + brand_options
    if st.session_state.get(brand_key) not in brand_choices:
        st.session_state[brand_key] = (
            default_brand if default_brand in brand_choices else brand_choices[0]
        )

    brand = st.selectbox(
        f"{label}: Brand",
        brand_choices,
        key=brand_key,
    )

    if brand == select_brand_label:
        st.caption("Select a brand to display observed records.")
        return

    brand_df = brand_base[brand_base["primary_brand"] == brand].copy()
    if brand_df.empty:
        st.caption("Select a brand to display observed records.")
        return

    st.markdown(f"### {brand}")
    st.caption(f"Company / owner: {_brand_company_label(brand_df)}")

    total_records = len(brand_df)
    nutrition_count = int(_nutrition_any_mask(brand_df).sum())
    nova_available = int(brand_df["nova_group"].notna().sum())
    nova4 = int((brand_df["nova_group"] == 4).sum())

    metric_cols = st.columns(2)
    metric_cols[0].metric("Observed records", f"{total_records:,}")
    metric_cols[1].metric("Nutrition data coverage", _pct(nutrition_count, total_records))
    metric_cols = st.columns(2)
    metric_cols[0].metric(
        "Median energy, kcal/100g",
        _fmt_indexed(brand_df["energy_kcal"].median(), references.get("energy_kcal"), 0),
    )
    metric_cols[1].metric(
        "Median protein, g/100g",
        _fmt_indexed(brand_df["protein_100g"].median(), references.get("protein_100g"), 1),
    )
    metric_cols = st.columns(2)
    metric_cols[0].metric(
        "Median fibre, g/100g",
        _fmt_indexed(brand_df["fiber_100g"].median(), references.get("fiber_100g"), 1),
    )
    metric_cols[1].metric(
        "Median sugars, g/100g",
        _fmt_indexed(brand_df["sugars_100g"].median(), references.get("sugars_100g"), 1),
    )
    metric_cols = st.columns(2)
    metric_cols[0].metric(
        "Median saturated fat, g/100g",
        _fmt_indexed(
            brand_df["saturated_fat_100g"].median(),
            references.get("saturated_fat_100g"),
            1,
        ),
    )
    metric_cols[1].metric(
        "Median salt, g/100g",
        _fmt_indexed(brand_df["salt_100g"].median(), references.get("salt_100g"), 2),
    )
    metric_cols = st.columns(2)
    metric_cols[0].metric("NOVA 4", f"{_pct(nova4, nova_available)} ({nova4:,}/{nova_available:,})")
    metric_cols[1].metric("Nutri-Score", _nutriscore_distribution(brand_df))

    st.markdown("**Product records**")
    product_records = brand_df.head(100)
    product_view = _brand_compare_product_table(brand_df, references, limit=100)
    product_event = st.dataframe(
        product_view,
        hide_index=True,
        width="stretch",
        column_config=_column_help_config(list(product_view.columns)),
        on_select="rerun",
        selection_mode="single-row",
        key=f"bc_products_{label.lower().replace(' ', '_')}_{brand}",
    )
    if hasattr(product_event, "selection"):
        selected_rows = product_event.selection.rows
    else:
        selected_rows = product_event.get("selection", {}).get("rows", [])
    if selected_rows:
        with st.expander("Selected product detail", expanded=True):
            _render_compact_product_detail(product_records.iloc[selected_rows[0]])
    if len(brand_df) > 100:
        st.caption(f"Showing 100 of {len(brand_df):,} product records for {brand}.")


components.inject_base_css()
components.render_header(
    "Market Overview",
    (
        "Explore observed Open Food Facts product records by selected "
        "country-category scope; counts are not sales-weighted, "
        "distribution-weighted, or market-share estimates."
    ),
)
st.warning(
    "BETA version. This launch build uses Open Food Facts data and "
    "rule-based cleaning and mapping layers. Some records may remain "
    "incomplete or imperfect. Page refreshes and large filter changes may "
    "take up to 90 seconds.",
    icon="ℹ️",
)

if not db.database_exists():
    st.info(
        "No app database found yet. Run the pipeline or provide the public MVP "
        "database artifact — see the README."
    )
    st.stop()

# ── Section navigation (left pane) ───────────────────────────────────────────
# Shows name + subtitle for every planned section so a first-time visitor
# sees what's available; a returning visitor clicks instead of scrolling.
_SECTIONS = [
    {
        "key": "category_report",
        "sidebar_label": "1. Category Report",
        "view_label": (
            "1. CATEGORY REPORT. Country-category landscape; drill into "
            "companies, brands, and products."
        ),
        "caption": (
            "Country-category landscape; drill into companies, brands, and products."
        ),
    },
    {
        "key": "brand_compare",
        "sidebar_label": "2. Brand Compare",
        "view_label": (
            "2. BRAND COMPARE. Compare two brands side by side within the "
            "selected country-category base."
        ),
        "caption": "Compare two brands side by side within the selected country-category base.",
    },
    {
        "key": "product_map",
        "sidebar_label": "3. Product Map",
        "view_label": (
            "3. PRODUCT MAP. Map observed product records across selected "
            "nutrition dimensions."
        ),
        "caption": "Map observed product records across selected nutrition dimensions.",
    },
]
_SECTION_BY_KEY = {section["key"]: section for section in _SECTIONS}
_CATEGORY_REPORT_SECTION = "category_report"
_BRAND_COMPARE_SECTION = "brand_compare"
_PRODUCT_MAP_SECTION = "product_map"

if (
    "mo_active_section" not in st.session_state
    or st.session_state["mo_active_section"] not in _SECTION_BY_KEY
):
    st.session_state["mo_active_section"] = _CATEGORY_REPORT_SECTION

with st.sidebar:
    st.markdown("**Market Overview views**")
    for i, section in enumerate(_SECTIONS, start=1):
        is_active = st.session_state["mo_active_section"] == section["key"]
        if st.button(
            f"{'▶ ' if is_active else ''}{section['sidebar_label']}",
            key=f"mo_nav_{i}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state["mo_active_section"] = section["key"]
            st.rerun()
        st.caption(section["caption"])

active_section = st.session_state["mo_active_section"]

# ── Fixed defaults for first load ────────────────────────────────────────────
_DEFAULT_REGION_CODE = "FRANCE"
_DEFAULT_CATEGORY    = "snacks"

region_options       = db.get_region_options()  # [(code, label), ...]
region_codes         = [code for code, _ in region_options]
region_labels        = [label for _, label in region_options]
region_code_to_label = dict(region_options)

category_options = db.get_filter_options()["query_category"]

st.subheader("Select scope")
st.caption(
    "Initial load may take around 30-90 seconds because the app prepares the "
    "selected country-category dataset for drill-down. After the first load, "
    "filters are usually faster."
)
col_region, col_category, col_view = st.columns([1, 1, 1.35])
with col_region:
    default_region_idx = (
        region_codes.index(_DEFAULT_REGION_CODE)
        if _DEFAULT_REGION_CODE in region_codes else 0
    )
    region_label = st.selectbox(
        "Country / market", region_labels, index=default_region_idx, key="mo_region",
    )
    region_code = {v: k for k, v in region_code_to_label.items()}[region_label]
with col_category:
    default_category_idx = (
        category_options.index(_DEFAULT_CATEGORY)
        if _DEFAULT_CATEGORY in category_options else 0
    )
    category = st.selectbox(
        "Category", category_options, index=default_category_idx, key="mo_category",
    )
with col_view:
    report_labels = [section["view_label"] for section in _SECTIONS]
    report_keys = [section["key"] for section in _SECTIONS]
    report_descriptions = {section["view_label"]: section["caption"] for section in _SECTIONS}
    active_view_label = _SECTION_BY_KEY[active_section]["view_label"]
    if st.session_state.get("mo_report") not in report_labels:
        st.session_state["mo_report"] = active_view_label
    report_label = st.selectbox(
        "View",
        report_labels,
        index=report_labels.index(active_view_label),
        key="mo_report",
    )
    selected_section_key = report_keys[report_labels.index(report_label)]
    if selected_section_key != st.session_state["mo_active_section"]:
        st.session_state["mo_active_section"] = selected_section_key
        st.rerun()
    if selected_section_key != _CATEGORY_REPORT_SECTION:
        st.caption(report_descriptions.get(report_label, ""))

# ── Load the region x category population (cached; shared by all 3 sections) ─
df_market = db.get_market_products(category, region_code)
df_market_unsegmented = df_market
selected_segment = None
if category == "beverages":
    st.subheader("Beverage view segment")
    if st.session_state.get("mo_beverage_segment") not in _BEVERAGE_SEGMENT_CHOICES:
        st.session_state["mo_beverage_segment"] = SEGMENT_LABELS[
            READY_TO_DRINK_SEGMENT
        ]
    beverage_segment_label = st.selectbox(
        "Beverage view segment",
        _BEVERAGE_SEGMENT_CHOICES,
        index=_BEVERAGE_SEGMENT_CHOICES.index(
            st.session_state.get(
                "mo_beverage_segment",
                SEGMENT_LABELS[READY_TO_DRINK_SEGMENT],
            )
        ),
        key="mo_beverage_segment",
    )
    st.caption(
        "Beverages are split into ready-to-drink products and beverage "
        "preparations / alcohol because these product forms are not directly "
        "comparable in nutrition charts."
    )
    st.caption(
        "Beverage segmentation is an MVP classification. In the MVP regions, "
        "58,265 records are classified as ready-to-drink beverages, 39,886 as "
        "beverage preparations / alcohol, and 11,218 remain unclassified. "
        "Unknown beverage records are work in progress and should not be "
        "interpreted as a separate market segment."
    )
    selected_segment = _BEVERAGE_SEGMENT_BY_LABEL.get(beverage_segment_label)
    if selected_segment:
        df_market = df_market[
            df_market["beverage_view_segment"] == selected_segment
        ].copy()
else:
    st.session_state["mo_beverage_segment"] = SEGMENT_LABELS[
        READY_TO_DRINK_SEGMENT
    ]

selected_base = f"{region_label} · {_category_label(category)}"
if category == "beverages" and selected_segment:
    selected_base = f"{selected_base} · {beverage_segment_label}"
st.caption(
    f"Current data snapshot: {_SNAPSHOT_LABEL} · "
    f"{len(df_market):,} products in selected scope"
)
if category == "beverages" and selected_segment:
    st.caption(
        f"Filtered from {len(df_market_unsegmented):,} beverages in the selected "
        f"country / market."
    )
st.markdown(f"**Selected scope: {selected_base}**")

if active_section == _BRAND_COMPARE_SECTION:
    st.markdown("### 2. Brand Compare")
    st.info(
        "Select any two brands in the selected country-category base and "
        "compare their observed records side by side; values are not "
        "sales-weighted or market-share estimates."
    )

    brand_options = sorted(
        df_market["primary_brand"].dropna().unique(),
        key=lambda b: str(b).lower(),
    )
    if len(brand_options) < 2:
        st.info("At least two brands are needed in the selected scope for Brand Compare.")
        st.stop()

    company_options = sorted(
        df_market["company"].dropna().unique(),
        key=lambda c: str(c).lower(),
    )
    default_brand_a = _brand_option_match(brand_options, "kitkat", 0)
    default_brand_b = _brand_option_match(brand_options, "mars", 1)
    if default_brand_b == default_brand_a and len(brand_options) > 1:
        default_brand_b = brand_options[1]

    scope_key = f"{region_code}|{category}|brand_compare_v2"
    if st.session_state.get("bc_scope_key") != scope_key:
        st.session_state["bc_scope_key"] = scope_key
        st.session_state["bc_company_brand_a"] = "All companies / owners"
        st.session_state["bc_company_brand_b"] = "All companies / owners"
        st.session_state["bc_brand_brand_a"] = default_brand_a
        st.session_state["bc_brand_brand_b"] = default_brand_b

    reference_values = _reference_values(df_market)
    total_records = len(df_market)
    nova_count = int(_coverage_mask(df_market, "nova_group").sum())
    nova4_count = int((df_market["nova_group"] == 4).sum())

    st.markdown(f"### Reference base: {selected_base} observed records")
    st.caption("Both selected brands are compared within this same selected country-category base.")
    ref_cols = st.columns(5)
    ref_cols[0].metric("Observed product records", f"{total_records:,}")
    ref_cols[1].metric("Median energy, kcal/100g", _fmt_num(df_market["energy_kcal"].median(), 0))
    ref_cols[2].metric("Median protein, g/100g", _fmt_num(df_market["protein_100g"].median(), 1))
    ref_cols[3].metric("Median sugars, g/100g", _fmt_num(df_market["sugars_100g"].median(), 1))
    ref_cols[4].metric(
        "NOVA 4",
        f"{_pct(nova4_count, nova_count)} ({nova4_count:,}/{nova_count:,})",
        help=(
            "NOVA 4 percentage is calculated among records with NOVA data "
            "available, not among all observed records."
        ),
    )

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        _render_brand_compare_panel(
            "Brand A",
            company_options,
            default_brand_a,
            df_market,
            reference_values,
        )
    with col_b:
        _render_brand_compare_panel(
            "Brand B",
            company_options,
            default_brand_b,
            df_market,
            reference_values,
        )

    st.stop()

if active_section not in {_CATEGORY_REPORT_SECTION, _PRODUCT_MAP_SECTION}:
    st.info("This Market Overview report is not built yet.")
    st.stop()

if active_section == _CATEGORY_REPORT_SECTION:
    st.markdown("### 1. Category Report")
    st.info(
        "This report summarizes observed records for the selected "
        "country-category base and lets you drill into companies, brands, "
        "and products."
    )

    st.markdown(f"## {selected_base}")
    st.caption(
        "Observed product records from Open Food Facts for the selected "
        "country-category base."
    )

    st.subheader("Category Report filters")
    st.caption("Optional fields")
    _ALL_COMPANIES_LABEL = "All companies / owners"
    _ALL_BRANDS_LABEL = "All brands"

    company_values = sorted(df_market["company"].dropna().unique())
    col_company, col_brand = st.columns(2)
    with col_company:
        company_filter = st.selectbox(
            "Company / owner — optional",
            [_ALL_COMPANIES_LABEL] + company_values,
            index=0,
            key="cr_company",
        )

    if company_filter == _ALL_COMPANIES_LABEL:
        brand_base = df_market
        brand_values = []
    else:
        brand_base = df_market[df_market["company"] == company_filter]
        brand_values = sorted(brand_base["primary_brand"].dropna().unique())

    if (
        st.session_state.get("cr_brand") != _ALL_BRANDS_LABEL
        and st.session_state.get("cr_brand") not in brand_values
    ):
        st.session_state["cr_brand"] = _ALL_BRANDS_LABEL

    with col_brand:
        brand_filter = st.selectbox(
            "Brand — optional",
            [_ALL_BRANDS_LABEL] + brand_values,
            index=0,
            key="cr_brand",
            disabled=(company_filter == _ALL_COMPANIES_LABEL),
        )

    if company_filter == _ALL_COMPANIES_LABEL:
        st.caption("Select a company / owner first to narrow by brand.")
    if st.button("Reset filters", key="cr_reset_filters"):
        st.session_state["cr_company"] = _ALL_COMPANIES_LABEL
        st.session_state["cr_brand"] = _ALL_BRANDS_LABEL
        st.rerun()

    st.divider()

    total_records = len(df_market)
    nutrition_count = int(_nutrition_any_mask(df_market).sum())
    ingredient_count = int(_coverage_mask(df_market, "ingredients_text").sum())
    nutriscore_count = int(_coverage_mask(df_market, "nutriscore_grade").sum())
    nova_count = int(_coverage_mask(df_market, "nova_group").sum())
    mapped_count = int(_mapped_company_mask(df_market).sum())

    summary_cols = st.columns(3)
    with summary_cols[0]:
        _metric_card("Observed product records", f"{total_records:,}")
        _metric_card(
            "Nutrition data coverage",
            f"{_pct(nutrition_count, total_records)}",
            f"{nutrition_count:,} records with at least one displayed nutrition value.",
        )
    with summary_cols[1]:
        _metric_card(
            "Ingredient text coverage",
            f"{_pct(ingredient_count, total_records)}",
            f"{ingredient_count:,} records with ingredient text.",
        )
        _metric_card(
            "Nutri-Score coverage",
            f"{_pct(nutriscore_count, total_records)}",
            f"{nutriscore_count:,} records with Nutri-Score available.",
        )
    with summary_cols[2]:
        _metric_card(
            "NOVA coverage",
            f"{_pct(nova_count, total_records)}",
            f"{nova_count:,} records with NOVA group available.",
        )
        _metric_card(
            "Company mapping coverage",
            f"{_pct(mapped_count, total_records)}",
            f"{mapped_count:,} records mapped to a company / owner.",
        )

    st.divider()

    st.markdown(f"### Reference base: {selected_base} observed records")
    st.caption("All metrics below are calculated among records with available data.")

    ref_cols = st.columns(4)
    ref_metrics = [
        ("Median energy, kcal/100g", "energy_kcal", 0, ""),
        ("Median protein, g/100g", "protein_100g", 1, ""),
        ("Median fibre, g/100g", "fiber_100g", 1, ""),
        ("Median sugars, g/100g", "sugars_100g", 1, ""),
        ("Median saturated fat, g/100g", "saturated_fat_100g", 1, ""),
        ("Median salt, g/100g", "salt_100g", 2, ""),
    ]
    for idx, (label, col, decimals, suffix) in enumerate(ref_metrics):
        with ref_cols[idx % 4]:
            _metric_card(label, _fmt_num(df_market[col].median(), decimals, suffix))

    nova4_count = int((df_market["nova_group"] == 4).sum())
    nutri_dist = _nutriscore_distribution(df_market)
    ref_extra_cols = st.columns(2)
    with ref_extra_cols[0]:
        _metric_card(
            "NOVA 4 among records with NOVA available",
            f"{_pct(nova4_count, nova_count)}",
            "NOVA 4 percentage is calculated among records with NOVA data "
            "available, not among all observed records.",
        )
    with ref_extra_cols[1]:
        st.markdown("**Nutri-Score among records with Nutri-Score available**")
        st.caption(nutri_dist)

    st.divider()

    st.markdown("### Drill-down table")
    st.info(
        "Company rows are navigation only; brand summaries and product rows "
        "contain the nutrition values."
    )
    st.caption("Brand summaries are based on observed records in the selected base and are not sales-weighted.")
    st.caption(
        "Extreme values may reflect unusual products or source-data issues. "
        "Use product-level drill-down to inspect them."
    )

    drill_df = df_market.copy()
    if company_filter != _ALL_COMPANIES_LABEL:
        drill_df = drill_df[drill_df["company"] == company_filter]
    if brand_filter != _ALL_BRANDS_LABEL:
        drill_df = drill_df[drill_df["primary_brand"] == brand_filter]

    st.markdown(f"**Selected drill scope:** {len(drill_df):,} observed records")

    if drill_df.empty:
        st.info("No product records match the selected drill-down filters.")
        st.stop()

    reference_values = _reference_values(df_market)

    company_counts = (
        drill_df.groupby("company", dropna=False)
        .agg(
            observed_records=("barcode", "count"),
            brands=("primary_brand", "nunique"),
        )
        .reset_index()
    )

    def _company_sort_key(company: str) -> tuple[int, str]:
        company_text = str(company or "")
        if company_text == db.COMPANY_MANUAL_REVIEW_LABEL:
            return (1, company_text.lower())
        if company_text == db.COMPANY_OTHER_LABEL:
            return (2, company_text.lower())
        return (0, company_text.lower())

    company_counts = company_counts.sort_values(
        "company", key=lambda s: s.map(_company_sort_key)
    )

    for company_name in company_counts["company"]:
        company_df = drill_df[drill_df["company"] == company_name]
        n_company_records = len(company_df)
        n_company_brands = company_df["primary_brand"].nunique()
        expander_label = (
            f"{company_name} · {n_company_records:,} observed records · "
            f"{n_company_brands:,} brands"
        )
        with st.expander(expander_label, expanded=(company_filter != _ALL_COMPANIES_LABEL)):
            company_cols = st.columns(3)
            with company_cols[0]:
                _metric_card("Observed product records", f"{n_company_records:,}")
            with company_cols[1]:
                _metric_card("Number of brands", f"{n_company_brands:,}")
            with company_cols[2]:
                _metric_card(
                    "Nutrition data coverage",
                    _pct(_nutrition_any_mask(company_df).sum(), n_company_records),
                )

            st.markdown("**Brand summaries**")
            brand_summary = _brand_summary(company_df, reference_values)
            brand_event = st.dataframe(
                brand_summary,
                hide_index=True,
                width="stretch",
                column_config=_column_help_config(list(brand_summary.columns)),
                on_select="rerun",
                selection_mode="single-row",
                key=f"cr_brands_{company_name}",
            )

            selected_brand = None
            if (
                company_filter == company_name
                and brand_filter != _ALL_BRANDS_LABEL
            ):
                selected_brand = brand_filter
            else:
                if hasattr(brand_event, "selection"):
                    selected_brand_rows = brand_event.selection.rows
                else:
                    selected_brand_rows = brand_event.get("selection", {}).get("rows", [])
                if selected_brand_rows:
                    selected_brand = brand_summary.iloc[selected_brand_rows[0]]["Brand"]

            if selected_brand:
                brand_products = company_df[company_df["primary_brand"] == selected_brand]
                st.markdown(
                    f"**Product records: {selected_brand} · "
                    f"{len(brand_products):,} observed product records**"
                )
                product_records = brand_products.head(250)
                product_view = _product_table(brand_products, reference_values, limit=250)
                product_event = st.dataframe(
                    product_view,
                    hide_index=True,
                    width="stretch",
                    column_config=_column_help_config(list(product_view.columns)),
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"cr_products_{company_name}_{selected_brand}",
                )
                if hasattr(product_event, "selection"):
                    selected_rows = product_event.selection.rows
                else:
                    selected_rows = product_event.get("selection", {}).get("rows", [])
                if selected_rows:
                    _render_product_detail(product_records.iloc[selected_rows[0]])
                if len(brand_products) > 250:
                    st.caption(
                        f"Showing 250 of {len(brand_products):,} product records "
                        f"for {selected_brand}. Use the Brand filter to narrow the drill-down."
                    )
            else:
                st.caption(
                    "Select one brand in the table above, or use the filters above "
                    "to display product records for a selected company / owner and brand."
                )

    st.stop()

if active_section == "By Region":
    st.markdown("### 3. By Region")
    st.caption("Compare fixed nutritional benchmarks across regions and broad product categories.")
    st.caption("Values show the median, with the 25th–75th percentile range underneath.")

    bench_df = db.get_region_category_benchmarks()

    if bench_df.empty:
        st.warning(
            "No precomputed region benchmarks found yet — run "
            "pipeline/compute_region_benchmarks.py to generate them."
        )
        st.stop()

    # Fixed display order — not alphabetical, matches the spec's own
    # category ordering and the region ui_order already used for the
    # Region selectbox above.
    _CATEGORY_ORDER = ["dairies", "snacks", "cereals", "beverages"]
    _region_order_map = {code: i for i, code in enumerate(region_codes)}
    bench_df["_cat_order"] = bench_df["category"].map(
        lambda c: _CATEGORY_ORDER.index(c) if c in _CATEGORY_ORDER else len(_CATEGORY_ORDER)
    )
    bench_df["_region_order"] = bench_df["region_code"].map(_region_order_map).fillna(99)
    bench_df = bench_df.sort_values(["_cat_order", "_region_order"])

    def _fmt_cell(median, p25, p75, decimals: int) -> str:
        if median is None or pd.isna(median):
            return '<div style="color:#999;">—</div>'
        med_str = f"{median:.{decimals}f}"
        range_str = f"{p25:.{decimals}f}–{p75:.{decimals}f}" if p25 is not None and not pd.isna(p25) else "—"
        return (
            f'<div style="font-weight:600;">{med_str}</div>'
            f'<div style="font-size:0.78rem;color:#8A8F8C;">{range_str}</div>'
        )

    st.markdown(
        f"**Selected market highlighted: {region_label} · {_category_label(category)}**"
    )

    rows_html = []
    last_cat = None
    for _, r in bench_df.iterrows():
        cat_disp = _category_label(r["category"])
        region_disp = region_code_to_label.get(r["region_code"], r["region_code"])
        is_selected = (r["region_code"] == region_code) and (r["category"].lower() == category.lower())
        row_bg = "#EEF1EF" if is_selected else "transparent"
        border_left = f"3px solid {components.PRIMARY_ACCENT}" if is_selected else "3px solid transparent"

        cat_cell = f'<b>{cat_disp}</b>' if r["category"] != last_cat else ""
        last_cat = r["category"]

        nova_pct = r["nova4_pct"]
        nova_str = f"{nova_pct:.0f}%" if nova_pct is not None and not pd.isna(nova_pct) else "—"
        nova_title = (
            f"{int(r['nova4_n']):,} of {int(r['nova_classified_n']):,} products with a "
            f"determined NOVA group" if not pd.isna(r["nova_classified_n"]) else ""
        )

        cell_energy  = _fmt_cell(r['energy_median'],      r['energy_p25'],      r['energy_p75'],      0)
        cell_protein = _fmt_cell(r['protein_eff_median'],  r['protein_eff_p25'], r['protein_eff_p75'],  1)
        cell_fibre   = _fmt_cell(r['fibre_eff_median'],    r['fibre_eff_p25'],   r['fibre_eff_p75'],    1)
        cell_satfat  = _fmt_cell(r['satfat_eff_median'],   r['satfat_eff_p25'],  r['satfat_eff_p75'],   1)
        cell_sugars  = _fmt_cell(r['sugars_eff_median'],   r['sugars_eff_p25'],  r['sugars_eff_p75'],   1)

        # Built as ONE single-line string, deliberately — st.markdown runs
        # content through a Markdown parser before honoring
        # unsafe_allow_html, and any line starting with 4+ spaces of
        # indentation gets treated as a Markdown code block and rendered
        # as escaped literal text instead of parsed as HTML. A tidy
        # multi-line indented f-string in the Python source looks fine
        # here but silently breaks in the browser — confirmed by running
        # both versions through the `markdown` package directly before
        # fixing this.
        rows_html.append(
            f'<tr style="background:{row_bg}; border-left:{border_left};">'
            f'<td style="padding:0.5rem 0.7rem;">{cat_cell}</td>'
            f'<td style="padding:0.5rem 0.7rem;">{region_disp}</td>'
            f'<td style="padding:0.5rem 0.7rem; text-align:right;">{int(r["product_count"]):,}</td>'
            f'<td style="padding:0.5rem 0.7rem; text-align:right;">{cell_energy}</td>'
            f'<td style="padding:0.5rem 0.7rem; text-align:right;">{cell_protein}</td>'
            f'<td style="padding:0.5rem 0.7rem; text-align:right;">{cell_fibre}</td>'
            f'<td style="padding:0.5rem 0.7rem; text-align:right;">{cell_satfat}</td>'
            f'<td style="padding:0.5rem 0.7rem; text-align:right;">{cell_sugars}</td>'
            f'<td style="padding:0.5rem 0.7rem; text-align:right;" title="{nova_title}">{nova_str}</td>'
            f'</tr>'
        )

    header_html = (
        '<tr style="border-bottom:2px solid #D8DBD9; text-align:left;">'
        '<th style="padding:0.5rem 0.7rem;">Category</th>'
        '<th style="padding:0.5rem 0.7rem;">Region</th>'
        '<th style="padding:0.5rem 0.7rem; text-align:right;">Products</th>'
        '<th style="padding:0.5rem 0.7rem; text-align:right;">Energy, kcal/100g or ml</th>'
        '<th style="padding:0.5rem 0.7rem; text-align:right;">Protein, g/100 kcal</th>'
        '<th style="padding:0.5rem 0.7rem; text-align:right;">Fibre, g/100 kcal</th>'
        '<th style="padding:0.5rem 0.7rem; text-align:right;">Saturated fat, g/100 kcal</th>'
        '<th style="padding:0.5rem 0.7rem; text-align:right;">Sugars, g/100 kcal</th>'
        '<th style="padding:0.5rem 0.7rem; text-align:right;">NOVA 4, % of classified</th>'
        '</tr>'
    )
    table_html = (
        '<div style="overflow-x:auto;">'
        '<table style="width:100%; border-collapse:collapse; font-size:0.9rem;">'
        f'<thead>{header_html}</thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table>'
        '</div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    st.caption("Bold value: median · Range underneath: 25th–75th percentile")
    st.caption(
        "Product counts describe records in the cleaned OFF-derived database "
        "and are not sales- or distribution-weighted. NOVA 4% is a share of "
        "classified products, not of the full category — hover a NOVA cell "
        "for the underlying counts."
    )
    st.caption(f"Benchmark snapshot: {_SNAPSHOT_LABEL}")

    csv_bytes = bench_df.drop(columns=["_cat_order", "_region_order"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download benchmark table as CSV", data=csv_bytes,
        file_name="by_region_benchmarks.csv", mime="text/csv",
    )

    st.stop()

if active_section == "Product Profile Landscape":
    st.markdown("### 2. Product Profile Landscape")
    st.caption("Build a cumulative profile to see how often nutritional characteristics combine.")
    st.markdown(
        f"**{region_label} · {_category_label(category)}** &nbsp;·&nbsp; "
        f"Current data snapshot: {_SNAPSHOT_LABEL}"
    )
    st.caption(
        "Each step adds another condition. Percentages show the share of "
        "eligible products meeting all conditions up to that step."
    )

    # label -> (slot, condition_key). NOVA's two variants share one slot —
    # picking either excludes both from later steps (spec section 12).
    _PROFILE_DIMENSIONS = {
        "Higher protein efficiency": ("protein", "protein_hi"),
        "Higher fibre efficiency":   ("fibre",   "fibre_hi"),
        "Lower total sugars":        ("sugar",   "sugar_lo"),
        "Lower saturated fat":       ("satfat",  "satfat_lo"),
        "Lower energy density":      ("energy",  "energy_lo"),
        "NOVA 1–3":                  ("nova",    "nova_1_3"),
        "NOVA 4 — Ultra-processed":  ("nova",    "nova_4"),
    }
    _DEFAULT_STEPS = ["Lower saturated fat", "Higher protein efficiency", "Higher fibre efficiency"]
    all_labels = list(_PROFILE_DIMENSIONS.keys())

    with st.expander("What do \"higher\" / \"lower\" mean?", expanded=False):
        st.caption(
            "Each condition compares a product to the fixed country-category "
            "benchmark for the current data snapshot. \"Higher\" means an "
            "index of at least 110 (at least 10% above benchmark); \"lower\" "
            "means an index of 90 or below (at least 10% below benchmark). "
            "NOVA is categorical rather than benchmark-based."
        )

    if st.button("Reset profile", key="mo_profile_reset"):
        st.session_state["mo_profile_step1"] = _DEFAULT_STEPS[0]
        st.session_state["mo_profile_step2"] = _DEFAULT_STEPS[1]
        st.session_state["mo_profile_step3"] = _DEFAULT_STEPS[2]
        st.rerun()

    step1_default = st.session_state.get("mo_profile_step1", _DEFAULT_STEPS[0])
    step1 = st.selectbox(
        "Step 1", all_labels,
        index=all_labels.index(step1_default) if step1_default in all_labels else 0,
        key="mo_profile_step1",
    )
    step1_slot = _PROFILE_DIMENSIONS[step1][0]

    step2_choices = ["None"] + [l for l in all_labels if _PROFILE_DIMENSIONS[l][0] != step1_slot]
    step2_default = st.session_state.get("mo_profile_step2", _DEFAULT_STEPS[1])
    if step2_default not in step2_choices:
        step2_default = "None"
    step2 = st.selectbox(
        "Step 2 (optional)", step2_choices,
        index=step2_choices.index(step2_default),
        key="mo_profile_step2",
    )

    step3 = "None"
    if step2 != "None":
        used_slots = {step1_slot, _PROFILE_DIMENSIONS[step2][0]}
        step3_choices = ["None"] + [l for l in all_labels if _PROFILE_DIMENSIONS[l][0] not in used_slots]
        step3_default = st.session_state.get("mo_profile_step3", _DEFAULT_STEPS[2])
        if step3_default not in step3_choices:
            step3_default = "None"
        step3 = st.selectbox(
            "Step 3 (optional)", step3_choices,
            index=step3_choices.index(step3_default),
            key="mo_profile_step3",
        )
    else:
        st.caption("Step 3 becomes available once Step 2 is set.")

    active_labels = [step1] + ([step2] if step2 != "None" else []) + ([step3] if step3 != "None" else [])
    active_keys = [_PROFILE_DIMENSIONS[l][1] for l in active_labels]
    full_subset_key = "|".join(sorted(active_keys))

    lookup = db.get_profile_intersections(region_code, category, full_subset_key)

    if not lookup:
        st.warning(
            "No precomputed profile data found for this market yet — run "
            "pipeline/compute_profile_intersections.py to generate it."
        )
    else:
        # eligible_count is constant across every row sharing this
        # full_subset_key (spec section 8), so any row gives the right value.
        eligible_count = next(iter(lookup.values()))[0]
        n_total_market = len(df_market)
        coverage_pct = (eligible_count / n_total_market) if n_total_market else 0

        levels = [("All eligible products", None, eligible_count, 100.0)]
        prev_matching = eligible_count
        for i in range(1, len(active_labels) + 1):
            sub_key = "|".join(sorted(active_keys[:i]))
            _, matching = lookup.get(sub_key, (eligible_count, 0))
            pct = (matching / eligible_count * 100) if eligible_count else 0
            prefix = "" if i == 1 else "AND "
            levels.append((f"{prefix}{active_labels[i - 1]}", prev_matching, matching, pct))
            prev_matching = matching

        _MIN_BAR_PCT = 6  # visual floor so a 1-2% result stays legible
        for j, (label, prev_m, count, pct) in enumerate(levels):
            bar_pct = max(pct, _MIN_BAR_PCT) if count > 0 else 0
            retention_note = ""
            if j > 1 and prev_m:
                retention_note = f" · {count / prev_m:.0%} of previous level"
            st.markdown(
                f'<div style="margin:0.5rem 0;">'
                f'<div style="font-size:0.85rem;font-weight:600;color:#3F4A47;">{label.upper()}</div>'
                f'<div style="background:#ECECEC;border-radius:4px;height:22px;margin:0.15rem 0;">'
                f'<div style="background:{components.PRIMARY_ACCENT};width:{bar_pct}%;height:100%;'
                f'border-radius:4px;"></div></div>'
                f'<div style="font-size:0.85rem;color:#4A4A4A;">{pct:.0f}% · {count:,}{retention_note}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.caption(f"Eligible-data coverage: {coverage_pct:.0%}")
        st.caption(
            f"{eligible_count:,} of {n_total_market:,} products in the selected "
            f"region-category have valid data for all selected profile dimensions."
        )
        st.caption(f"Benchmarks: index ≥110 / ≤90 · Snapshot: {_SNAPSHOT_LABEL}")

    st.stop()

# ── Product Map filters (local to this section only) ─────────────────
st.subheader("Product Map filters")
st.caption("Optional fields")

all_companies_present = sorted(df_market["company"].dropna().unique())
_ALL_COMPANIES_LABEL = "All companies"
company_choices = [_ALL_COMPANIES_LABEL] + [
    c for c in all_companies_present if c != db.COMPANY_OTHER_LABEL
]
if db.COMPANY_OTHER_LABEL in all_companies_present:
    company_choices.append(db.COMPANY_OTHER_LABEL)

col_company, col_brand = st.columns(2)
with col_company:
    selected_company = st.selectbox("Company", company_choices, index=0, key="mo_company")

if selected_company == _ALL_COMPANIES_LABEL:
    df_company_scope = df_market
    brand_pool = sorted(df_market["primary_brand"].dropna().unique())
else:
    df_company_scope = df_market[df_market["company"] == selected_company]
    brand_pool = sorted(df_company_scope["primary_brand"].dropna().unique())

_ALL_BRANDS_LABEL = "All brands"
with col_brand:
    selected_brand = st.selectbox(
        "Brand", [_ALL_BRANDS_LABEL] + brand_pool, index=0, key="mo_brand",
    )

if st.button("Reset filters", key="mo_reset_filters"):
    st.session_state["mo_company"] = _ALL_COMPANIES_LABEL
    st.session_state["mo_brand"] = _ALL_BRANDS_LABEL
    st.rerun()

if selected_brand == _ALL_BRANDS_LABEL:
    df_scope = df_company_scope
else:
    df_scope = df_company_scope[df_company_scope["primary_brand"] == selected_brand]

st.divider()

# ── Section 3: Product Map ──────────────────────────────────────────────────
st.markdown("### 3. Product Map")
st.caption("Explore individual products across selected quantitative nutrition metrics.")

# Quantitative-only metric registry. Deliberately excludes Positioning,
# NOVA, Nutri-Score, and any categorical field — spec section 4 rule.
_METRICS: dict[str, str] = {
    "Energy, kcal/100 g or 100 ml":       "energy_kcal",
    "Protein, g/100 g or 100 ml":         "protein_100g",
    "Protein, g/100 kcal":                "protein_per_kcal",
    "Fat, g/100 g or 100 ml":             "fat_100g",
    "Saturated fat, g/100 g or 100 ml":   "saturated_fat_100g",
    "Saturated fat, g/100 kcal":          "satfat_per_kcal",
    "Carbohydrates, g/100 g or 100 ml":   "carbs_100g",
    "Sugars, g/100 g or 100 ml":          "sugars_100g",
    "Sugars, g/100 kcal":                 "sugars_per_kcal",
    "Fibre, g/100 g or 100 ml":           "fiber_100g",
    "Fibre, g/100 kcal":                  "fiber_per_kcal",
    "Salt, g/100 g or 100 ml":            "salt_100g",
}
_PER_KCAL_COLS = {"protein_per_kcal", "fiber_per_kcal", "satfat_per_kcal", "sugars_per_kcal"}
_CHART_RANGE_OPTIONS = ["Lower 3%", "Middle 94%", "Upper 3%", "All"]
_CHART_RANGE_TO_BAND = {
    "Lower 3%": "L",
    "Middle 94%": "M",
    "Upper 3%": "U",
}

_DEFAULT_X_LABEL = "Energy, kcal/100 g or 100 ml"
_DEFAULT_Y_LABEL = "Protein, g/100 kcal"

metric_labels = list(_METRICS.keys())
col_x, col_y = st.columns(2)
with col_x:
    x_label = st.selectbox(
        "X-axis", metric_labels,
        index=metric_labels.index(_DEFAULT_X_LABEL), key="mo_xaxis",
    )
    x_range_label = st.selectbox(
        "X-axis range",
        _CHART_RANGE_OPTIONS,
        index=_CHART_RANGE_OPTIONS.index("Middle 94%"),
        key="mo_xaxis_range",
        help=(
            "Chart range uses precomputed nutrition percentiles for the "
            "selected metric. Middle 94% is the default for readability; "
            "Lower 3%, Upper 3%, and All remain available."
        ),
    )
with col_y:
    # Same metric cannot be on both axes (spec section 4).
    y_choices = [m for m in metric_labels if m != x_label]
    y_default = _DEFAULT_Y_LABEL if _DEFAULT_Y_LABEL in y_choices else y_choices[0]
    y_label = st.selectbox(
        "Y-axis", y_choices,
        index=y_choices.index(y_default), key="mo_yaxis",
    )
    y_range_label = st.selectbox(
        "Y-axis range",
        _CHART_RANGE_OPTIONS,
        index=_CHART_RANGE_OPTIONS.index("Middle 94%"),
        key="mo_yaxis_range",
        help=(
            "Chart range uses precomputed nutrition percentiles for the "
            "selected metric. Middle 94% is the default for readability; "
            "Lower 3%, Upper 3%, and All remain available."
        ),
    )

x_col = _METRICS[x_label]
y_col = _METRICS[y_label]


def _chart_band_col(metric_key: str) -> str | None:
    return db.CHART_BAND_COLUMNS.get(metric_key)


def _range_mask(frame: pd.DataFrame, metric_key: str, range_label: str) -> pd.Series:
    if range_label == "All":
        return pd.Series(True, index=frame.index)
    band_col = _chart_band_col(metric_key)
    band_value = _CHART_RANGE_TO_BAND.get(range_label)
    if not band_col or band_col not in frame.columns or band_value is None:
        return pd.Series(False, index=frame.index)
    return frame[band_col].fillna("").astype(str).eq(band_value)

# Methodological note: whenever Energy is paired with any per-100kcal
# metric, that metric is partly derived from Energy (Energy is the
# denominator) — this generalizes the spec's own note about the default
# pair (Energy x Protein/100kcal) to every per-kcal metric, since the
# same mathematical relationship holds for fiber/satfat/sugars per kcal
# too, not just protein.
_energy_selected   = "energy_kcal" in (x_col, y_col)
_per_kcal_selected = (x_col in _PER_KCAL_COLS) or (y_col in _PER_KCAL_COLS)
if _energy_selected and _per_kcal_selected:
    st.caption(
        "One of the selected metrics is derived partly from Energy. "
        "This chart shows nutritional efficiency, not statistical correlation."
    )

# ── Additional chart options ────────────────────────────────────────────────
with st.expander("Additional chart options", expanded=False):
    bubble_choices = ["None"] + [m for m in metric_labels if m not in (x_label, y_label)]
    bubble_label = st.selectbox("Bubble size", bubble_choices, index=0, key="mo_bubble")
    colour_label = st.selectbox("Colour by", ["None", "NOVA group", "Nutri-Score"],
                                 index=0, key="mo_colour")

    if bubble_label != "None":
        bubble_col = _METRICS[bubble_label]
        _bubble_coverage = df_scope[bubble_col].notna().mean() if len(df_scope) else 0
        st.caption(f"Bubble size: {bubble_label} · available for {_bubble_coverage:.0%} of products in scope")
    else:
        bubble_col = None

# ── Eligible population: both axis metrics must be valid (spec section 12) ──
_axis_value_mask = df_scope[x_col].notna() & df_scope[y_col].notna()
df_axis_eligible = df_scope[_axis_value_mask]

_range_mask_selected = _range_mask(
    df_axis_eligible,
    x_col,
    x_range_label,
) & _range_mask(df_axis_eligible, y_col, y_range_label)
df_eligible = df_axis_eligible[_range_mask_selected]

n_in_scope = len(df_scope)
n_axis_eligible = len(df_axis_eligible)
n_eligible = len(df_eligible)
_coverage_pct = (n_axis_eligible / n_in_scope) if n_in_scope else 0
_trimmed_count = n_axis_eligible - n_eligible

st.markdown(
    f"**{region_label} · {_category_label(category)}** &nbsp;·&nbsp; "
    f"{n_in_scope:,} products in scope &nbsp;·&nbsp; {n_eligible:,} products plotted"
)
st.caption(f"{_coverage_pct:.1%} of products in scope have usable values for both selected axes.")
if _trimmed_count:
    st.caption(
        "Chart ranges use precomputed nutrition percentiles for the selected "
        "metric(s). Product and market statistics continue to use the full "
        "eligible population unless otherwise stated."
    )
    st.caption(
        f"{_trimmed_count:,} otherwise axis-eligible product(s) are outside "
        "the selected chart range."
    )

# ── Large-volume handling: sample for display, keep stats on full population ─
_DISPLAY_THRESHOLD = 15_000
_sampled = n_eligible > _DISPLAY_THRESHOLD

if not _sampled:
    df_display = df_eligible
else:
    # Stratified sample over an X/Y grid (preserves overall distribution and
    # density areas), stratified additionally by colour category when colour
    # is active (preserves category proportions), plus explicit inclusion of
    # extreme points on both axes (guards against losing outliers to random
    # sampling). Brand/company diversity is not separately stratified for —
    # a real simplification versus the full spec wording, flagged here
    # rather than silently claimed as solved.
    df_e = df_eligible.copy()
    try:
        df_e["_xbin"] = pd.cut(df_e[x_col], bins=20, duplicates="drop")
        df_e["_ybin"] = pd.cut(df_e[y_col], bins=20, duplicates="drop")
    except ValueError:
        df_e["_xbin"] = 0
        df_e["_ybin"] = 0

    strat_cols = ["_xbin", "_ybin"]
    if colour_label == "NOVA group":
        strat_cols.append("nova_group")
    elif colour_label == "Nutri-Score":
        strat_cols.append("nutriscore_grade")

    frac = _DISPLAY_THRESHOLD / n_eligible
    sampled_parts = [
        grp.sample(frac=frac, random_state=42) if len(grp) > 1 else grp
        for _, grp in df_e.groupby(strat_cols, observed=True, dropna=False)
    ]
    df_sample = pd.concat(sampled_parts) if sampled_parts else df_e.head(0)

    # Always include extremes on both axes so outliers aren't lost to sampling.
    _n_extreme = max(1, int(0.005 * n_eligible))
    extremes_idx = pd.Index([])
    for col in (x_col, y_col):
        extremes_idx = extremes_idx.union(df_e.nsmallest(_n_extreme, col).index)
        extremes_idx = extremes_idx.union(df_e.nlargest(_n_extreme, col).index)
    df_display = pd.concat([df_sample, df_e.loc[df_e.index.intersection(extremes_idx)]])
    df_display = df_display[~df_display.index.duplicated()]

    st.caption(
        f"Displaying {len(df_display):,} representative points from "
        f"{n_eligible:,} eligible products. Product counts and market "
        f"statistics use the full selected population."
    )

# ── Build the scatter (WebGL — required at this row count) ─────────────────
def _product_map_nova_label(v) -> str:
    try:
        iv = int(v)
        return f"NOVA {iv}" if iv in (1, 2, 3, 4) else "Not determined"
    except (TypeError, ValueError):
        return "Not determined"


def _nutriscore_label(v) -> str:
    v = str(v).strip().upper() if v is not None else ""
    return v if v in ("A", "B", "C", "D", "E") else "Not available"


# NOVA colour-by uses an aggregated 2-bucket scheme (1-3 vs. 4), not the
# 5-way muted palette used for hover/detail labels above. This is a
# deliberate departure from a strictly neutral palette: NOVA 4 is
# officially named "ultra-processed" by the classification itself, and
# that framing is an established external public-health convention, not
# an in-house judgment we're inventing (unlike the composition scores
# removed earlier this project) — so red here is treated as reflecting
# the classification's own convention, not adding a new one.
def _nova_color_group(v) -> str:
    try:
        iv = int(v)
    except (TypeError, ValueError):
        return "Not determined"
    if iv in (1, 2, 3):
        return "NOVA 1-3"
    if iv == 4:
        return "NOVA 4 (ultra-processed)"
    return "Not determined"


_NOVA_GROUP_COLORS = {
    "NOVA 1-3": "#8FBF7A",
    "NOVA 4 (ultra-processed)": "#D4453A",
    "Not determined": "#C7C7C7",
}
# Nutri-Score keeps its own established on-pack colour convention
# (externally standardized, not an editorial choice we're introducing).
_NUTRISCORE_COLORS = {
    "A": "#038141", "B": "#85BB2F", "C": "#FECB02",
    "D": "#EE8100", "E": "#E63E11", "Not available": "#C7C7C7",
}

fig = go.Figure()

if bubble_col is not None and len(df_display):
    _raw_size = df_display[bubble_col].fillna(0).clip(lower=0)
    _max_val = _raw_size.max() or 1
    marker_size = 6 + (_raw_size / _max_val).pow(0.5) * 24  # area-proportional, capped
else:
    marker_size = 9

customdata = np.stack([
    df_display["barcode"].astype(str),
    df_display["company"].astype(str),
    df_display["primary_brand"].astype(str),
    df_display["product_name"].astype(str),
    df_display[x_col].astype(float),
    df_display[y_col].astype(float),
    df_display["nova_group"].map(_product_map_nova_label),
    df_display["nutriscore_grade"].map(_nutriscore_label),
], axis=-1) if len(df_display) else np.empty((0, 8))

hover_template = (
    "<b>%{customdata[3]}</b><br>"
    "Brand: %{customdata[2]}<br>"
    "Company: %{customdata[1]}<br>"
    f"Region: {region_label}<br>"
    f"Category: {_category_label(category)}<br>"
    f"{x_label}: " + "%{x:.2f}<br>"
    f"{y_label}: " + "%{y:.2f}<br>"
    "NOVA: %{customdata[6]}<br>"
    "Nutri-Score: %{customdata[7]}"
    "<extra></extra>"
)

if colour_label == "NOVA group" and len(df_display):
    color_series = df_display["nova_group"].map(_nova_color_group)
    marker_color = color_series.map(_NOVA_GROUP_COLORS).fillna("#C7C7C7")
elif colour_label == "Nutri-Score" and len(df_display):
    color_series = df_display["nutriscore_grade"].map(_nutriscore_label)
    marker_color = color_series.map(_NUTRISCORE_COLORS).fillna("#C7C7C7")
else:
    marker_color = components.PRIMARY_ACCENT

fig.add_trace(go.Scattergl(
    x=df_display[x_col] if len(df_display) else [],
    y=df_display[y_col] if len(df_display) else [],
    mode="markers",
    marker=dict(
        size=marker_size, color=marker_color, opacity=0.6,
        line=dict(width=0),
    ),
    customdata=customdata,
    hovertemplate=hover_template,
))
fig.update_layout(
    height=620,
    xaxis_title=x_label,
    yaxis_title=y_label,
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="white",
    dragmode="pan",
)

event = st.plotly_chart(
    fig, use_container_width=True, on_select="rerun", key="mo_scatter",
)

# ── Colour legend (only relevant when a colour-by option is active) ────────
def _legend_html(swatches: dict[str, str]) -> str:
    items = "".join(
        f'<span style="display:inline-flex;align-items:center;margin-right:1.1rem;">'
        f'<span style="width:12px;height:12px;border-radius:50%;background:{color};'
        f'display:inline-block;margin-right:0.4rem;"></span>{label}</span>'
        for label, color in swatches.items()
    )
    return f'<div style="margin:0.3rem 0 0.9rem 0;">{items}</div>'


if colour_label == "NOVA group":
    st.markdown(_legend_html(_NOVA_GROUP_COLORS), unsafe_allow_html=True)
elif colour_label == "Nutri-Score":
    st.markdown(_legend_html(_NUTRISCORE_COLORS), unsafe_allow_html=True)

# ── Product details — click a dot (read-only, does not filter anything) ────
st.markdown("**Product details — click a dot**")
_points = event.selection.get("points", []) if event and hasattr(event, "selection") else []

if not _points:
    st.caption("Click a product dot to view its details.")
else:
    _cd = _points[0].get("customdata")
    if _cd:
        barcode = str(_cd[0])
        selected_rows = df_display[df_display["barcode"].astype(str) == barcode]
        if selected_rows.empty:
            st.caption(f"Selected barcode: {barcode}")
        else:
            _render_product_detail(selected_rows.iloc[0])
            st.caption(f"Barcode: {barcode}")
