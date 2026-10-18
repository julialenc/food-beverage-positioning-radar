# Methodology

This document explains what Food & Beverage Positioning Radar measures, how the
main analytical layers are prepared, and what the outputs should not be
interpreted to mean. For exact database fields and types, see
`docs/03_PROJECT_REFERENCE/04_DATA_DICTIONARY.md`. Detailed governance is documented separately in
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

See `docs/03_PROJECT_REFERENCE/03_LIMITATIONS.md` for the full source, coverage, quality, and licensing
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

See `docs/01_PRODUCT_DATA_GOVERNANCE/01_CATEGORY_SCOPE_AND_CLEANUP.md` for the full category rules and override
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

See `docs/01_PRODUCT_DATA_GOVERNANCE/02_BRAND_COMPANY_MAPPING.md` for precedence, scoped ownership logic,
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
- guarded treatment of energy-formula limitations for low-energy and
  alcohol/fermented beverages before generating mismatch warnings;
- within-brand plausibility warnings;
- distributional plausibility review before stable tail patterns become
  deterministic rules;
- chart-range bands for display readability.

Scenario A/B/C/C2 exclusion rates describe historical experiments. They do not
define the current Market Overview calculation population; the final hard-gate
and warning policy below is authoritative.

Current treatment:

- hard data-quality errors are excluded from Product Explorer, Market Overview
  calculations, and Market Overview charts;
- products that pass the hard gate remain visible in Product Explorer and
  eligible for Market Overview calculations, even when warning fields flag
  energy-macro mismatch or within-brand nutrition plausibility concerns;
- Product Map chart ranges filter what is drawn for readability only; they do
  not redefine aggregate eligibility;
- `include_in_aggregates` and `include_in_charts` remain in the schema for
  compatibility and audit history, while the current source of truth is
  `include_in_product_table` plus selected-axis non-null values and chart-range
  display filters.

The September 2026 nutrition-governance rule does not use a separate Market
Overview calculation exclusion rate beyond the Product Explorer hard gate.

See `docs/01_PRODUCT_DATA_GOVERNANCE/03_NUTRITION_QUALITY_GOVERNANCE.md` for the detailed rules.

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

As checked on 2026-10-16, the local working database contains **23,403**
`product_analysis` rows with `claim_source = 'vision'`, including confirmed
no-claim observations. The original country samples were supplemented with
targeted private-label coverage. The combined coverage is not a representative
market sample; original backbone weights do not apply to all these records.
The original 17,127-observation denominator is retained only as historical
release information. This count does not verify the live deployed app.

These releases are samples from the image-eligible OFF universe. They are not
retail-sales samples, market-share estimates, or a census of all packaged
products.

The latest approved UK/Ireland prompt permits explicit product-name/brand
claim evidence and adds deterministic text rescues after completed OCR/LLM
extraction. It uses product-name, brand and OCR
text: "free from" branding counts as a shopper-facing proposition, and origin
wording such as "British Milk" can count as provenance positioning. Flag-plus-
wording pack examples motivated the review, but the implemented rescue detects
text, not flag images. Explicit fat-reduction wording is distinguished from a
skimmed descriptor alone. These rules are market-specific and broader than
the original OCR-only claim-evidence restriction; see section 6.4 of the
extraction guide for exact behavior.

Two prevalence views must remain distinct:

- **sample proportion** — the observed share within the full sampled release,
  including purposive/enriched components;
- **backbone design-weighted estimate** — an approximate estimate based on the
  probability-oriented backbone of the image-eligible OFF sample.

See `docs/02_PACK_IMAGE_ANALYSIS/01_FRONT_PACK_CLAIM_EXTRACTION.md` for sampling design, prompt history, validation,
release details, and OCR/LLM limitations.

## Metric definitions

### Positioning signals / claim taxonomy

**Status:** Implemented; Streamlit displays vision-based positioning signals.

**Measures:** Explicit front-of-pack positioning territories detected from valid
OCR/LLM observations, including the approved UK text rescues, such as protein,
fibre, vitamins/fortification, no added
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
`docs/02_PACK_IMAGE_ANALYSIS/02_CLAIM_TAXONOMY_LABELS.md`.

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

See `docs/03_PROJECT_REFERENCE/01_ADR.md` for the architectural rationale behind the reporting layers.

## Private-label analysis

These standalone business analyses and supporting evidence live in
[`presentations/private_label_analysis/`](../../presentations/private_label_analysis/README.md).
They are independent of the Streamlit application; the app does not consume
the presentations or their evidence files.

The private-label analyses cover Aldi and Lidl across the project regions,
alongside top mainstream retailers for France (6), UK (5), US (5). They examine
three complementary dimensions: **portfolio architecture, product composition,
and on-pack claims**.

