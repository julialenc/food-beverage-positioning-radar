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

A sampled subset of image-eligible products has undergone front-of-pack image
analysis. Across the current US/UK and France analytical releases, the project
contains 17,127 valid front-of-pack observations. Azure AI Vision's Read API
performs OCR on the product image, and the extracted text is passed to Azure
OpenAI's `gpt-4.1-nano` deployment for structured claim extraction. Total OCR
and LLM cost for the US, UK, and France runs was approximately 20 CHF.

The sampled releases are designed to study claim territories within an
image-eligible Open Food Facts sampling frame. They are not retail-sales
samples, market-share estimates, or a census of all packaged products. When
prevalence is reported from the extraction releases, this project distinguishes
between:

- **Sample proportion:** the observed proportion among all sampled products,
  including purposive components intentionally enriched for analytically
  interesting claim territories.
- **Backbone design-weighted estimate within the image-eligible OFF sampling
  frame:** an approximate design-weighted estimate based only on the
  probability-oriented backbone component of the sample. These weights are
  approximate after brand capping, and Open Food Facts itself is not a
  probability sample of retail sales or shelf presence.

See `docs/CLAIM_EXTRACTION.md` for the full sampling design, prompt history,
release record, extraction validator, and OCR/LLM limitations.

## Metric definitions

Each metric below states what it measures and what it explicitly does not
measure.

### Claim taxonomy
**Status:** Implemented
**What it measures:** Groups detected positioning into five categories —
functional, free-from / reduced-content, natural/organic, other positioning,
or no claim identified — and a secondary sub-category (e.g. protein, gut
health, no added sugar, heritage). Where a valid front-pack observation exists,
the taxonomy is sourced from OCR/LLM pack-image extraction (`claim_source` =
`vision`). Where no valid pack observation exists, a fallback classification
may rely on product-name, label, and ingredient-derived signals
(`claim_source` = `ingredient_text_only`). Stored category codes
(`FUNCTIONAL`, `FREE_OF`, etc.) are not display-ready — see
`docs/UI_LABELS.md` for the canonical code-to-label mapping used by the
Streamlit app.

The distinction between missing pack evidence and a confirmed no-claim front
pack is load-bearing:

- `pack_claims_found = NULL` means no valid pack observation exists: not
  analyzed, non-front image, or extraction failure. This is the only state
  where ingredient/name fallback is allowed.
- `pack_claims_found = ""` means the front pack was assessed and no taxonomy
  claim was found. This must remain a true no-claim observation and must not
  trigger ingredient-derived fallback.
- `pack_claims_found = "..."` contains pipe-separated claims detected from
  front-pack evidence.

Ingredient-derived fallback classifications must not be presented as
front-of-pack observations in the user interface or reporting language.
**What it does not measure:** Whether a claim is legally valid, substantiated,
or compliant with food labelling regulation in any jurisdiction. It also
reflects only the single highest-priority category present on a
product, not a complete count of every claim territory found — for
that, the underlying `pack_claims_found` field lists every individual
claim detected.

### Ingredient markers
**Status:** Implemented internally; not a user-facing score in the current MVP
**What it measures:** Identifies ingredient-processing markers in the
ingredient list (e.g. emulsifiers, artificial sweeteners, glucose syrups,
modified starches) and summarizes them into a weighted score
(`composition_marker_score`, 0–40, using pre-assigned marker weights —
see `docs/COLUMN_DESCRIPTIONS.md` for the exact formula), with a
categorical reference band
(`Extensive`/`Moderate`/`Limited`/`Minimal markers`). This is a
composition-only signal, computed independently of any pack claim.
The score remains in the pipeline for historical compatibility and internal
analysis, but proprietary composite-style scores are not displayed in the
current Streamlit MVP.
**What it does not measure:** Whether a product is good or bad, or whether
any individual marker is harmful in the amount present.

### Positioning-to-composition gap
**Status:** Legacy/internal; not a user-facing metric in the current MVP
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
score, not a deception detector. Because of this interpretability limitation,
the score is retained only for historical/internal compatibility and is not
shown as a proprietary score in the current Streamlit MVP.

### Claim-benchmark intersections
**Status:** Implemented
**What it measures:** Specific instances where detected positioning co-occurs
with a relevant nutrition, ingredient, or processing benchmark signal — for
example, "Protein positioning with saturated fat above reference threshold."
For products with valid OCR/LLM extraction, the positioning side comes from
front-pack evidence. For products without a valid pack observation, any
fallback-derived intersection should be interpreted as a weaker evidence layer
and labelled accordingly through `claim_source`.
**What it does not measure:** Intent. The presence of an intersection does
not imply the claim is false; both the positioning and the composition data
point can be simultaneously accurate.

### Nutrition benchmark flags
**Status:** Implemented
**What it measures:** Whether a nutrient value (sugar, saturated fat, fat,
salt) sits above a reference threshold, applied per 100g or 100ml. Stored as
neutral codes (e.g. `sugar_above_reference`), not display text — see
`docs/UI_LABELS.md` for the code-to-label mapping used by the Streamlit
app. Thresholds follow the UK Food Standards Agency's front-of-pack labelling guidance and are
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
`tag_claims.py` have fully enriched the database. It contains claim taxonomy
shares, pack-claim coverage, benchmark intersection rates, and other
reporting-stage summaries computed from the full current database snapshot —
not only the products changed in a given weekly update, so a trend chart never
confuses "what changed this week" with "the observed market this week." Each
reporting snapshot is identified by `week_ending` (the reporting period) and
`run_timestamp` (the precise execution time), enabling time-series queries
(e.g. "% of products with a protein claim over time") without losing prior
periods' data.

A third table, **`positioning_example_products`**, is not a time
series at all — it is a small, curated set of neutral product examples
for Streamlit overview pages, fully replaced on every `db_summary.py` run.
See `docs/ADR.md` ADR-012 for the full architectural rationale for this
separation.

Reporting-stage exports generated by `db_summary.py` are separate from the
earlier `load.py`, `merge_scores.py`, or `tag_claims.py` exports. Those earlier
exports remain useful for QA and product-level inspection at each pipeline
stage; `db_summary.py` outputs are the final aggregate reporting layer used by
the Streamlit analytical board and any downstream analysis.

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
as sports nutrition products), and extraction quality caveats. Current
methodology caveats that materially affect interpretation include:

- **Open Food Facts category contamination:** the current cereals release
  figures include pasta, bread, flour, rusks, breadsticks, and puff pastry
  products; snacks contamination by noodles is also under review. These are
  source taxonomy and filtering issues, not claim-extraction failures.
- **OCR and pack-design limitations:** OCR quality degrades on dark packs,
  angled or cropped images, small thumbnails, and highly stylized typography.
- **Panel-classification residual error:** some valid front packs are likely
  still classified as non-front, especially where certification, origin, or
  short ingredient declarations dominate the OCR text.
- **Unmapped claim understatement:** some claim-like text captured in
  `other_claims` or `detected_claim_phrases` is not mapped into the boolean
  taxonomy, producing a small estimated understatement of claim prevalence in
  release-01.
- **Missing is not zero:** null values, failed observations, and confirmed zero
  values have different meanings and must not be collapsed during analysis.
