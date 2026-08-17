"""
Market Overview.

Release 1 scope: a snapshot of the observable product universe, not a
segmentation or trend report. Three sections, built and checked one at a
time:
  1. Product Landscape         — this file, built now
  2. Product Profile Landscape — cumulative AND-condition funnel, not yet built
  3. By Region                 — fixed cross-region/category benchmark table, not yet built

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

components.inject_base_css()
components.render_header(
    "Market Overview",
    "Explore nutritional efficiency across the observable product universe.",
)

if not db.database_exists():
    st.info("No local database found yet — run the pipeline first (see docs/ONBOARDING.md).")
    st.stop()

# ── Section navigation (left pane) ───────────────────────────────────────────
# Shows name + subtitle for every planned section so a first-time visitor
# sees what's available; a returning visitor clicks instead of scrolling.
# Sections 2 and 3 are placeholders until built — shown so the navigation
# shape doesn't change later, not because they have content yet.
_SECTIONS = [
    ("Product Landscape",
     "Explore individual products across selected quantitative nutrition metrics."),
    ("Product Profile Landscape",
     "Build a cumulative profile for the selected market."),
    ("By Region",
     "Fixed comparison of all regions and categories."),
]

if "mo_active_section" not in st.session_state:
    st.session_state["mo_active_section"] = _SECTIONS[0][0]

with st.sidebar:
    st.markdown("**Market Overview sections**")
    for i, (name, subtitle) in enumerate(_SECTIONS, start=1):
        is_active = st.session_state["mo_active_section"] == name
        if st.button(
            f"{'▶ ' if is_active else ''}{i}. {name}",
            key=f"mo_nav_{i}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state["mo_active_section"] = name
            st.rerun()
        st.caption(subtitle)

active_section = st.session_state["mo_active_section"]

# ── Data snapshot line (global, not scope-dependent) ─────────────────────────
_TOTAL_PRODUCTS = db.count_products()
st.caption(f"Data snapshot: July 2026 · {_TOTAL_PRODUCTS:,} products in database")

# ── Fixed defaults for first load ────────────────────────────────────────────
_DEFAULT_REGION_CODE = "FRANCE"
_DEFAULT_CATEGORY    = "snacks"

# ── Market scope (mandatory, single-select, shared by sections 1 and 2) ─────
st.subheader("Market scope")
st.caption("Mandatory fields")

region_options       = db.get_region_options()  # [(code, label), ...]
region_codes         = [code for code, _ in region_options]
region_labels        = [label for _, label in region_options]
region_code_to_label = dict(region_options)

category_options = db.get_filter_options()["query_category"]

col_region, col_category = st.columns(2)
with col_region:
    default_region_idx = (
        region_codes.index(_DEFAULT_REGION_CODE)
        if _DEFAULT_REGION_CODE in region_codes else 0
    )
    region_label = st.selectbox(
        "Region *", region_labels, index=default_region_idx, key="mo_region",
    )
    region_code = {v: k for k, v in region_code_to_label.items()}[region_label]
with col_category:
    default_category_idx = (
        category_options.index(_DEFAULT_CATEGORY)
        if _DEFAULT_CATEGORY in category_options else 0
    )
    category = st.selectbox(
        "Category *", category_options, index=default_category_idx, key="mo_category",
    )

# ── Load the region x category population (cached; shared by all 3 sections) ─
df_market = db.get_market_products(category, region_code)

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
    _CATEGORY_ORDER = ["dairy", "snacks", "cereals", "beverages"]
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
        f"**Selected market highlighted: {region_label} · {category.title()}**"
    )

    rows_html = []
    last_cat = None
    for _, r in bench_df.iterrows():
        cat_disp = r["category"].title()
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
    st.caption("Benchmark snapshot: July 2026")

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
        f"**{region_label} · {category.title()}** &nbsp;·&nbsp; "
        f"Current data snapshot: July 2026"
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
        st.caption("Benchmarks: index ≥110 / ≤90 · Snapshot: July 2026")

    st.stop()

# ── Product Landscape filters (local to this section only) ─────────────────
st.subheader("Product Landscape filters")
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

if selected_brand == _ALL_BRANDS_LABEL:
    df_scope = df_company_scope
else:
    df_scope = df_company_scope[df_company_scope["primary_brand"] == selected_brand]

st.divider()

# ── Section 1: Product Landscape ────────────────────────────────────────────
st.markdown("### 1. Product Landscape")
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

_DEFAULT_X_LABEL = "Energy, kcal/100 g or 100 ml"
_DEFAULT_Y_LABEL = "Protein, g/100 kcal"

metric_labels = list(_METRICS.keys())
col_x, col_y = st.columns(2)
with col_x:
    x_label = st.selectbox(
        "X-axis", metric_labels,
        index=metric_labels.index(_DEFAULT_X_LABEL), key="mo_xaxis",
    )
with col_y:
    # Same metric cannot be on both axes (spec section 4).
    y_choices = [m for m in metric_labels if m != x_label]
    y_default = _DEFAULT_Y_LABEL if _DEFAULT_Y_LABEL in y_choices else y_choices[0]
    y_label = st.selectbox(
        "Y-axis", y_choices,
        index=y_choices.index(y_default), key="mo_yaxis",
    )

x_col = _METRICS[x_label]
y_col = _METRICS[y_label]

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
_eligible_mask = df_scope[x_col].notna() & df_scope[y_col].notna()
df_eligible = df_scope[_eligible_mask]

n_in_scope = len(df_scope)
n_eligible = len(df_eligible)
_coverage_pct = (n_eligible / n_in_scope) if n_in_scope else 0

st.markdown(
    f"**{region_label} · {category.title()}** &nbsp;·&nbsp; "
    f"{n_in_scope:,} products in scope &nbsp;·&nbsp; {n_eligible:,} products plotted"
)
st.caption(f"{_coverage_pct:.1%} of products in scope have usable values for both selected axes.")

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
def _nova_label(v) -> str:
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
    df_display["nova_group"].map(_nova_label),
    df_display["nutriscore_grade"].map(_nutriscore_label),
], axis=-1) if len(df_display) else np.empty((0, 8))

hover_template = (
    "<b>%{customdata[3]}</b><br>"
    "Brand: %{customdata[2]}<br>"
    "Company: %{customdata[1]}<br>"
    f"Region: {region_label}<br>"
    f"Category: {category.title()}<br>"
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
        barcode, comp, brand, name, xv, yv, nova_lbl, ns_lbl = _cd
        detail_cols = st.columns(6)
        detail_cols[0].markdown(f"**Company**\n\n{comp}")
        detail_cols[1].markdown(f"**Brand**\n\n{brand}")
        detail_cols[2].markdown(f"**Product**\n\n{name}")
        detail_cols[3].markdown(f"**{x_label}**\n\n{float(xv):.2f}")
        detail_cols[4].markdown(f"**{y_label}**\n\n{float(yv):.2f}")
        detail_cols[5].markdown(f"**NOVA / Nutri-Score**\n\n{nova_lbl} / {ns_lbl}")
        st.caption(f"Barcode: {barcode}")
