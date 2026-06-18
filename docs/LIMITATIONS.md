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

**Image availability varies.** Not all products in OFF have a usable
front-of-pack image. Products without an image URL, or with a placeholder
URL (containing `/invalid/`), are excluded from pack-image claim extraction.
This means image-based claim analysis is systematically absent for some
brands and categories, regardless of the tiered sampling strategy.

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

## Methodology limitations

**Language coverage.** Ingredient-based analysis (composition marker score,
ingredient-based claim signals, intersection pattern flags) is limited to
products where the ingredient text is detected as English, French, or
bilingual (EN/FR). Products in other languages retain full nutrition data
but are excluded from ingredient-marker analysis to avoid silent false
negatives from an English/French-only dictionary. This affects approximately
16% of products in the current dataset.

**Image-based claim coverage.** Pack-image claim extraction covers
approximately 4,700 products — a tiered sample prioritising brands and
categories most likely to carry front-of-pack positioning claims. Products
outside this sample have ingredient-text and product-name signals only.
Claim taxonomy and claim-benchmark intersections should not be interpreted
as comprehensive for any brand or category unless that brand/category is
well-represented in the vision-analyzed subset.

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

**Positioning-to-composition gap is a composite, not a pure gap measure.**
The full score combines an ingredient-marker component (which applies
regardless of whether any pack claim is present) with a claim-weight
component and a context component (both of which require claims to be
present). A product with no detected claims can still receive a non-zero
score from the ingredient-marker component alone. See `docs/METHODOLOGY.md`
for the full breakdown.

## Extraction and detection limitations

**Sports nutrition and performance products.** Products designed for
endurance or performance use may show nutrition benchmark flags, such as
high sugar or high energy, that reflect intended product use rather than
an unexpected product profile. The pipeline does not currently detect
distribution channel or intended use context, so sports nutrition products
are treated identically to general packaged foods.

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

**Ingredient-text false positives.** Mandatory ingredient enrichment (e.g.
"(niacin, riboflavin, folic acid)" on enriched flour, standard in US
products) can trigger fortification or functional claim signals from
ingredient text alone. A parenthetical-stripping step is applied before
ingredient-based claim detection to reduce this, but edge cases may remain.

**"Nature" as a brand element.** In French, Belgian, and Swiss markets, the
word "nature" used as a flavour descriptor (e.g. "yaourt nature" = plain
yogurt) may be detected as a naturalness/clean-label signal by
ingredient-text analysis. This is a known false-positive pattern for plain
dairy products in these markets.
