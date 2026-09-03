# Methodology

This document explains what Food & Beverage Positioning Radar measures, how the
main analytical layers are prepared, and what the outputs should not be
interpreted to mean. For exact database fields and types, see
`docs/COLUMN_DESCRIPTIONS.md`. Detailed governance is documented separately in
the specialist files referenced below.

## Core principle

Food & Beverage Positioning Radar maps how packaged foods and beverages position
themselves through claims, ingredients, nutrition, processing, and product
design.

It does **not** assess legal compliance, assign health verdicts, judge whether a
product is good or bad, or recommend products to consumers. Benchmarks are
reference points for comparison, not pass/fail judgments.

## Data source

Product data comes from Open Food Facts (OFF), an open, crowdsourced database
licensed under the Open Database License (ODbL).

OFF provides broad, reproducible product coverage, but its records can be
incomplete, duplicated, inconsistent, outdated, or uneven across markets and
brands. Product counts therefore represent observed OFF records, not sales,
market share, distribution, or shelf presence.

See `docs/LIMITATIONS.md` for the full source, coverage, quality, and licensing
caveats.

## Data preparation and governance

The app does not display raw OFF rows without preparation. The pipeline applies
separate governance layers for:

1. analytical category scope;
2. brand normalization and company routing;
3. nutrition quality and outlier treatment;
4. ingredient-based analysis;
5. front-of-pack claim extraction;
6. reporting and chart eligibility.

These layers add derived fields, mappings, and inclusion flags. They do not
rewrite the underlying OFF source evidence.

Core rules:

- preserve raw provenance where the pipeline provides raw fields, especially
  nutrition (`*_off_raw`) and brand evidence (`off_brands_raw`);
- keep missing values distinct from confirmed zeros;
- prefer exact reviewed product evidence over broad inferred rules;
- do not force uncertain classifications merely to make the dataset look
  complete;
- keep product-level display and aggregate/chart eligibility as separate
  decisions.

## Analytical scope

Launch regions:

```text
FRANCE
UK_IE
US_CANADA
```

Launch categories:

```text
snacks
cereals
dairies
beverages
```

The app displays `dairies` as **Dairy**.

Products that clearly do not belong in any of the four analytical categories
can receive a reviewed `OUT_OF_SCOPE` decision. This removes them from the
app-facing four-category universe while preserving their source/provenance
records.

## Category cleanup

OFF category tags are contributor-assigned and can inherit broad or noisy parent
categories. The Radar therefore classifies by **product format and commercial
use case**, not simply by ingredient or source category tag.

The main category principles are:

- `snacks` covers confectionery, ice cream/frozen snack desserts, savoury snacks,
  sweet biscuits/bakery snacks, snack bars, cereal bars, and fruit snacks;
- `cereals` means breakfast cereal formats such as flakes, muesli, granola,
  porridge/oatmeal, puffs, clusters, and similar bowl/hot-cereal products;
- cereal/snack bars belong in `snacks`, not `cereals`;
- finished dairy products, including drinkable yogurt and cultured dairy
  drinks, remain in `dairies`; drinkability alone does not make them beverages;
- beverage preparations such as syrups, concentrates, tea/coffee preparations,
  powders, and hot-chocolate products can remain in `beverages`;
- clear meals, cooking ingredients, sauces, baking preparations, meal
  components, and other non-comparable formats can be routed to
  `OUT_OF_SCOPE`;
- when another launch category is clearly better, a reviewed product can be
  moved rather than removed.

Snacks and cereals received detailed manual category cleanup across France,
UK/Ireland, and US/Canada. The September 2026 brand/company and regional orphan
audits also identified exact category corrections across cereals, dairies,
snacks, and beverages in France and US/Canada. Those GTIN-level decisions are
authoritative for the affected products.

Restaurant/menu observations are not packaged CPG products. Where a reliable
source/type discriminator exists, they should be filtered before analytical
category and orphan generation. Broad exclusions by restaurant brand are unsafe
because the same brand can also appear on legitimate packaged retail products.

See `docs/CATEGORY_CLEANUP.md` for the full category rules and override
precedence.

## Brand and company mapping

Brand and company are separate analytical entities.

The launch pipeline distinguishes:

```text
off_brands_raw      = raw OFF brand evidence
brand_entity_raw    = conservative extracted consumer-facing brand entity
normalized_brand    = cleaned consumer-facing brand used for brand analysis
brand_family        = optional broader umbrella for useful roll-ups
resolved_company    = directional company / owner route used for filtering
```

The app should prefer `normalized_brand` for brand display when available.
`primary_brand` is retained for legacy compatibility/provenance.

