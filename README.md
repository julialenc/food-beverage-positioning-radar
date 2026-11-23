# Food & Beverage Positioning Radar

Food & Beverage Positioning Radar is an **open-data research and
market-intelligence tool** for FMCG and retail research. It helps explore how
packaged foods and beverages position themselves through portfolio architecture,
nutrition, ingredients, processing and on-pack communication, using Open Food
Facts data, governed analytical layers and supplementary retailer research.

The **Streamlit application is the primary interactive interface and is currently
in beta**. Private Labels and Segmentation are separate research workstreams
within the Radar, with their own presentations, evidence and publication status.

[![Data License: ODbL](https://img.shields.io/badge/Data%20License-ODbL-blue)](https://opendatacommons.org/licenses/odbl/)
[![Code License: Apache 2.0](https://img.shields.io/badge/Code%20License-Apache%202.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org/)
[![Data: Open Food Facts](https://img.shields.io/badge/Data-Open%20Food%20Facts-orange)](https://world.openfoodfacts.org/)

## Explore the Radar

**[Open the Streamlit application](https://food-beverage-positioning-radar.streamlit.app/)**

- **Geographies:** France, UK & Ireland, US & Canada.
- **Categories:** snacks, cereals, dairy and beverages.
- **Market Overview:** compare observed category patterns, brands and companies;
  explore product-level nutrition maps and beverage view filters.
- **Product Explorer:** search and filter individual products by market,
  category, brand/company, nutrition status, NOVA, Nutri-Score and detected
  positioning signals, then inspect their evidence.

The app's Methodology and About pages explain interpretation and source limits.
The public beta can be slower on cold starts or broad filter changes. Product
counts describe observed OFF records, not sales, market share or distribution.

## Private Labels

Four published standalone analyses examine retailer private-label positioning.
They are independent of the Streamlit interface and cover:

- **Architecture:** how brands and ranges organize value, quality, premium and
  specialist propositions within retailer portfolios.
- **Composition:** category-level nutrition medians against the observed
  regional-category market median; assortment mix and small samples matter.
- **Claims:** detected-claim incidence and positioning territories, with the
  analyzed-pack or claim-bearing denominator stated in the evidence.

| Analysis | Presentation |
|---|---|
| Aldi and Lidl — France, UK and US | [Read the Aldi and Lidl analysis (PDF)](presentations/private_label_analysis/aldi_lidl/aldi_lidl_architecture.pdf) |
| Top 6 retailers in France | [Read the France analysis (PDF)](<presentations/private_label_analysis/mainstream_france_retailers/private_labels_france_top 5_retailers.pdf>) |
| Top 5 retailers in UK | [Read the UK analysis (PDF)](presentations/private_label_analysis/mainstream_uk_ie_retailers/private_labels_uk_top_5_retailers.pdf) |
| Top 5 retailers in US | [Read the US analysis (PDF)](<presentations/private_label_analysis/mainstream_us_canada_retailers/private_labels_us_top 5_retailers.pdf>) |

Portfolio architecture is qualitative research developed with GPT-5.5 through
chat, reviewed and aligned by Julia Lenc and reviewed by retail professionals.
Retailer websites and packshots supplemented OFF inputs. Exact architecture
prompts were not retained. Aggregate CSVs support composition and claims
calculations; product-level input exports remain local.

**Evidence qualifications:** the original Aldi/Lidl PDF awaits revision and does
not reproduce every reviewed evidence value; an Asda discrepancy in the UK PDF
remains unresolved. The underlying regional groupings are France, UK/Ireland
and US/Canada. The France PDF retains its historical "top 5" filename despite
its six-retailer scope. Claim denominators and extraction coverage differ across
analyses and do not establish market-level claim prevalence.

[Private-label evidence and PDF differences](presentations/private_label_analysis/README.md) ·
[Private-label methodology](docs/03_PROJECT_REFERENCE/02_METHODOLOGY.md#private-label-analysis)

## Segmentation — IN PROGRESS

Segmentation is an ongoing research workstream examining three separate layers:

1. **Commercial identity:** what a product is.
2. **Nutritional formulation:** how it is formulated.
3. **Communicated positioning:** what its packaging communicates.

**[Explore the operational segmentation research website](https://segmentation-food-beverage-radar.lovable.app/)**

This is a **separate research presentation**, independent of the Streamlit
application. It presents selected research findings; it is not an integrated
Streamlit feature.

The first Wave 2 analytical package was **published as
[v1.0.0](https://github.com/julialenc/food-beverage-positioning-radar/releases/tag/v1.0.0)
on 22 November 2026** and remains frozen. Its OFF snapshot was retrieved on
17 October 2026 with a 29 September 2026 reporting cutoff. The released package
and operational website are completed deliverables within the ongoing workstream.

Reproduction starts from the released governed data and locked observations.
The release's declared-input replay and public download verification passed;
a fresh dependency installation was not certified. The full historical OCR/LLM
archive is outside v1.0.0's published scope.

[Segmentation methodology](presentations/segmentation/SEGMENTATION.md) ·
[Accepted findings and research audit](presentations/segmentation/first_run/03_lenses/AUDIT_v1.md) ·
[v1.0.0 replay instructions](presentations/segmentation/audit_replay/release/README.md) ·
[Release scope](presentations/segmentation/audit_replay/release/SCOPE.md) ·
[Validation evidence](presentations/segmentation/audit_replay/release/CHECK.md)

## Data, methodology and limitations

Open Food Facts is crowdsourced: records can be incomplete, duplicated,
outdated or inconsistent, and coverage is uneven across markets and brands.
Country tags record where products were observed, not guaranteed distribution.
The Radar does not assess legal compliance, rank healthfulness, recommend
purchases or estimate sales, demand, market share or shelf presence.

Shared principles:

- Preserve source provenance where available and keep derived interpretations
  and inclusion flags separate. Missing values are distinct from declared zeros;
  uncertain or unassessed claims are distinct from documented non-detection.
- Exact reviewed GTIN corrections take precedence over broad rules. Company
  routing is directional navigation metadata, not a legal ownership guarantee;
  ambiguous products can remain unmapped.
- Product Explorer can retain imperfect but useful records. Market Overview
  calculations use records passing Product Explorer's hard validity gates;
  chart-range controls affect readability, not data-quality judgments.
- OCR/LLM communication evidence covers selected analyzed images. Targeted
  retailer enrichment and differing extraction rules limit comparability.
  Beverage view segmentation is rule-based, not a complete commercial taxonomy.

Publication and reproduction coverage differ by workstream. Consult its evidence
guide or release scope before reproducing results; fresh exports must not
replace frozen historical inputs.

[Shared methodology](docs/03_PROJECT_REFERENCE/02_METHODOLOGY.md) ·
[Detailed limitations](docs/03_PROJECT_REFERENCE/03_LIMITATIONS.md) ·
[Data dictionary](docs/03_PROJECT_REFERENCE/04_DATA_DICTIONARY.md)

## Run locally / technical navigation

Use Python 3.12 for the main Streamlit application. From a Windows terminal:

```powershell
git clone https://github.com/julialenc/food-beverage-positioning-radar.git
cd food-beverage-positioning-radar
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

The app can read a prepared local database or the compressed public MVP database
artifact included for deployment. Azure Vision and Azure OpenAI credentials are
needed only when deliberately running the vision pipeline, not to explore the
prepared app dataset. Segmentation replay has its own dependency and input
instructions, linked above.

The app pipeline ingests OFF data, applies category/brand/nutrition governance,
optionally enriches selected images through OCR/LLM extraction, and builds
SQLite reporting tables and deployment artifacts. Standalone research has
separate evidence and release contracts.

| Area | Navigation |
|---|---|
| Application | [Entry point](app.py), [pages](pages/), [shared UI and database helpers](shared/) |
| Pipeline | [Stages, supporting tools and archives](pipeline/README_NAVIGATING_PIPELINE.md), [retention audit](pipeline/PIPELINE_RETENTION_AUDIT.md) |
| Data | [Data navigation](data/README_NAVIGATING_DATA.md), [reference inputs and provenance](data/01_reference_inputs/README.md) |
| Governance | [Category scope](docs/01_PRODUCT_DATA_GOVERNANCE/01_CATEGORY_SCOPE_AND_CLEANUP.md), [brand/company mapping](docs/01_PRODUCT_DATA_GOVERNANCE/02_BRAND_COMPANY_MAPPING.md), [nutrition quality](docs/01_PRODUCT_DATA_GOVERNANCE/03_NUTRITION_QUALITY_GOVERNANCE.md) |
| Pack evidence | [Extraction methodology](docs/02_PACK_IMAGE_ANALYSIS/01_FRONT_PACK_CLAIM_EXTRACTION.md), [claim labels](docs/02_PACK_IMAGE_ANALYSIS/02_CLAIM_TAXONOMY_LABELS.md) |
| Research | [Presentations index](presentations/README.md), [segmentation first-run guide](presentations/segmentation/first_run/README.md) |

## Licenses and attribution

Product data comes from [Open Food Facts](https://world.openfoodfacts.org/) and
is licensed under the **[Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/)**.

Repository code and original project documentation are licensed under the
**Apache License, Version 2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
Retain these files when reusing or redistributing the project and credit:

```text
Food & Beverage Positioning Radar by Julia Lenc
Data from Open Food Facts - https://world.openfoodfacts.org
```

See [CITATION.md](CITATION.md) for project and presentation citation guidance.
