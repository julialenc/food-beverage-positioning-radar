# Food & Beverage Positioning Radar

**A beta open-data market-intelligence board for exploring how packaged foods
and beverages position themselves through nutrition, ingredients, processing,
brand / company mapping, and front-of-pack communication.**

[![Data License: ODbL](https://img.shields.io/badge/Data%20License-ODbL-blue)](https://opendatacommons.org/licenses/odbl/)
[![Code License: Apache 2.0](https://img.shields.io/badge/Code%20License-Apache%202.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org/)
[![Data: Open Food Facts](https://img.shields.io/badge/Data-Open%20Food%20Facts-orange)](https://world.openfoodfacts.org/)

> **Beta MVP launch build.** This project is built on Open Food Facts records.
> It includes documented cleaning, nutrition-quality, brand-normalization, and
> company-mapping layers, but some records may remain incomplete, imperfect, or
> unresolved at source-data level.

## What This Is

Food & Beverage Positioning Radar is a neutral analytical board for exploring
packaged food and beverage products. It helps users inspect what products
contain, how they are classified, which brands and companies they map to, and
what they communicate on pack where image evidence is available.

The main question is:

**How do packaged foods and beverages position themselves through claims,
ingredients, nutrition, processing, and design?**

The tool does not judge products, assess legal compliance, recommend purchases,
rank brands, or estimate market share. It organizes open product data so users
can inspect patterns and make their own interpretation.

## Current MVP Scope

The August 2026 beta focuses on observed Open Food Facts records in:

- France
- UK & Ireland
- US & Canada

Current Streamlit categories:

- Snacks
- Cereals
- Dairy
- Beverages

Counts are observed Open Food Facts records after project cleaning rules. They
are not sales volumes, market shares, launch counts, shelf shares, retail
distribution, or consumer-demand estimates.

## What The App Shows

**Market Overview** shows high-level patterns for a selected market-category
base. It supports category reports, brand comparison, company/brand drill-down,
and product-level nutrition maps.

**Product Explorer** lets users search individual products, filter by category,
market, brand, company, nutrition status, NOVA, Nutri-Score, and detected
positioning signals, then inspect product-level evidence.

**Methodology** and **About** explain how to read the data, what the app does
not claim, and where Open Food Facts source limitations matter.

## Methodology In Brief

The app separates two evidence layers:

**Composition data** comes from structured Open Food Facts records. It includes
nutrition values, ingredients, Nutri-Score, NOVA group, category tags, market
tags, brand normalization, and company / owner mapping.

**Pack-communication evidence** comes from OCR and LLM analysis of selected
front-pack images. It is shown at product level where available and should not
be read as representative market-level claim prevalence.

Nutrition-quality governance preserves raw Open Food Facts values and adds
flags for analytical inclusion. Product Explorer can show imperfect but useful
records. Market Overview calculations and charts exclude records with
implemented hard data-quality flags, material energy/macronutrient
inconsistencies, or documented chart-distorting outlier rules where available.

Brand and company mapping are separated into layers: raw Open Food Facts brand
evidence, normalized consumer-facing brand, and company / owner mapping. Company
filters are directional navigation aids, not legal ownership guarantees.

## Known Beta Limitations

- Open Food Facts is crowdsourced; records can be incomplete or inconsistent.
- Missing values are not zero.
- Product counts are observed records, not market size.
- Brand/company ownership can be market-specific, license-specific, or recently changed.
- Some brand-to-company mappings are pragmatic launch-stage routing decisions and may be refined in future updates.
- Some unresolved brands remain under `Other / not mapped`.
- Beverage segmentation is MVP-ready but not a final beverage taxonomy.
- Front-pack claim extraction covers selected image-analyzed products only.
- Initial Streamlit page loads or broad filter changes may take up to around 90 seconds.

## Who This Is For

The primary audience is CPG professionals, insight managers, market analysts,
consultants, nutrition professionals, dietitians, and researchers who need a
transparent open-data tool for category and product-pattern exploration.

The technical audience includes AI engineers, ML engineers, and data scientists
interested in OCR/LLM extraction, open-data cleaning, product classification,
and reproducible analytical pipelines.

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
pipeline. The Streamlit app can run from the prepared local database.

## Main Repository Areas

```text
app.py                  Streamlit entry point
pages/                  Streamlit pages
shared/                 Shared UI and database helpers
pipeline/               Data ingestion, cleaning, analysis, and loading scripts
data/reference/         Curated reference mappings and lookup files
database/               Local SQLite database and schema reference
docs/                   Methodology, limitations, governance, and architecture docs
```

The exact repository hierarchy may evolve during cleanup, but these are the
main working areas of the project.

## Documentation

- `docs/METHODOLOGY.md` - metric definitions, evidence layers, and interpretation rules
- `docs/LIMITATIONS.md` - source-data, licensing, and methodology limitations
- `docs/CATEGORY_CLEANUP.md` - category cleanup and routing governance
- `docs/BRAND_COMPANY_MAPPING.md` - brand normalization and company mapping governance
- `docs/NUTRITION_OUTLIER_GOVERNANCE.md` - nutrition-quality and outlier-treatment rules
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
