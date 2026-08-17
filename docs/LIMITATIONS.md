# Data source, license, and limitations

This document catalogs the known limitations affecting how outputs from
Food & Beverage Positioning Radar should be interpreted. For metric-specific
scope statements ("what it measures / what it does not measure"), see
`docs/METHODOLOGY.md`.

## Data source: Open Food Facts

Product data is sourced from Open Food Facts (OFF), an open, crowdsourced
database. The following limitations are inherent to this source and apply
regardless of how the pipeline processes the data.

**Coverage is uneven.** OFF contains millions of product records, but
coverage varies by country, category, brand, image availability, and
contributor activity. Well-documented markets (France, Germany, UK, US)
are better represented than others. Product presence in this dataset does
not mean a product is widely distributed or commercially relevant in any
specific market.

**No sales data.** Product counts are not market share. A brand with fifty
products in the dataset may have negligible commercial volume; a brand with
three products may be a market leader. Observed products and claims reflect
what appears in the Open Food Facts product universe, not how widely those
products are distributed or how well they perform commercially.

**Crowdsourced quality.** Product names, images, nutrition values,
ingredients, and categories are entered by contributors and can be
incomplete, outdated, duplicated, or inconsistent. Nutrition values in
particular are sourced from pack declarations, not independent laboratory
analysis. The `completeness_score` field (see `docs/COLUMN_DESCRIPTIONS.md`)
provides a per-product indicator of how many key fields are populated, but
it does not guarantee the accuracy of the values that are present.

**Missing is not zero.** A missing nutrition value, a failed observation,
an empty string, and a declared zero are different states. The pipeline
preserves these distinctions because collapsing them would create false
certainty. In particular, `pack_claims_found = NULL` means no valid pack
observation exists, while `pack_claims_found = ""` means a valid front pack
was assessed and no taxonomy claim was found.

**Image availability varies.** Not all products in OFF have a usable
front-of-pack image. Products without an image URL, or with a placeholder
URL (containing `/invalid/`), are excluded from pack-image claim extraction.
This means image-based claim analysis is systematically absent for some
brands and categories, regardless of the tiered sampling strategy.

**Category taxonomy is noisy.** OFF categories are contributor-assigned and
inherit broad parent tags. Current cereals release figures are contaminated by
pasta, bread, flour, rusks, breadsticks, puff pastry, and related grain
products. Snacks contamination by noodles and related products is also under
review. These are source taxonomy and filtering limitations, not
claim-extraction failures.

**Brand strings are fragmented.** The same brand may appear under multiple
spellings, capitalizations, or with and without parent-company prefixes.
Normalization (see `docs/BRAND_COMPANY_MAPPING.md`) reduces but does not
eliminate this fragmentation. Brand-level aggregations should be treated as
approximate where the underlying brand string is inconsistently populated
in the source data.

## License and attribution

Open Food Facts data is licensed under the Open Database License (ODbL).
Use of this data requires attribution to Open Food Facts. Derivative
databases produced from OFF data may have share-alike obligations under
ODbL; review the license terms before redistributing any dataset derived
from this pipeline. Analysis outputs such as charts, summaries, and reports
may be treated differently from redistributed structured data, depending on
the use case.

