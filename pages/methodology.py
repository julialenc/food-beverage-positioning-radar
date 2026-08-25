"""
Methodology page for the Streamlit app.

This page translates the technical methodology into final-user language.
Detailed metric definitions and caveats remain in docs/METHODOLOGY.md and
docs/LIMITATIONS.md.
"""

from __future__ import annotations

import streamlit as st

from shared import components

GITHUB_URL = "https://github.com/julialenc/food-beverage-positioning-radar"


components.inject_base_css()
components.render_header(
    "Methodology",
    "How to read the data, evidence layers, metrics, and limitations in this app.",
)

st.markdown(
    """
This app shows structured observations about packaged food and beverage
products. This beta MVP uses Open Food Facts data, rule-based cleaning, and
documented mapping layers. It does not produce product verdicts.

The app combines two types of evidence:

**What the product is**  
Ingredients, nutrition values, processing indicators, Nutri-Score, NOVA
group, company / brand mapping, market / region tags, and nutrition reference
points.

**What the product tells**  
Product claims, benefit cues, ingredient claims, and pack communication,
based on front-of-pack image analysis where available.

The goal is to help users explore product and category patterns, not to
decide whether a product is good, bad, healthy, unhealthy, misleading, or
compliant.
"""
)

st.markdown("### 1. Data Source")
st.markdown(
    """
Product records come from **Open Food Facts**, an open, crowdsourced database
of food and beverage products.

Open Food Facts is rich and useful, but it is not a retail audit database.
Product names, brands, categories, images, ingredients, nutrition values,
Nutri-Score, NOVA group, and country tags may vary in completeness and
quality.

Product counts in this app are counts of observed product records in the
cleaned database. They are not sales volumes, market shares, shelf shares,
launch counts, distribution-weighted estimates, or consumer-demand measures.

A product appearing in the dataset means it was observed in Open Food Facts.
It does not mean the product is currently available, widely distributed,
commercially important, or representative of sales in a given market.
"""
)

st.markdown("### 2. Evidence Layers")
st.markdown(
    """
The app separates composition data from pack-communication evidence.

**Composition data** comes from Open Food Facts structured product records. It
includes ingredients, nutrition values, Nutri-Score, NOVA group, product
category, brand, company mapping, and country tags. This is the broad observed
product base used for Market Overview summaries.

**Pack-communication evidence** comes from OCR and LLM analysis of selected
front-pack images. It captures claims, benefit cues, ingredient cues, and
other visible pack communication where valid image evidence exists.

Pack-communication evidence is not available for every product and is not
based on a random representative sample. It should not be read as
market-level claim prevalence.
"""
)

st.markdown("### 3. App Views")
st.markdown(
    """
**Market Overview** shows high-level patterns for a selected country-category
base. It is designed for nutrition, processing, reference classification,
company, brand, and market / region exploration.

Market Overview uses Open Food Facts composition data for aggregate summaries.
It does not use OCR or LLM pack-claim extraction to report market-level claim
shares.

**Product Explorer** lets users search and inspect individual products. It
shows product-level evidence: nutrition values, reference classifications,
product image, pack-image claim evidence where available, and exportable
filtered results.
"""
)

st.markdown("### 4. Market Overview Summaries")
st.markdown(
    """
Market Overview is designed to answer:

**Within this selected Open Food Facts country-category base, what composition
and classification patterns do we observe, and which companies, brands, and
products contribute to them?**

It is not designed to answer:

- What is the market share?
- Which country is healthier?
- Which company has the best portfolio?
- How many products in the real market claim a specific benefit?
- Which brands are winning?

For this reason, Market Overview should be read as an observed-record summary,
not a market report in the retail-audit sense.

The app avoids country-category comparisons that could be misleading, such as
"US Snacks vs France Snacks." Open Food Facts coverage differs by country and
contributor behaviour. Safer comparisons are made within the same selected
base, such as one brand compared with the observed France Dairy records.
"""
)

st.markdown("### 5. Category Report")
st.markdown(
    """
**Category Report** is the high-level summary view for one selected
country-category base.

Example:

**France · Snacks**  
**France · Dairy**

The selected country-category base acts as the reference base for the page.

Users can expand from the selected base to companies, brands, and products.
Company rows are used as navigational roll-ups, not as full nutrition
profiles. Company portfolios can be very heterogeneous, so company-level
nutrition aggregation should be interpreted cautiously or avoided.

Brand-level summaries may be shown where there are enough product records, but
they remain observed-record summaries, not market-share or sales-weighted
views.
"""
)

st.markdown("### 6. Brand Compare")
st.markdown(
    """
**Brand Compare** lets users compare two brands or product groups within the
same selected country-category base.

The shared base matters. For example, comparing two brands within
**France · Dairy** is safer than comparing France Dairy with US Snacks, because
the products are being interpreted within the same observed dataset scope.

Brand Compare is intended for brand-level and product-level comparison. It
should not be read as company portfolio scoring or as a recommendation of one
brand over another.
"""
)

st.markdown("### 7. Product Map")
st.markdown(
    """
**Product Map** plots individual products across selected quantitative
nutrition metrics.

Each point represents an observed product record from the cleaned Open Food
Facts dataset. Extreme values may reflect unusual products, data-entry issues,
category contamination, or source-data errors.

Product Map is useful for finding outliers and patterns, but it should not be
read as a representative market landscape.
"""
)