### Brand principles

- preserve the most specific supported consumer-facing brand or meaningful
  private-label line;
- do not replace a brand with its parent company;
- do not turn generic or collision-prone strings into reusable aliases without
  strong evidence;
- supplier, manufacturer, importer, distributor, bottler, co-packer, or
  licensee information is evidence, not automatic proof of brand ownership.

### Company principles

`resolved_company` is a directional navigation/reporting field, not a universal
legal ownership register.

Ownership can vary by region, market, product form, licensing arrangement,
joint venture, or recent acquisition/divestiture. Project region is evidence,
not proof of the product's actual market.

When broad routing is unsafe, exact reviewed GTIN overrides take precedence.
Where ownership cannot be established with sufficiently strong evidence, the
product remains under:

`Other / not mapped to a company`

The project deliberately prefers a **false negative to a false-positive owner
assignment**.

### Launch mapping completion

The launch mapping phase is complete and locked:

- reviewed retailer/private-label portfolios are complete;
- all nine priority manufacturer portfolios are locked after product-level
  audit and regression validation;
- the regional-category orphan review is complete across all launch regions.

An orphan candidate was defined as a normalized brand still under
`Other / not mapped to a company` with **at least 100 products within one
specific region × category bucket**.

France and US/Canada contained qualifying orphan candidates and were audited,
implemented, and validated. UK/Ireland had no qualifying orphan candidates at
that threshold.

The final criterion is satisfied: no normalized brand with at least 100
products in a single launch region-category remains under
`Other / not mapped to a company` without reviewed resolution. Individual
products can still remain under `Other` when ownership is genuinely ambiguous.

See `docs/BRAND_COMPANY_MAPPING.md` for precedence, scoped ownership logic,
reference files, and maintenance rules.

## Nutrition quality and outlier treatment

Nutrition-quality governance determines whether a record is suitable for:

- product-level display;
- aggregate calculations;
- charts.

The project does not overwrite OFF nutrition values. It preserves source values
and adds quality/inclusion flags.

Implemented launch checks include:

- hard impossibility checks such as negative nutrient values, nutrients above
  100g/100g, impossible macro mass balance, sugars above carbohydrates,
  saturated fat above total fat, and impossible energy values;
- per-100 kcal nutrient-density checks;
- energy-versus-macro consistency checks;
- Scenario C2 safeguards for low-energy beverages and small absolute kcal gaps;
- distributional plausibility review before stable tail patterns become
  deterministic rules.

Current treatment:

- hard data-quality errors are excluded from Product Explorer, aggregates, and
  charts;
- material energy-macro inconsistencies can remain visible at product level but
  are excluded from aggregates and charts;
- genuine but chart-distorting tails can remain visible in Product Explorer
  while being excluded from charts when a documented rule exists.

The final launch exclusion rate from Market Overview calculations is
approximately **3.02%**.

Within-brand nutrition plausibility checks are not yet fully implemented in the
launch MVP.

See `docs/NUTRITION_OUTLIER_GOVERNANCE.md` for the detailed rules.

## Beverage segmentation

Beverages use a separate view-segmentation layer for chart comparability:

```text
ready_to_drink_beverages
beverage_preparations_and_alcohol
unknown_beverage_segment
not_beverage
```

The segmentation prevents ready-to-drink products from being mixed
uncritically with syrups, concentrates, powders, tea/coffee preparations,
alcohol-related products, meal-replacement shakes, and other materially
different formats.

This is a chart/readability layer, not a complete beverage-market taxonomy.

## Front-of-pack claim extraction

A sampled subset of image-eligible products undergoes front-of-pack analysis:

```text
OFF image
→ Azure AI Vision OCR
→ Azure OpenAI structured claim extraction
→ validation
→ claim taxonomy
```

As of the August 2026 launch build, the current US/UK and France analytical
releases contain **17,127 valid front-of-pack observations**.

These releases are samples from the image-eligible OFF universe. They are not
retail-sales samples, market-share estimates, or a census of all packaged
products.

Two prevalence views must remain distinct:

- **sample proportion** — the observed share within the full sampled release,
  including purposive/enriched components;
- **backbone design-weighted estimate** — an approximate estimate based on the
  probability-oriented backbone of the image-eligible OFF sample.

See `docs/CLAIM_EXTRACTION.md` for sampling design, prompt history, validation,
release details, and OCR/LLM limitations.

## Metric definitions

### Positioning signals / claim taxonomy

**Status:** Implemented; Streamlit displays vision-based positioning signals.

