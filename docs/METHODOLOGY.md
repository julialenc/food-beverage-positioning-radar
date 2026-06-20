# Methodology

This document defines how Food & Beverage Positioning Radar measures what it
measures, and — just as importantly — what each metric does not measure. It
exists so that no output from this tool is read as a verdict it was never
designed to give. For exact field names and types, see
`docs/COLUMN_DESCRIPTIONS.md`; this document explains the concepts behind them.

## Core principle

This tool maps how packaged foods and beverages position themselves through
claims, ingredients, nutrition, processing, and product design. It does not
assess legal compliance, assign health verdicts, or recommend products to
consumers. Benchmarks are reference points for comparison, not pass/fail
judgments. Interpretation of any pattern shown here is the responsibility of
the user.

## Data source

Product data is sourced from Open Food Facts (OFF), an open, crowdsourced
database licensed under the Open Database License (ODbL). See
`docs/LIMITATIONS.md` for coverage, quality, and licensing details.

## Pack-image claim extraction process

A subset of products (currently around 4,700, selected via a purposive
tiered sampling strategy favouring brands and categories where positioning
claims are most likely to be present) have undergone front-of-pack image
analysis: Azure AI
Vision's Read API performs OCR on the product image, and the extracted text
is passed to Azure OpenAI's `gpt-4.1-nano` deployment for structured claim
extraction. Total cost for the full run to date was approximately 8 CHF.
Products outside this subset rely on ingredient-text and product-name signals
only (see "Claim taxonomy" below).

## Metric definitions

Each metric below states what it measures and what it explicitly does not
measure.

### Claim taxonomy
**Status:** Implemented
**What it measures:** Groups pack claims into five categories — functional,
free-from / reduced-content, natural/organic, other positioning, or no claim
identified — and a secondary sub-category (e.g. protein, gut health, no
added sugar, heritage). Sourced from pack-image extraction where
available (`claim_source` = `vision`), falling back to combined
ingredient-text and product-name signals otherwise (`claim_source` =
`ingredient_text_only`). Stored category codes (`FUNCTIONAL`, `FREE_OF`,
etc.) are not display-ready — see `docs/UI_LABELS.md` for the
canonical code-to-label mapping used by the Streamlit app and Power BI
deck.
**What it does not measure:** Whether a claim is legally valid, substantiated,
or compliant with food labelling regulation in any jurisdiction. It also
reflects only the single highest-priority category present on a
product, not a complete count of every claim territory found — for
that, the underlying `pack_claims_found` field lists every individual
claim detected.

### Ingredient markers
**Status:** Implemented
**What it measures:** Identifies ingredient-processing markers in the
ingredient list (e.g. emulsifiers, artificial sweeteners, glucose syrups,
modified starches) and summarizes them into a weighted score
(`composition_marker_score`, 0–40, using pre-assigned marker weights —
see `docs/COLUMN_DESCRIPTIONS.md` for the exact formula), with a
categorical reference band
(`Extensive`/`Moderate`/`Limited`/`Minimal markers`). This is a
composition-only signal, computed independently of any pack claim.
**What it does not measure:** Whether a product is good or bad, or whether
any individual marker is harmful in the amount present.

### Positioning-to-composition gap
**Status:** Implemented
**What it measures:** A composite signal combining the ingredient-marker
score with the weight of front-of-pack claims present and, when claims are
present, additional context from processing level and Nutri-Score. A higher
value generally reflects a combination of more pronounced ingredient markers
and more emphatic front-of-pack positioning. The score (`positioning_composition_gap`,
0–100) has a categorical reference band (`High`/`Moderate`/`Low`/`Minimal
positioning-composition signal`) — labelled "signal" rather than "gap" at
the band level specifically because of the composite-not-pure-gap caveat
below.
**What it does not measure:** Whether a product is misleading, deceptive, or
violates any advertising standard. It is also not purely a measure of
"claim versus reality" in every case: the ingredient-marker component applies
regardless of whether any claim is present, so a product with no detected
claims can still receive a non-zero value. This is a composite analytical
score, not a deception detector.

### Claim-benchmark intersections
**Status:** Implemented
**What it measures:** Specific instances where a detected positioning (a
pack claim where available, otherwise combined ingredient-text and
absence/reduction signals) co-occurs with a relevant nutrition,
ingredient, or processing benchmark signal — for example, "Protein
positioning with saturated fat above reference threshold." Computed for
every product, using whichever evidence layer fed that product's claim
taxonomy (see `claim_source` above).
**What it does not measure:** Intent. The presence of an intersection does
not imply the claim is false; both the positioning and the composition data
point can be simultaneously accurate.