Required attribution: **Open Food Facts** — [https://world.openfoodfacts.org](https://world.openfoodfacts.org)

This document is not legal advice; users planning to redistribute derived
datasets should review the ODbL terms for their specific use case.

## Methodology limitations

**Language coverage.** Ingredient-based analysis (composition marker score,
ingredient-based claim signals, intersection pattern flags) is limited to
products where the ingredient text is detected as English, French, or
bilingual (EN/FR). Products in other languages retain full nutrition data
but are excluded from ingredient-marker analysis to avoid silent false
negatives from an English/French-only dictionary. This affects approximately
16% of products in the current dataset.

**Image-based claim coverage.** The current US/UK and France analytical
releases contain 17,127 valid front-of-pack observations. These observations
come from sampled, image-eligible Open Food Facts products; they are not a
retail-sales sample, market-share estimate, or census of all packaged
products. Products outside the valid pack-observation population may rely on
ingredient/name-derived fallback signals. Claim taxonomy and claim-benchmark
intersections should not be interpreted as comprehensive for any brand or
category unless that brand/category is well represented in the
vision-analyzed subset. Check `release_run_id`, `pack_analysis_attempted`,
`claim_source`, and `pack_claims_found` (see
`docs/COLUMN_DESCRIPTIONS.md`) before treating any claim-taxonomy result as
pack-image-confirmed rather than fallback-derived.

**Nutrition benchmark thresholds.** The reference thresholds used for
nutrition benchmark flags (sugar, saturated fat, fat, salt) follow the UK
Food Standards Agency's front-of-pack labelling guidance. These thresholds
are applied uniformly to all products in the dataset as a single reference
scheme for cross-product comparison, regardless of the product's country of
origin or the labelling regulations that apply to it. They are not a
universal standard and do not represent legal requirements in any
jurisdiction.

**Liquid/solid classification.** Whether a product is treated as liquid or
solid (which affects which threshold set applies) is approximated using an
energy-density proxy: products below 100 kcal/100ml are treated as liquid.
This is an MVP approximation and may misclassify some categories (e.g.
semi-liquid foods, concentrated drinks). This should be reviewed if
nutrition benchmark flags become a central reporting layer.

**Legacy/internal composite fields are not user-facing metrics.**
`composition_marker_score` and `positioning_composition_gap` remain in parts
of the historical pipeline, but they are not displayed as proprietary scores
in the current Streamlit MVP. If used for internal diagnostics, they should be
interpreted with the caveats in `docs/METHODOLOGY.md`.

**Weekly summary tables describe an observed snapshot, not the market.**
`weekly_brand_positioning_summary` (see `docs/METHODOLOGY.md` for the
distinction between this table and the ingredient-stage-only
`weekly_brand_summary`) reflects the Open Food Facts product universe as
represented in the current database snapshot at the time it was computed.
It does not measure retail distribution, market share, sales velocity, or
consumer penetration — the same "no sales data" limitation above applies
to every aggregate derived from this table, including any brand- or
category-level trend shown in the Streamlit app or exported reporting tables.

**Serving-size and usage context.** Most nutrition comparisons in this
tool are made per 100g or 100ml to allow consistent cross-product
comparison. They do not account for typical serving size, consumption
frequency, preparation method, or usage occasion. A product intended to
be consumed in small portions may look different under a per-100g
comparison than under a serving-based view. This is especially relevant
for spreads, sauces, confectionery, powders, cereals, sports gels, and
concentrated drinks. Serving-size analysis may be added in a future
version if source-data completeness is sufficient.

## Extraction and detection limitations

**Model and prompt dependency.** Pack-claim extraction depends on the OCR
engine, LLM deployment, prompt version, and model behavior at the time of
the run. Results may change if the model, prompt, OCR service, or
extraction rules are updated. The pipeline records `vision_model`,
`prompt_version`, `ocr_status`, `llm_status`, and `pack_analysis_timestamp`
(see `docs/COLUMN_DESCRIPTIONS.md`) so extraction results can be audited
and compared across runs. See `docs/CLAIM_EXTRACTION.md` for prompt version
history, release counts, validation behavior, and known extraction issues.

**Sports nutrition and performance products.** Products designed for
endurance or performance use may show benchmark or composition signals,
such as sugar above reference thresholds or high energy density, that
reflect intended product use rather than an unexpected product profile.
The pipeline does not currently detect distribution channel, target user,
or intended use occasion, so sports nutrition products are treated
identically to general packaged foods.

**Promotional pack elements.** Claims such as "+10% free", "new size", or
"now with 20% more" can be misclassified as comparative positioning claims
during extraction. Prompt rules in the extraction step have been added to
reduce this, but residual misclassification may remain in products analyzed
before those rules were introduced.

**OCR quality and pack design.** Extraction quality depends on image
resolution, OCR legibility, and pack typography. Highly stylized, low-contrast,
or low-resolution pack images may result in missed or partial claim
extraction. This is a known limitation for certain brand design styles
(e.g. brands using decorative or handwritten typography) and for products
where the front-of-pack image captured by contributors does not show the
primary claim-bearing face of the pack.

**Panel classification residual error.** OCR flattens visual hierarchy, so a
valid front pack can resemble an ingredient, legal, or nutrition panel in text
form. French cheese and organic dairy packs are a known risk area because
front labels often include certification, origin, producer, and short
ingredient text. A second-pass panel-context review reduces this error for
French dairy, but residual false exclusions may remain, including possible
lower-rate errors in the English release.

**Unmapped claim text.** Some claim-like text can be captured in
`other_claims` or `detected_claim_phrases` without mapping into a boolean
taxonomy field. Rescuing only the captured subset would be non-random, so the
current approach is conservative and may slightly understate claim prevalence
for affected releases.

**Ingredient-text false positives.** Mandatory ingredient enrichment (e.g.
"(niacin, riboflavin, folic acid)" on enriched flour, standard in US
products) can trigger fortification or functional claim signals from
ingredient text alone. A parenthetical-stripping step is applied before
ingredient-based claim detection to reduce this, but edge cases may remain.

**"Nature" as a flavour descriptor.** In French, Belgian, and Swiss
markets, the word "nature" is often used as a flavour descriptor (e.g.
"yaourt nature" = plain yogurt). It can be mistaken for a naturalness or
clean-label signal in ingredient-text or product-name analysis. This is a
known false-positive pattern for plain dairy and bakery products in these
markets.