**Measures:** Explicit front-of-pack positioning territories detected from valid
OCR/LLM observations, such as protein, fibre, vitamins/fortification, no added
or reduced sugar, organic, plant-based, heritage, sustainability, and other
pack cues.

A critical distinction is:

- `pack_claims_found = NULL` — no valid pack observation exists;
- `pack_claims_found = ""` — a valid front pack was assessed and no taxonomy
  claim was found;
- a non-empty value — one or more pack claims were detected.

A confirmed no-claim observation must not be replaced with an
ingredient-derived claim. Legacy or fallback classifications may remain for
internal QA, but they must not be presented as confirmed front-of-pack
evidence.

**Does not measure:** legal validity, substantiation, regulatory compliance, or
consumer benefit.

Stored claim codes are mapped to user-facing labels through
`docs/UI_LABELS.md`.

### Ingredient markers

**Status:** Implemented internally; not displayed as a proprietary user-facing
score in the current MVP.

**Measures:** Selected ingredient-processing markers identified in the
ingredient list and summarized internally through
`composition_marker_score`.

**Does not measure:** whether a product is healthy, unhealthy, good, bad, or
harmful at the amount consumed.

### Positioning-to-composition gap

**Status:** Legacy/internal; not a user-facing metric.

The historical `positioning_composition_gap` combines ingredient-marker and
positioning information into a composite analytical signal. Because it is not a
pure "claim versus reality" measure and can be non-zero even without a detected
claim, it is retained only for compatibility/internal analysis.

It must not be interpreted as a deception or misleading-claims score.

### Claim-benchmark intersections

**Status:** Implemented.

**Measures:** Co-occurrence between a positioning signal and a relevant
nutrition, ingredient, or processing reference point, for example protein
positioning alongside saturated fat above a reference threshold.

An intersection describes two observed signals occurring together. It does not
infer intent or claim falsity.

### Nutrition benchmark flags

**Status:** Implemented.

**Measures:** Whether sugar, saturated fat, fat, or salt sits above the
project's reference threshold per 100g or 100ml.

The project uses the UK Food Standards Agency front-of-pack threshold scheme as
a common reference for cross-product comparison. The thresholds are analytical
reference points, including for non-UK products; they are not legal-compliance
tests.

The liquid/solid distinction is approximated in the MVP using an energy-density
proxy, which can misclassify some products.

### NOVA / processing indicators

**Status:** Implemented from OFF.

**Measures:** NOVA group 1–4 as recorded/classified in the OFF source.

**Does not measure:** safety, overall health value, or product quality in
isolation.

### Nutri-Score

**Status:** Implemented where available from OFF.

**Measures:** The standardized A–E nutrition-profile grade supplied in OFF.

**Does not measure:** personalized suitability and does not incorporate every
dimension of a product, such as serving context or processing.

### Product segment

**Status:** Planned, not yet implemented.

**Will measure:** groups of products sharing patterns across positioning,
ingredients, nutrition, processing, and category.

A segment will be a market-pattern grouping, not a health or recommendation
tier.

### Completeness score

**Status:** Implemented.

**Measures:** The percentage of eleven core structured fields populated for a
product: product name, brands, ingredient text, six nutrition values,
Nutri-Score, and NOVA group.

**Does not measure:** accuracy or product quality. A populated field can still
be wrong, and a low score primarily indicates missing source data.

## Reporting layers

Three database outputs serve different purposes.

### `weekly_brand_summary`

Generated at the ingredient-analysis stage before pack-image claim extraction.
It is primarily a pipeline/QA summary and should not be used as the final source
for pack-claim territory shares or benchmark-intersection reporting.

### `weekly_brand_positioning_summary`

Generated after the database has been fully enriched. This is the final
reporting aggregation layer for claim taxonomy shares, pack-claim coverage,
benchmark intersections, and related market-intelligence summaries.

Each snapshot represents the full current database state for its reporting
period, rather than only products changed during that week.

### `positioning_example_products`

A small curated set of neutral product examples used by Streamlit overview
pages. It is refreshed rather than treated as a historical time series.

See `docs/ADR.md` for the architectural rationale behind the reporting layers.

## Interpretation limits

The most important interpretation boundaries are:

- OFF coverage and data quality are uneven;
- product counts are not sales or market share;
- category and company fields are governed analytical classifications, not
  perfect universal taxonomies or legal ownership determinations;
- nutrition flags decide analytical suitability rather than correcting source
  data;
- beverage segmentation exists primarily for comparability;
- image-based claim analysis is limited to products with usable front-of-pack
  evidence and remains subject to OCR/image-quality error;
- missing values, failed observations, and confirmed zeros are different states.

See `docs/LIMITATIONS.md` for the complete limitation catalogue.
