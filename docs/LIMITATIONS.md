# Data source, license, and limitations

**Status:** Launch documentation — current  
**Last updated:** September 2026

This document catalogs the main limitations affecting interpretation of
Food & Beverage Positioning Radar outputs. For metric definitions and
"what it measures / what it does not measure", see `docs/METHODOLOGY.md`.

## Data source: Open Food Facts

Product data is sourced from Open Food Facts (OFF), an open, crowdsourced
database. Several limitations are inherent to the source and remain relevant
even after project-level cleaning.

### Coverage is uneven

OFF coverage varies by country, category, brand, image availability, and
contributor activity. Product presence in the database does not mean that a
product is widely distributed, currently sold, or commercially important in a
specific market.

The launch regions — France, UK/Ireland, and US/Canada — are analytically
reviewed scopes for this project, not complete censuses of those retail markets.

### Product counts are not market share

The Radar has no sales, distribution, household penetration, or shelf-space
data. Counts represent observed OFF product records.

A brand with many observed products is not necessarily a market leader, and a
brand with few records is not necessarily commercially small. The same
limitation applies to brand/category trends and all aggregate reporting tables.

### Crowdsourced fields can be wrong or incomplete

Product names, brands, categories, countries, images, ingredients, and
nutrition values can be missing, duplicated, outdated, inconsistent, or entered
at different levels of detail.

The `completeness_score` measures field population, not accuracy. A complete
record can still contain incorrect source values.

### Missing is not zero

Missing values, failed observations, empty strings, and declared zeros are
different states and must remain distinct.

For pack claims in particular:

- `pack_claims_found = NULL` means no valid pack observation exists;
- `pack_claims_found = ""` means a valid front pack was assessed and no taxonomy
  claim was found.

### Image availability is selective

Not all OFF products have a usable front-of-pack image. Products without a
usable image cannot contribute confirmed image-based claim observations.

Image coverage can therefore differ systematically by brand, category, market,
or contributor activity.

## Category limitations

OFF categories are contributor-assigned folksonomy tags rather than a clean
retail taxonomy. The project applies governed category rules before products
enter the four launch analytical categories:

```text
snacks
cereals
dairies
beverages
```

Snacks and cereals received detailed manual category cleanup across the three
launch regions. The September 2026 mapping/orphan audits also produced reviewed
GTIN-level category corrections across France and US/Canada, including category
moves and `OUT_OF_SCOPE` decisions.

This materially improves the launch base, but it does **not** create a universal
or perfect food taxonomy. Edge product forms can remain debatable, and source
noise can reappear when OFF records change or new products are ingested.

Restaurant/menu records are not intended to be part of the packaged CPG
universe. A large US/Canada beverage leakage was identified during audit and
reviewed. Future refreshes can still reintroduce similar source contamination
if upstream source/type signals change or are incomplete.

`OUT_OF_SCOPE` is an analytical decision for this Radar, not a statement that a
product is invalid or incorrectly classified in OFF.

See `docs/CATEGORY_CLEANUP.md` for the launch taxonomy and exact-override
precedence.

## Brand and company limitations

### Brand strings remain source-dependent

OFF brand strings can contain spelling variants, parent companies, multiple
brands, retailer references, historical names, or contributor noise.

The launch normalization layer has been extensively reviewed, including
retailer/private-label portfolios, the nine priority manufacturers, and the
regional orphan-brand exercise. This substantially reduces material
fragmentation, but it cannot guarantee that every individual OFF brand string
is correct or optimally normalized.

### Company / owner is directional

`resolved_company` is a company-navigation and reporting field, not a universal
legal ownership register.

Ownership can vary by market, product form, licensing arrangement, joint
venture, private-label architecture, acquisition/divestiture timing, or import
route. The project uses scoped rules and exact GTIN overrides where broad
mapping is unsafe.

The launch mapping phase is locked, and no normalized brand with at least
100 products in a single launch region-category remains under
`Other / not mapped to a company` without reviewed resolution.

This does **not** mean every individual product has a specific owner assigned.
Products can remain under `Other / not mapped to a company` when ownership
cannot be established with sufficiently strong evidence. The project
deliberately prefers a false negative to a false-positive owner assignment.

See `docs/BRAND_COMPANY_MAPPING.md` for the mapping hierarchy and maintenance
rules.

## Nutrition limitations

### Nutrition governance is not source correction

OFF nutrition values come from pack declarations and contributor entries, not
independent laboratory analysis.

The pipeline adds quality statuses and inclusion flags to determine whether a
record is suitable for Product Explorer, aggregate calculations, and charts. It
does not claim to identify which source field is wrong in every inconsistent
record, and raw OFF values remain traceable where provenance fields are
available.

Some records can therefore remain visible at product level while being excluded
from aggregate analysis.

See `docs/NUTRITION_OUTLIER_GOVERNANCE.md` for the detailed rules.

### Within-brand plausibility is not fully implemented