st.markdown("### 8. Nutrition And Processing Data")
st.markdown(
    """
Nutrition values are sourced from Open Food Facts where available. The app may
show fields such as energy, protein, fibre, sugars, saturated fat, salt,
carbohydrates, and fat.

The app preserves raw Open Food Facts nutrition values and adds governance
flags for aggregate analysis. Product Explorer can show imperfect but useful
records. Market Overview calculations and charts exclude records with
implemented hard data-quality flags, material energy/macronutrient
inconsistencies, or documented chart-distorting outlier rules where available.

**Nutri-Score** and **NOVA group** are external reference classifications
sourced from Open Food Facts. They are not created by this project and should
not be read as this tool's own product judgment.

Nutri-Score summarizes aspects of a product's nutrition profile where
available. NOVA describes the level of industrial processing assigned in Open
Food Facts. Neither system is a personalized dietary recommendation, a
product-quality verdict, or a full explanation of the product.
"""
)

st.markdown("### 9. Nutrition Reference Points")
st.markdown(
    """
Nutrition reference points show whether selected nutrients, such as sugar,
saturated fat, fat, or salt, sit above a chosen reference threshold per 100g
or 100ml.

These reference points are used for comparison across products. They are not a
legal assessment, health-risk assessment, or product recommendation.

A product can sit above a nutrition reference threshold and still make an
accurate claim. The reference point is context, not a contradiction by itself.
"""
)

st.markdown("### 10. Front-Pack Claim Evidence")
st.markdown(
    """
A sampled subset of image-eligible products has undergone front-of-pack image
analysis using OCR and LLM extraction.

When the app shows pack-image claim evidence, it means visible front-pack text
was extracted and classified from the product image.

There are three important evidence states:

**Pack claim found**  
The front pack was analyzed and one or more claims were detected.

**Pack analyzed, no claim found**  
The front pack was analyzed, but no claim was identified in the taxonomy.

**No valid pack observation**  
The product was not analyzed, had no usable front-pack image, or extraction
failed. In this case, absence of a displayed pack claim does not mean the
product has no claim. It only means no valid front-pack observation is
available in this dataset.

Where no valid pack observation exists, any product-name, label, or
ingredient-derived fallback signal must not be read as a confirmed
front-of-pack observation.
"""
)

st.markdown("### 11. Positioning Signals")
st.markdown(
    """
The app groups front-pack communication into practical **Positioning** labels.

Examples include protein, fibre, vitamins and minerals, no added / reduced
sugar, organic, plant-based, sustainability, heritage, or other visible
pack-positioning signals.

These labels are based on OCR and LLM extraction from analyzed front-pack
images where available. They do not assess whether a claim is legally valid,
substantiated, misleading, or compliant.

If a product is not vision-analyzed, the app shows it as **Not tested** rather
than assuming that no claim exists.
"""
)

st.markdown("### 12. Company And Brand Mapping")
st.markdown(
    """
Brand names from Open Food Facts are normalized to make filtering easier.
Some brands map clearly to one company or owner. Others depend on market,
licensing, product type, or recent ownership changes.

Brand handling is separated into three layers: raw Open Food Facts brand
evidence, normalized consumer-facing brand, and company / owner mapping. For
market-specific brands, the app uses scoped mapping rules where possible.
Cases that cannot be resolved safely are shown as **Other / not mapped** in
the app, while backend review status is preserved for audit.

Company filters are navigational roll-ups. They help users explore
portfolios, but the strongest analytical unit remains the product, brand,
category, and market / region.
"""
)

st.markdown("### 13. Beverage View Segment")
st.markdown(
    """
For Market Overview, beverages are split into practical MVP segments so that
ready-to-drink products are not mixed with syrups, concentrates, powders,
tea bags, coffee capsules, alcohol, and similar preparation-based or
alcohol-related products in the same nutrition charts.

The beverage segment classifier is rule-based and intended for launch-stage
chart readability, not as a final beverage taxonomy. Unknown beverage records
are work in progress and should not be interpreted as a separate market
segment.
"""
)

st.markdown("### 14. Market / Region Filter")
st.markdown(
    """
Market / region is derived from Open Food Facts country tags.

It is useful for directional market exploration, but it does not mean verified
retail distribution, market share, or confirmed product availability.

A product can appear in more than one market / region if Open Food Facts has
multiple country tags for the same product.
"""
)

st.markdown("### 15. How To Interpret The App")
st.markdown(
    """
Use the app to explore patterns, compare products, identify claim territories,
inspect examples, and generate hypotheses.

Do not use it to conclude that a product is misleading, illegal, healthier,
worse, or recommended. The app shows evidence layers and reference points.
Interpretation remains with the user.
"""
)

st.markdown("### 16. Known Limitations")
st.markdown(
    """
Important current limitations:

- Open Food Facts categories can be broad or inconsistent.
- Some product records are incomplete.
- The database does not contain sales volume, market share, shelf share,
  launch counts, distribution, or consumer-demand data.
- Product counts are observed records, not market size.
- Image-based claim extraction covers a sampled subset, not every product.
- OCR quality varies by image quality, pack design, language, and layout.
- Pack-communication evidence is not representative of the full Open Food
  Facts product base.
- The reviewed MVP category scopes have been cleaned, but residual source
  category noise may remain.
- Company ownership can be market-specific, license-specific, or
  product-type-specific.
- Beverage segmentation is MVP-ready but not a final beverage taxonomy.
- Market / region tags are directional and based on Open Food Facts country
  tags.
- Missing values are not zero and should not be interpreted as absence.
"""
)

st.link_button("View Methodology And Code On GitHub", GITHUB_URL)
