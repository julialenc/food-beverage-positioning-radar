# Food & Beverage Positioning Radar

**A beta open-data market-intelligence board for exploring how packaged foods
and beverages position themselves through nutrition, ingredients, processing,
brand / company mapping, and front-of-pack communication.**

[![Data License: ODbL](https://img.shields.io/badge/Data%20License-ODbL-blue)](https://opendatacommons.org/licenses/odbl/)
[![Code License: Apache 2.0](https://img.shields.io/badge/Code%20License-Apache%202.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org/)
[![Data: Open Food Facts](https://img.shields.io/badge/Data-Open%20Food%20Facts-orange)](https://world.openfoodfacts.org/)

> **Beta MVP launch build.** This project is built on Open Food Facts records.
> It includes governed cleaning, nutrition-quality, category, brand, company,
> and front-pack evidence layers. Open Food Facts remains crowdsourced, so some
> product records can still be incomplete, inconsistent, or unresolved.

## What This Is

Food & Beverage Positioning Radar is a neutral analytical board for exploring
packaged food and beverage products. It helps users inspect what products
contain, how they are classified, which consumer-facing brands and company
routes they map to, and what they communicate on pack where image evidence is
available.

The central question is:

**How do packaged foods and beverages position themselves through claims,
ingredients, nutrition, processing, and design?**

The tool does not judge products, assess legal compliance, recommend purchases,
rank brands, or estimate market share. It organizes open product data so users
can inspect patterns and make their own interpretation.

## Current Scope

The beta MVP focuses on observed Open Food Facts records in:

- France
- UK & Ireland
- US & Canada

Current Streamlit categories:

- Snacks
- Cereals
- Dairy
- Beverages

Counts are observed Open Food Facts records after project cleaning rules. They
are not sales volumes, launch counts, household penetration, retail
distribution, shelf share, or consumer-demand estimates.

## What The App Shows

**Market Overview** shows high-level patterns for a selected market-category
base. It supports category reports, brand comparison, company/brand drill-down,
product-level nutrition maps, and a beverage view segment filter that separates
ready-to-drink beverages from beverage preparations / alcohol and unknown
beverage records.

**Product Explorer** lets users search individual products, filter by category,
market, brand, company, nutrition status, NOVA, Nutri-Score, and detected
positioning signals, then inspect product-level evidence.

**Methodology**, **Limitations**, and **About** explain how to read the data,
what the app does not claim, and where Open Food Facts source limitations
matter.

## Governance Status

The major launch governance layers are documented for the current MVP scope;
reviewed mapping and category scopes are locked where stated:

- category cleanup is locked for France, UK/Ireland, and US/Canada snacks and
  cereals, with additional GTIN-level corrections from the September 2026
  mapping/orphan audits;
- retailer/private-label mapping is complete and locked;
- the nine priority manufacturer portfolios are locked after product-level
  audit and regression validation;
- regional-category orphan-brand review is complete across France, UK/Ireland,
  and US/Canada;
- nutrition-quality and outlier governance is implemented for Product Explorer,
  Market Overview calculations, and chart inclusion;
- beverage segmentation is an MVP chart-readability layer, not a final beverage
  taxonomy.

The regional orphan threshold was:

```text
normalized brand assigned to Other / not mapped to a company
AND at least 100 products in one specific region x category bucket
```

France and US/Canada had qualifying candidates and were audited, implemented,
and validated. UK/Ireland had no qualifying orphan candidates at that threshold.
The final residual review confirms that no normalized brand with at least 100
products in a single launch region-category remains under
`Other / not mapped to a company` without reviewed resolution.

Individual products can still remain under `Other / not mapped to a company`
when ownership is genuinely ambiguous. The project deliberately prefers a false
negative to a false-positive owner assignment.

## Methodology In Brief

The app separates two evidence layers:

**Structured product evidence** comes from Open Food Facts records plus governed
project-derived metadata. It includes composition data such as nutrition values,
ingredients, Nutri-Score, and NOVA group, alongside category scope, market tags,
brand normalization, and company / owner routing.

**Pack-communication evidence** comes from OCR and LLM analysis of selected
front-pack images. It is shown at product level where available and should not
be read as representative market-level claim prevalence.

Core data principles:

- raw source values are preserved where the pipeline has provenance fields;
- missing values are not treated as zero;
- category, brand, company, and nutrition fields are governed derived layers;
- Product Explorer can show imperfect but useful records;
- Market Overview calculations and charts use stricter inclusion rules;
- exact reviewed GTIN overrides outrank broad brand/company/category rules.

## Known Beta Limitations

- Open Food Facts is crowdsourced; records can be incomplete, duplicated,
  outdated, or inconsistent.
- Product counts are observed records, not market size.
- Country tags indicate where a product was observed in Open Food Facts, not
  guaranteed distribution.
- Brand/company ownership can be market-specific, product-form-specific,
  license-specific, or recently changed.
- Company filters are directional navigation aids, not legal ownership
  guarantees.
- Some products remain under `Other / not mapped to a company` after review.
- Beverage segmentation is rule-based and not a complete commercial beverage
  taxonomy.
- Front-pack claim extraction covers selected image-analyzed products only.
- Cold starts and broad filter changes can be slower on the public beta
  deployment.

## How To Run

```bash
git clone https://github.com/julialenc/food-beverage-positioning-radar.git
cd food-beverage-positioning-radar
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Azure Vision and Azure OpenAI credentials are required only for the vision
pipeline. The Streamlit app can run from the prepared local database or from the
compressed public MVP database artifact included for deployment.

## Repository Layout

```text
app.py                  Streamlit entry point
pages/                  Streamlit pages
shared/                 Shared UI, labels, beverage segments, and DB helpers
pipeline/               Production and maintenance pipeline scripts
data/reference/         Production reference mappings and lookup files
database/               Schema reference and compressed public MVP DB artifact
docs/                   Methodology, limitations, governance, and ADRs
```

Generated local workspaces are kept as empty committed folders with `.gitkeep`
placeholders:

```text
data/raw/                         Cached OFF/API inputs when regenerated
data/sample/                      Local pipeline outputs and release samples
data/brand_mapping_review/        Local brand/company review exports
data/nutrition_outlier_review/    Local nutrition-quality review exports
```

Generated CSVs, raw Open Food Facts downloads, local audit exports, and the full
local SQLite build database are not part of the public data surface. They can be
regenerated when needed and should not be committed unless a file is explicitly
promoted to production reference status.

## Production Reference Files

The production reference layer is under `data/reference/`:

- `company_brand_mapping.csv` - reusable brand-to-company routing rules;
- `brand_alias_mapping.csv` - reviewed brand-string aliases;
- `private_label_brand_mapping.csv` - reviewed retailer/private-label brand
  architecture;
- `reviewed_product_mapping_overrides.csv` - exact GTIN-level reviewed brand,
  company, category, and `OUT_OF_SCOPE` overrides;
- `top_company_brand_portfolio_matrix.csv` - priority manufacturer portfolio and
  discovery reference;
- `README.md` - reference-file descriptions and provenance notes.

These files are project-maintained derived inputs, not raw Open Food Facts data.
They preserve brand, company, and product-specific governance decisions used by
`pipeline/clean.py`, `pipeline/load.py`, and the Streamlit app.

## Pipeline Overview

The standard local build path is:

```text
1. pipeline/bootstrap.py or pipeline/ingest.py
2. pipeline/clean.py
3. pipeline/nutrition_outliers/build_quality_flags.py
4. pipeline/analyze.py
5. pipeline/load.py
6. pipeline/smart_sample.py                         [manual when refreshing vision sample]
7. pipeline/vision_extract.py                       [paid/manual vision stage]
8. pipeline/merge_scores.py
9. pipeline/tag_claims.py
10. pipeline/db_summary.py
11. pipeline/compute_region_benchmarks.py
12. pipeline/compute_profile_intersections.py
13. pipeline/compute_axis_ranges.py
14. pipeline/build_deployment_database.py
```

Some scripts are maintenance or review utilities rather than automatic pipeline
steps. Use them deliberately when refreshing mappings, category rules,
nutrition governance, or the vision sample. `smart_sample.py` and
`vision_extract.py` are shown in the build path for completeness but are run
only when vision results are intentionally refreshed. The vision/OCR stage calls
paid Azure services and should not be run as part of an automatic loop.

## Documentation

- `docs/METHODOLOGY.md` - metric definitions, evidence layers, and
  interpretation rules
- `docs/LIMITATIONS.md` - source-data, coverage, and methodology limitations
- `docs/CATEGORY_CLEANUP.md` - category cleanup and routing governance
- `docs/BRAND_COMPANY_MAPPING.md` - brand normalization and company mapping
  governance
- `docs/NUTRITION_OUTLIER_GOVERNANCE.md` - nutrition-quality and outlier
  treatment rules
- `docs/COLUMN_DESCRIPTIONS.md` - database/output field definitions
- `docs/CLAIM_EXTRACTION.md` - OCR/LLM front-pack claim extraction methodology
- `docs/ADR.md` - architecture decision records
- `data/reference/README.md` - reference mapping files and provenance notes

## Data Source, License, And Attribution

Product data is sourced from [Open Food Facts](https://world.openfoodfacts.org/),
licensed under the **Open Database License (ODbL)**.

Repository code and original project documentation are licensed under the
**Apache License, Version 2.0**. See `LICENSE` and `NOTICE`.

If you reuse or redistribute this project, retain the Apache 2.0 license and
notice files and credit:

```text
Food & Beverage Positioning Radar by Julia Lenc
```

Data attribution:

```text
Data from Open Food Facts - https://world.openfoodfacts.org
```

See `CITATION.md` for citation guidance.

---

*Data from Open Food Facts - openfoodfacts.org - ODbL license*  
*Project code and documentation licensed under Apache 2.0*