### Portfolio architecture

Architecture analysis used retailer-level product CSV exports containing
product names, brand/company mappings, nutrition, ingredients, pack sizes,
image URLs, and available positioning fields. These exports are retained
locally as the analysis inputs.

The analysis was conducted interactively using GPT-5.5 through chat. It examined
how brands, subranges, categories, price/quality tiers, and consumer needs
organize each retailer's observed portfolio. External retailer websites and
packshots supplemented the Open Food Facts records when checking current
ranges and specialist propositions.

Open Food Facts inputs were supplemented with retailer-published information
and newer product examples, including product descriptions, nutrition
information and packshots. Consequently, some presentation examples may not
appear in the retained OFF-derived CSV exports. Supplementary examples support
qualitative architecture analysis and illustration; they are not automatically
included in the CSV-based composition benchmarks or claims denominators. The
Harvest Morn Cookie Dough Bar on the Aldi slide is an example supplied from the
Aldi UK website, as confirmed by Julia Lenc. Its original website URL and access
date have not been recovered in this cleanup.

Julia Lenc, the repo owner, reviewed and aligned the resulting interpretations
before publication. The architecture was also reviewed by retail professionals.
Architecture conclusions are qualitative, analyst-reviewed interpretations;
they are not deterministic classifications generated by the production
pipeline. Different prompts or model runs may produce different groupings or
wording.

The retained onboarding documents record the analytical framework at particular
stages. They do not capture every subsequent correction or the complete chat
history. Exact prompts were not retained, so the original analysis cannot be
reproduced verbatim. Any prompt template reconstructed from these documents
must be identified as a reconstruction.

### Product composition

Composition comparisons use retailer-category nutrition medians and the
corresponding regional-category medians, recorded in
`nutrition_values_vs_market_median_all_retailers.csv`.

The retained CSV is the presentation evidence. The optional
`pipeline/maintenance/expand_private_label_macro_benchmarks.py` refresh preserves
its `total region` baseline rows and recalculates retailer-category rows from
the selected local database; it does not rebuild that regional baseline.
Retailer rows use the latest `ingested_at`, resolved company, region/category,
and `COALESCE(include_in_product_table, 1) = 1`. Nutrient medians exclude missing
values independently and retain declared zeros. Fresh outputs require a new path
outside the retained evidence tree.

“Market median” refers to the project's eligible observed Open Food Facts
records for that region and category. It is not a sales-weighted or
representative estimate of the entire retail market.

Category medians are sensitive to assortment composition. For example, a higher
dairy protein median may reflect a larger share of cheese rather than different
formulation within comparable products. These comparisons describe observed
composition and do not establish nutritional superiority or reformulation.

### On-pack claims

Claims analysis uses the available OCR/LLM pack observations and distinguishes
two measures:

- **Claim incidence:** packs with at least one detected positioning claim
  divided by all valid analyzed packs, including confirmed no-claim observations.
- **Territory share:** claim-bearing packs carrying a given territory divided
  by all claim-bearing analyzed packs.

Products not analyzed are excluded from both denominators. Invalid or unreadable
observations are not treated as confirmed no-claim observations. A pack may carry
multiple territories, so territory shares can sum to more than 100%.

The denominator-check and summary CSVs document the counts and calculations
supporting the analyses. Some check files include both denominator views for
comparison; the denominator stated for each published measure determines which
column applies.

These percentages describe the analyzed samples. They do not estimate claim
prevalence across the entire retailer assortment or market.

#### Aldi/Lidl reviewed claims evidence

The Aldi/Lidl evidence rebuilt on 2026-10-15 uses frozen product exports and
explicit claim-code groupings. This is a reconstruction of the analysis, not
the original chat calculation code. The full 13-territory mapping is recorded
in `presentations/private_label_analysis/aldi_lidl/README.md` and in each
row of `aldi_lidl_claims_denominator_check.csv`. In particular, Energy uses
`energy_claim`; Sugar / fat reduction uses `sugar_free_claim`, `reduced_sugar`
and `reduced_fat_claim`. The broader groupings used in later mainstream US
analysis must not silently replace these Aldi/Lidl definitions.

Territories may overlap. A product can count in both Plant-based / vegan and
Free-from; a territory counts a product once even when several codes support
it. Stacking counts distinct original positioning tags, not reviewed territories.

