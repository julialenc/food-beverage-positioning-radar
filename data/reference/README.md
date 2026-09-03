# Reference Data

This folder contains curated reference inputs, launch mapping tables, and
provenance files used by the Food & Beverage Positioning Radar pipeline.

The files here are not raw Open Food Facts data. They are project-maintained
lookups that support category routing, brand normalization, company / owner
navigation, and audited launch fixes.

Region grouping for the Market / region filter is defined one level up in
`data/country_region_mapping.csv`.

## Launch Reference Files

### `company_brand_mapping.csv`

Main company / owner routing table used by `pipeline/clean.py` and the
Streamlit app. After the September 2026 Top 9, retailer, France, and
US/Canada regional-category orphan cleanup, it contains 3,631 rows across 208
parent-company values.

This file supports directional company / owner filtering. It is not a legal
ownership audit. Market-scoped, licensed, recently changed, and manually
reviewed ownership cases are represented through metadata fields such as
`ownership_resolution_status`, `market_scope`, `region_codes_include`,
`region_codes_exclude`, `brand_mapping_source`, `review_note`, and
`needs_manual_review`.

Streamlit must not display `Manual review` as a visible company / owner value.
Rows that still require review should use a mapped company or
`Other / not mapped to a company` as the visible owner, with review status kept
in metadata.

Full governance notes are documented in `docs/BRAND_COMPANY_MAPPING.md`.

### `brand_alias_mapping.csv`

Observed brand-string variants mapped to canonical brand strings.

This file is part of the brand alias normalization layer. It should be read
together with the newer extraction and private-label logic in
`pipeline/clean.py`:

1. preserve raw OFF brand evidence;
2. extract a brand-level entity;
3. normalize spelling, punctuation, and approved aliases;
4. resolve company / owner separately.

Alias mapping must not collapse consumer-facing brand lines into parent
companies. For example, `KitKat` remains a brand entity and is routed to the
appropriate company later.

### `private_label_brand_mapping.csv`

Curated private-label mapping reference. After the September 2026 retailer
mapping exercise, this contains 1,388 reviewed rows covering the completed
retailer/private-label portfolios.

The purpose is brand-level/private-label-line normalization, not parent-company
assignment. For example, `Carrefour Bio`, `Carrefour Classic`,
`Carrefour Sensation`, `Reflets de France`, and `Simpl` are preserved as
brand-level entities before company routing.

Do not expand this file to other retailers without the same step-by-step review
process.

### `top_company_brand_portfolio_matrix.csv`

Top-company portfolio routing matrix used as an input for the August/September
2026 Top 9 company review. It currently contains 247 portfolio/discovery rows.

This file supports the curated routing layer for Nestlé, PepsiCo,
The Coca-Cola Company, Mondelēz International, Danone, Kraft Heinz,
The Hershey Company, Starbucks, and selected Unilever / demerged / spun-off
exceptions.

The matrix is an input to company mapping. It should not be used as a blanket
override without the conflict checks described in
`docs/BRAND_COMPANY_MAPPING.md`.

### `reviewed_product_mapping_overrides.csv`

Exact GTIN-level reviewed overrides for cases where product evidence is
stronger than contaminated Open Food Facts brand metadata or a broad portfolio
rule. These rows can correct derived display brand, resolved company / owner,
or project category for a specific product, including `OUT_OF_SCOPE`.
The optional `region` column supports market-specific reviewed outcomes for
the same GTIN; blank `region` means the override is unscoped.
After the September 2026 Top 9 audits and France/US-Canada regional-category
orphan cleanup, this file contains 12,577 active reviewed override rows.

The file must not be used to infer broad brand aliases. Raw Open Food Facts
fields remain unchanged.

### `brand_counts.csv` and `brand_coverage_report.csv`

Brand coverage diagnostics used during mapping review. These are helpful for
prioritizing cleanup but are not the app's final company / owner truth table.

## Generated Outputs Elsewhere

Most audit outputs are generated outside this folder and are treated as local
review artifacts rather than production reference inputs:

- `data/brand_mapping_review/` contains brand/entity/company review exports.
- `data/nutrition_outlier_review/` contains nutrition-quality and outlier
  review exports.
- `data/sample/` contains pipeline sample outputs when generated locally.
- `database/` contains the local SQLite database when built locally.

Large or one-off review files should generally stay local, be regenerated from
the relevant script when needed, and not be added to `data/reference/`.

## Reproducing From Scratch

Run the pipeline stages in the order documented in the main `README.md`.

The vision-extraction stage calls paid Azure services, so it should be run
deliberately rather than as part of an automatic loop. Reference files in this
folder are intended to make cleaning and company-routing decisions reproducible
when the raw Open Food Facts data is refreshed.
