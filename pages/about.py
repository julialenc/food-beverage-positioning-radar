"""
About page for the Streamlit app.

This page is written for final users, not repository readers. Keep it
plain-language and short; technical detail belongs in docs/.
"""

from __future__ import annotations

import streamlit as st

from shared import components

GITHUB_URL = "https://github.com/julialenc/food-beverage-positioning-radar"


components.inject_base_css()
components.render_header(
    "About",
    (
        "A neutral market-intelligence app for exploring what packaged foods "
        "contain, how they are classified, and what they communicate on pack."
    ),
)

st.markdown(
    """
Food & Beverage Positioning Radar helps users explore packaged food and
beverage products from two sides:

This is a **beta MVP**. It uses Open Food Facts data plus documented cleaning,
nutrition-quality, brand-normalization, and company-mapping layers. Some
records may remain incomplete, imperfect, or unresolved at the source-data
level.

**What the product is**  
Ingredients, nutrition values, processing indicators, Nutri-Score, NOVA
classification, company / brand mapping, market / region tags, and nutrition
reference points.

**What the product tells**  
Product claims, benefit cues, ingredient claims, and pack communication,
based on front-of-pack image analysis where available.

The tool is built for CPG professionals, insight teams, market analysts,
consultants, nutrition professionals, dietitians, and researchers who want to
explore product and category patterns using a transparent open-data source.

It is not a product-rating app, health recommendation tool, legal assessment,
retail audit, market-share report, or consumer shopping guide. It does not
decide whether a product is good, bad, healthy, unhealthy, misleading, or
compliant. It organizes product data so users can inspect patterns and make
their own interpretation.
"""
)

st.markdown("### What You Can Do In This App")
st.markdown(
    """
Use **Market Overview** to explore high-level nutrition, processing,
reference-classification, company, brand, category, and market / region
patterns across observed Open Food Facts records.

Use **Product Explorer** to search individual products, inspect nutrition
values and reference classifications, view pack-image claim evidence where
available, and export filtered product records.
"""
)

st.markdown("### How To Read The Data")
st.markdown(
    """
The app separates two evidence layers:

**Composition data** comes from Open Food Facts structured product records.
This is the broad observed product base used for aggregate Market Overview
summaries.

**Pack-communication evidence** comes from OCR and LLM analysis of selected
front-pack images. This evidence is shown at product level where available.
It is not treated as representative market-level claim prevalence.

Counts and percentages in the app reflect observed records in the cleaned
Open Food Facts dataset. They are not sales volumes, market shares, shelf
shares, launch counts, retail distribution, or consumer-demand estimates.
"""
)

st.markdown("### Data Source And Limitations")
st.markdown(
    """
The underlying product data comes from **Open Food Facts**, an open,
crowdsourced database of food and beverage products.

Because the source is crowdsourced, some records may be incomplete,
inconsistently categorized, duplicated, missing images, or affected by label
and country-tag limitations. The app keeps these limitations visible rather
than hiding them.

Source data: **Open Food Facts**, licensed under **ODbL**.
"""
)

st.link_button("View Project On GitHub", GITHUB_URL)