Julia Lenc reviewed four region-specific GTIN decisions: an empty derived
territory for Aldi UK chocolate orange brownies was overridden to vegan, and
three existing plant/vegan assignments for plant drinks were confirmed from
product context and dairy-free claims. These are exact reviewed interpretations,
not a general rule that dairy-free means vegan. Original claim codes and
historical source snapshots remain unchanged. The decisions are recorded in
`reviewed_territory_decisions.csv` and OBS-025 in
`docs/03_PROJECT_REFERENCE/05_OBSERVATIONS.md`.

The aggregate check separates code-only numerators from reviewed contextual
additions. Thus the reviewed Plant-based / vegan shares include three
product-specific interpretations that are not explicit vegan/plant-based
claim-code detections. Users examining detection alone should use the code-only
columns. The reviewed figures differ from four cells of the original PDF;
those differences are explicit in the check file. The PDF is retained unchanged
pending Julia's revision and must not be described as reconciled with the new
reviewed evidence.

The summary includes regional counts and `ALL_REGIONS_RECORDS` totals to
reconstruct the original pooled headline incidence. A GTIN observed in several
regions contributes to each region; pooled totals count region records, not
globally distinct GTINs. They are not used for retailer comparisons of territory
shares across different regional mixes.

### Evidence and interpretation

The UK denominator-check file preserves both the requested claim-bearing base
and the all-analyzed base, with a slide comparison column. Those views are not
interchangeable: the retained UK slide percentages are checked against the
all-analyzed denominator: 64 of 65 recorded cells match after rounding.
The remaining Asda Sugar / fat reduction cell is 12% in the slide comparison,
versus 29/256 = 11.328125% (11% rounded) in the retained evidence. This difference
remains unresolved. A future presentation revision must explicitly label
the chosen denominator rather than silently substitute the requested view.
The final retained CSV evidence takes precedence over incomplete onboarding
instructions; no PDF percentages were changed during documentation alignment.


Published PDFs contain the reviewed conclusions. Supporting aggregate CSVs
document composition benchmarks and claim calculations, while product-level
input exports are retained locally.

Historical onboarding instructions may differ from the final method because
the analysis was refined during review. The methodology and evidence
accompanying each published analysis should reflect the final calculations and
reviewed decisions.

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

See `docs/03_PROJECT_REFERENCE/03_LIMITATIONS.md` for the complete limitation catalogue.

## Tracking

Timestamped local files and their manifests are the tracking evidence for OFF
product waves. The wave label, OFF capture or proxy cutoff date, actual retrieval
date, and date of a preserved database copy are distinct dates:

- **Aug 29 capture — October 16 preserved database:**
  `G:\My Drive\Food Beverage Positioning Radar\wave_archives\baseline_20261016T180817_168296Z\`
  contains the checksum-verified `baseline.db`, `manifest.json`, `REPORT.md`
  and `capture_script.py`. It was moved from the local
  `data/06_brand_governance_outputs/baseline_captures/` folder. August 29, 2026 is the
  owner-confirmed date of the original OFF product capture. The original raw
  August export is no longer available in this project. The October 16 copy
  preserves the later working database, including subsequent OCR/LLM enrichment
  and reviewed corrections; it does not recover every original August field
  value or claim result.
- **Sep 29 proxy — October 17 raw retrieval:**
  `data/02_raw_off_downloads/incremental_snapshots/wave2_proxy_20260929_retrieved_20261017T153127Z/`
  contains the untouched `source.csv.gz` OFF bulk export and `manifest.json`
  recording its actual October 17, 2026 retrieval time and checksum. The
  ingestion-only scan and cutoff decisions are preserved separately in
  `data/06_brand_governance_outputs/incremental_ingestion_trials/live_proxy_stage_20261017T153127Z_v3/`.

The September proxy was created by scanning the complete October 17 OFF export
on a separate database copy and staging records against an **inclusive September
29 cutoff in Europe/Berlin**. New records are eligible only if their OFF creation
time precedes 2026-09-29T22:00:00Z, the exclusive UTC boundary. Previously
retained products can carry October source revisions. The proxy therefore
represents a September-eligible population using October-retrieved values; it is
not a reconstruction of the values as they stood on September 29. Governed
processing subsequently admitted 148,366 staged observations on that copy. The
separate completed release is retained at
`data/06_brand_governance_outputs/incremental_ingestion_trials/release_real_proxy_20261018_v1/`;
its public app artifact has a September 29 reporting date and contains 360,118
display-eligible products. The October 17 retrieval date remains explicit.

The August archive is outside the Git repository on Google Drive. The September
raw export, manifests, database copies, staging reports and release audit are
Git-ignored under `data/` and are not included in Git commits. The compressed
public app database is tracked separately under
`database/positioning_radar_public_mvp.db.gz`.
Future waves should retain separate timestamped source and processing evidence
so the reporting cutoff is never mistaken for the retrieval or copy date.