### Nutrition benchmark flags
**Status:** Implemented
**What it measures:** Whether a nutrient value (sugar, saturated fat, fat,
salt) sits above a reference threshold, applied per 100g or 100ml. Stored as
neutral codes (e.g. `sugar_above_reference`), not display text — see
`docs/UI_LABELS.md` for the code-to-label mapping used by the Streamlit
app and Power BI deck. Thresholds
follow the UK Food Standards Agency's front-of-pack labelling guidance and are
used here as a single reference scheme for cross-product comparison. The EU's
mandatory nutrition declaration (Regulation 1169/2011) requires these nutrient
values to be stated on pack in a standard format, but the regulation itself
does not define high/low thresholds — that was deliberately left to individual
Member States and food businesses to develop voluntarily, which is why this
tool credits the UK FSA scheme specifically rather than EU law for the
threshold values themselves. In the MVP, liquid vs solid is approximated using
an energy-density proxy (under 100 kcal/100ml treated as liquid). This may
misclassify some categories and should be reviewed if benchmark flags become
a central reporting layer.
**What it does not measure:** Legal compliance, health risk, or suitability
for any individual. The same per-100g thresholds are applied to all products
in the dataset, including US-market products, for comparability, since FDA
per-serving daily-value percentages are not directly comparable to per-100g
data.

### NOVA / processing indicators
**Status:** Implemented (sourced from Open Food Facts)
**What it measures:** A reference classification (1–4) describing the degree
of industrial processing a product has undergone, as classified by Open Food
Facts contributors using the NOVA system.
**What it does not measure:** Product safety, health value, or quality in
isolation. NOVA group is one processing-level reference point, not a
standalone verdict.

### Nutri-Score
**Status:** Implemented where available (sourced from Open Food Facts)
**What it measures:** A standardized A–E letter grade summarizing a
product's nutrition profile, calculated from energy, sugar, saturated fat,
salt, fibre, protein, and fruit/vegetable/nut content, as provided by Open
Food Facts.
**What it does not measure:** A personalized dietary recommendation.
Nutri-Score does not account for serving size, individual dietary needs, or
non-nutritional factors such as ingredient processing or additive use.

### Product segment
**Status:** Planned, not yet implemented
**What it will measure:** Groupings of products based on shared patterns
across claims, ingredients, nutrition, processing indicators, and category,
intended to surface emerging market segments.
**What it will not measure:** Consumer suitability or health status. A
segment is a market-pattern grouping, not a recommendation tier.

### Completeness score
**Status:** Implemented
**What it measures:** Whether the structured fields most relevant to
analysis (product name, brands, ingredients text, six nutrition values,
Nutri-Score, NOVA group — eleven fields in total) are present for a given
product record. Calculated as the percentage of those eleven fields that are
populated, rounded to the nearest integer.
**What it does not measure:** Product quality. A low completeness score
reflects missing source data, not a deficiency in the product itself.

## Reporting layers: ingredient-stage vs final market-intelligence summary

Two different aggregation tables exist in the database, computed at
different points in the pipeline and serving different purposes — this
distinction matters for interpreting any brand- or category-level
summary correctly.

**`weekly_brand_summary`** is computed by `load.py`, before pack-image
claim extraction or claim taxonomy exist for any product. It reflects
ingredient-analysis-stage signals only (composition markers, NOVA,
ingredient-based claim signals) and is intended for early pipeline QA —
not as a source for claim territory shares, benchmark intersection
rates, or the positioning-to-composition gap, since none of that data
exists yet at the point this table is computed.

**`weekly_brand_positioning_summary`** is computed by `db_summary.py`,
the final reporting aggregation layer, run after `merge_scores.py` and
`tag_claims.py` have fully enriched the database. This is the actual
market-intelligence summary intended for the Power BI deck: claim
taxonomy shares, pack-claim coverage, benchmark intersection rates, and
average positioning-to-composition gap, all computed from the full
current database snapshot — not only the products changed in a given
weekly update, so a trend chart never confuses "what changed this week"
with "the observed market this week." Each reporting snapshot is
identified by `week_ending` (the reporting period) and `run_timestamp`
(the precise execution time), enabling time-series queries (e.g. "% of
products with a protein claim over time") without losing prior periods'
data.

A third table, **`positioning_example_products`**, is not a time
series at all — it is a small, curated set of neutral product examples
for Streamlit/Power BI overview pages, fully replaced on every
`db_summary.py` run. See `docs/ADR.md` ADR-012 for the full
architectural rationale for this separation.

Final Power BI exports (`powerbi_final_*.csv`) are generated by
`db_summary.py`, not by the earlier `load.py`, `merge_scores.py`, or
`tag_claims.py` exports. Those earlier exports remain useful for QA and
product-level inspection at each pipeline stage; `db_summary.py`'s
exports are the final, reporting-stage outputs intended for the Power
BI deck itself.

## Brand and company mapping

Brand strings in the source data are normalized and mapped to parent
companies for company-level filtering and aggregation. See
`docs/BRAND_COMPANY_MAPPING.md` for the mapping methodology and coverage.
Pattern metrics are computed at product level and aggregated primarily at
brand/category level. Company-level views may be used as roll-ups, but
should be interpreted cautiously because company portfolios are
heterogeneous (see `docs/ADR.md`).

## Known limitations of current methodology

See `docs/LIMITATIONS.md` for the full catalogue of known limitations
affecting interpretation, including coverage gaps, context limitations (such
as sports nutrition products), and extraction quality caveats.