The launch MVP handles hard impossibilities, per-100 kcal nutrient-density
checks, energy-macro consistency, Scenario C2 safeguards, and documented
distributional rules.

It does not yet systematically flag every unusually low or high nutrition value
relative to comparable products from the same brand.

### Benchmark thresholds are analytical references

Nutrition benchmark flags for sugar, saturated fat, fat, and salt use the UK
Food Standards Agency front-of-pack threshold scheme as one consistent
cross-product reference.

The thresholds are applied across markets for comparability. They are not
universal nutrition standards and are not legal-compliance tests for products
sold in other jurisdictions.

### Liquid/solid treatment is approximate

The MVP uses an energy-density proxy to determine which benchmark threshold set
to apply. Products below 100 kcal/100ml are treated as liquid.

This can misclassify some semi-liquid foods, concentrates, or unusual product
formats.

### Per-100g / per-100ml comparisons ignore serving context

Most nutrition comparisons use a common per-100g or per-100ml basis. They do not
account for typical serving size, preparation method, consumption frequency, or
usage occasion.

This matters particularly for concentrated products, powders, confectionery,
spreads, sauces, cereals, and sports/performance products.

## Beverage segmentation limitations

Market Overview separates beverages into:

```text
ready_to_drink_beverages
beverage_preparations_and_alcohol
unknown_beverage_segment
not_beverage
```

This is a rule-based comparability layer designed to prevent materially
different beverage formats from distorting charts. It is not a complete
commercial beverage taxonomy.

Unknown records should not be interpreted as a distinct market segment.

## Front-of-pack claim coverage

As of the August 2026 launch build, the current US/UK and France analytical
releases contain **17,127 valid front-of-pack observations**.

These observations come from sampled, image-eligible OFF products. They are not:

- a retail-sales sample;
- a market-share estimate;
- a census of packaged products;
- representative of products with no usable OFF image.

The Streamlit MVP displays vision-based positioning signals. Legacy or fallback
ingredient/name classifications can remain in the pipeline for internal QA, but
they must not be presented as confirmed pack observations.

See `docs/CLAIM_EXTRACTION.md` for the sampling design and release methodology.

## Extraction and detection limitations

### Model and prompt dependency

Pack-claim extraction depends on the OCR engine, LLM deployment, prompt version,
validation rules, and model behavior at the time of the run.

A future change to any of these components can change results. The pipeline
stores model/prompt/run metadata so releases can be audited rather than assumed
to be directly interchangeable.

### OCR quality and pack design

Low-resolution, cropped, angled, low-contrast, or highly stylized images can
produce incomplete OCR and missed claims.

Visual hierarchy is also flattened by OCR. A front pack containing origin,
certification, producer, or short ingredient text can resemble a legal or
ingredient panel in extracted text.

Panel-context review reduces this risk but does not eliminate it.

### Claim taxonomy is intentionally conservative

Some claim-like text can be captured in `other_claims` or
`detected_claim_phrases` without mapping into a boolean taxonomy field.

The project does not selectively rescue uncertain cases simply to increase
claim counts, so some claim prevalence can be understated.

### Promotional wording can resemble positioning

Messages such as "+10% free", "new size", or "20% more" can resemble
comparative positioning after OCR. Prompt rules reduce this error, but residual
misclassification can remain, particularly in older extraction runs.

### Ingredient-derived signals can create context errors

Ingredient text is useful for composition analysis but is not equivalent to a
front-of-pack claim.

Examples of known context risks include:

- mandatory enrichment declarations being detected as fortification language;
- `nature` meaning "plain" in French/Belgian/Swiss product naming rather than
  naturalness positioning.

Rules reduce these false positives, but ingredient-derived signals must remain
separate from confirmed pack observations.

### Language coverage is limited

Ingredient-based marker analysis is currently designed for English, French, and
bilingual EN/FR ingredient text. Other-language products retain other usable
fields but should not receive silent ingredient-marker false negatives.

Approximately 16% of the current dataset falls outside the implemented
ingredient-language scope.

## Legacy/internal analytical fields

`composition_marker_score` and `positioning_composition_gap` remain in parts of
the pipeline for historical compatibility and internal analysis.

They are not displayed as proprietary user-facing scores in the current
Streamlit MVP and should not be interpreted as product-quality, health, or
deception scores.

## Licensing and attribution

The repository code and original project documentation are licensed under the
Apache License, Version 2.0. Reuse and redistribution should retain the
`LICENSE` and `NOTICE` files and credit **Food & Beverage Positioning Radar by
Julia Lenc**.

Open Food Facts data is licensed separately under the Open Database License
(ODbL). Use requires attribution to Open Food Facts, and redistribution of
derived structured databases may trigger ODbL share-alike obligations.

Required attribution: **Open Food Facts** — https://world.openfoodfacts.org

This document is not legal advice. Users redistributing derived datasets should
review the ODbL terms for their specific use case.
