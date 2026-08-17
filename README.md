# Food & Beverage Positioning Radar

**A neutral market intelligence tool for analyzing how packaged foods and
beverages position themselves through claims, ingredients, nutrition,
processing, and design.**

[![Data License: ODbL](https://img.shields.io/badge/Data%20License-ODbL-blue)](https://opendatacommons.org/licenses/odbl/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org/)
[![Data: Open Food Facts](https://img.shields.io/badge/Data-Open%20Food%20Facts-orange)](https://world.openfoodfacts.org/)

---

## What this is

Food & Beverage Positioning Radar maps how packaged food and beverage
products position themselves through claims, ingredients, nutrition,
processing, and design. It ingests product data from Open Food
Facts, extracts front-of-pack claims using OCR and LLM analysis, applies
ingredient and nutrition analysis, and computes benchmark and
claim-intersection metrics for exploration in a Streamlit analytical board.

**Main question:** How do packaged foods and beverages position themselves
through claims, ingredients, nutrition, processing, and design?

One analytical lens explores where front-of-pack positioning intersects
with composition indicators.

The tool does not judge products, assess legal compliance, recommend
purchases, or blame brands. It shows structured product data through
analytical lenses; interpretation remains with the user.

---

## Where this fits

Food & Beverage Positioning Radar sits between new product databases,
product-attribute intelligence, and trend-foresight tools. Commercial
platforms such as Mintel GNPD, Innova, NIQ Label Insight, SPINS, and
Euromonitor Via offer broader enterprise-grade product and market
intelligence. This project is a focused, transparent, open-data
implementation designed to explore packaged food positioning through
claims, ingredients, nutrition, processing, and pack communication. It is
especially relevant for smaller companies, startups, consultants, and
analysts who need a lightweight market-intelligence layer rather than a
full enterprise subscription or retail audit system.

---

## Who this is for

**Primary — CPG professionals, insight managers, market analysts,
consultants:** A market intelligence tool for identifying claim
territories, product segments, ingredient systems, and
positioning-to-composition patterns across packaged food and beverage
categories. Not a market share tool, legal assessment, consumer
recommendation tool, or product-verdict system.

**Secondary — nutritionists, dietitians, nutrition coaches:** An education
and category-literacy tool for understanding how packaged products are
positioned and what they contain. Useful for finding coaching examples and
product-pattern illustrations. Not a meal-planning app or consumer
recommendation system.

**Technical — AI engineers, ML engineers, data scientists:** An applied
LLM/OCR pipeline for extracting and classifying product-positioning
signals from real-world packaging. Supports model, prompt, cost, OCR
quality, and structured-output comparisons. The technical audience is
served through this repository, notebooks, and benchmark documentation —
not through the main Streamlit UX.

This tool is not designed for legal or regulatory assessment, journalism,
consumer advocacy, retail/ecommerce professionals, or general consumers.
See `docs/METHODOLOGY.md` for the full scope statement.

---

## Deliverables

| Deliverable | Role | Description |
|---|---|---|
| Streamlit app (`app.py`) | Main product | Search, filter, sort, and inspect products. Product and overview pages show pack image evidence, extracted claims, brand/category, nutrition, processing indicators, benchmark flags, and claim-composition intersections. |
| This repository | Technical and reproducibility layer | Code, methodology, column descriptions, prompt history, sampling design, QA notes, and benchmark/export tables. Serves the AI engineering audience without changing the main UX. |

---

## Key metrics

Every metric has a definition, a scope statement, and a non-scope
statement in `docs/METHODOLOGY.md`. Stored values are short, stable codes
(not display text) — see `docs/UI_LABELS.md` for the canonical
code-to-label mapping used by the Streamlit app.

| Metric | What it measures |
|---|---|
| Claim taxonomy (`claim_category_1`/`2`) | Groups detected positioning into `FUNCTIONAL`, `FREE_OF`, `NATURAL_ORGANIC`, `OTHER`, or `NO_CLAIM`, plus a sub-category. Sourced from pack-image extraction where available (`claim_source` = `vision`); fallback-derived classifications are labelled separately and must not be read as front-pack observations |
| Front-pack claim evidence | OCR/LLM observations from image-eligible sampled products. The current US/UK and France releases contain 17,127 valid front-of-pack observations |
| Nutrition benchmark flags | Nutrients (sugar, saturated fat, fat, salt) above UK FSA front-of-pack reference thresholds, stored as neutral codes |
| Claim-benchmark intersections | Co-occurrences of a detected positioning with a relevant nutrition or composition benchmark signal |
| Completeness score | Percentage of key structured fields populated per product (data quality indicator, not product quality) |
| Product segment | Planned — groupings by claim, ingredient, nutrition, and processing profile for future Streamlit market-overview views |

---

## Repository structure

```
food-beverage-positioning-radar/
│
├── pipeline/
│   ├── bootstrap.py         # OFF bulk export download/filter/category assignment
│   ├── ingest.py            # OFF API pull for incremental updates
│   ├── clean.py              # Cleaning, language detection, completeness
│   ├── analyze.py            # Ingredient marker analysis
│   ├── load.py                # SQLite storage + QA/reporting CSV export
│   ├── detect_positioning_signals.py    # Pre-LLM positioning proxy
│   ├── assign_reality_bands.py          # Sampling reality bands
│   ├── classify_formulation_families.py # Rule-based product-type families
│   ├── smart_sample.py        # Curated sample for vision analysis
│   ├── vision_extract.py     # Azure Vision OCR + LLM claim extraction
│   ├── review_context_check.py # Second-pass panel-context review
│   ├── merge_scores.py       # Joins vision results and writes pack-claim evidence
│   ├── tag_claims.py          # Claim taxonomy + nutrition benchmark flags
│   ├── compute_axis_ranges.py           # Market Overview display ranges
│   ├── compute_region_benchmarks.py     # Region/category benchmark table
│   ├── compute_profile_intersections.py # Profile-intersection precompute
│   ├── db_summary.py          # Reporting aggregation layer
│   ├── validate_tags.py      # Manual QA sampler for claim taxonomy
│   ├── export_schema.py      # Exports live DB schema to schema.sql
│   ├── verify_schema.py      # Checks live DB against current DDL
│   └── __init__.py
│
├── app.py                    # Streamlit main product
│
├── database/
│   └── schema.sql            # Auto-generated schema reference (see export_schema.py)
│
├── data/
│   ├── reference/
│   │   ├── company_brand_mapping.csv   # Brand → parent company
│   │   └── brand_alias_mapping.csv     # Brand variant → canonical brand
│   ├── country_region_mapping.csv
│   ├── raw/                  # Raw OFF API JSON (gitignored)
│   └── sample/                # Pipeline CSVs (gitignored)
│
├── docs/
│   ├── METHODOLOGY.md          # Metric definitions, scope statements, reporting layers
│   ├── CLAIM_EXTRACTION.md      # Sampling, prompt history, OCR/LLM release record
│   ├── COLUMN_DESCRIPTIONS.md  # Every database field documented
│   ├── BRAND_COMPANY_MAPPING.md # Brand/company mapping methodology
│   ├── UI_LABELS.md             # Stored-code → display-label mapping
│   ├── OBSERVATIONS.md          # Data quality and market-pattern findings
│   ├── LIMITATIONS.md           # Known limitations for interpretation
│   └── ADR.md                   # Architecture Decision Records
│
├── logs/                     # Pipeline run logs (gitignored)
│
├── .env.example               # Environment variable template
├── .gitignore
├── requirements.txt
├── LICENSE
├── CITATION.md
└── README.md
```

---

## How to run

**Prerequisites:** Python 3.12+, approximately 500MB disk space for
development data. Azure Vision and Azure OpenAI credentials are required
only for the vision pipeline. The core pipeline does not require Azure;
`ingest.py` requires internet access to Open Food Facts, while the later
non-vision steps run locally against the database.

```bash
# 1. Clone and set up environment
git clone https://github.com/julialenc/food-beverage-positioning-radar.git
cd food-beverage-positioning-radar
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt

# 2. Copy environment template and add credentials
cp .env.example .env
```

**Core pipeline** (no Azure credentials needed):

```bash
python pipeline/bootstrap.py    # Full OFF bulk-export population
# or, for small incremental/API updates:
python pipeline/ingest.py
python pipeline/clean.py        # Clean, detect language, score completeness
python pipeline/analyze.py      # Ingredient marker analysis
python pipeline/load.py         # Load into SQLite, export CSVs
```

**Vision pipeline** (requires Azure credentials, incurs API cost — see
`docs/CLAIM_EXTRACTION.md`, `docs/METHODOLOGY.md`, and `docs/ADR.md`):

```bash
python pipeline/detect_positioning_signals.py
python pipeline/assign_reality_bands.py
python pipeline/classify_formulation_families.py
python pipeline/smart_sample.py            # Select a curated sample for image analysis
python pipeline/vision_extract.py --test   # Test on 10 products first
python pipeline/vision_extract.py          # Full run (--resume to continue an interrupted run)
python pipeline/merge_scores.py            # Join composition + vision results
```

**Claim tagging and final reporting:**

```bash
python pipeline/tag_claims.py    # Claim taxonomy + nutrition benchmark flags
python pipeline/db_summary.py    # Final reporting aggregation (run after the full pipeline)
```

**Launch the app:**

```bash
streamlit run app.py
```

**Utility scripts** (QA and maintenance, run as needed rather than as part
of the standard pipeline):

```bash
python pipeline/validate_tags.py           # Manual QA sample of claim taxonomy output
python pipeline/export_schema.py           # Regenerate database/schema.sql
python pipeline/verify_schema.py           # Check the live DB against current code
```

**Note on API availability:** The Open Food Facts API is hosted on
non-profit infrastructure and may return 503 errors during European peak
hours. Running `ingest.py` before 08:00 or after 21:00 CET improves
reliability. The retry logic handles transient failures automatically.

**For production scale:** See `docs/ADR.md` ADR-001 for the bulk export
strategy (one-time download of the full OFF product database, weekly API
diff for new products).

---

## Data source and license

Data is sourced from [Open Food Facts](https://world.openfoodfacts.org/),
licensed under the **Open Database License (ODbL)**.

- Attribution is required: "Data from Open Food Facts — openfoodfacts.org"
- Redistribution of structured datasets derived from Open Food Facts data
  may trigger ODbL share-alike obligations
- Analysis outputs such as charts, summaries, reports, and dashboards may
  be treated differently from redistributed structured databases,
  depending on the use case

See `docs/LIMITATIONS.md` for coverage gaps, crowdsourced quality
caveats, licensing notes, and the absence of sales volume data. This
document is not legal advice; review the ODbL terms directly for any
specific redistribution use case.

This repository's code is MIT licensed. See `CITATION.md` for citation
guidance.

---

## Versioning

Version numbers refer to capability layers developed during the project,
not a strictly linear product-release sequence — see `docs/ADR.md` for
the full rationale behind each decision.

| Version | Status | Core deliverable |
|---|---|---|
| v1 | Rebuilding | Rule-based ingredient analysis; composite scores retained internally but not user-facing in the Streamlit MVP |
| v1.5 | Planned | German ingredient dictionary and broader bulk-export filtering |
| v2 | Planned | Product segmentation and additional Streamlit market-overview views |
| v3 | Complete | Vision pipeline and pack-image claim extraction; current US/UK and France releases contain 17,127 valid front-of-pack observations |
| v3.5 | Planned | Prompt/model calibration and targeted future extraction tests, including English panel-context review and prompt-drift checks |
| Production | Planned | Full OFF bulk export, weekly scheduler, Streamlit public deployment |

---

## Documentation

| Document | Contents |
|---|---|
| `docs/METHODOLOGY.md` | Metric definitions, scope and non-scope statements, extraction process, the ingredient-stage vs final-summary reporting distinction |
| `docs/CLAIM_EXTRACTION.md` | Front-of-pack sampling design, prompt history, OCR/LLM release record, validator behavior, and extraction limitations |
| `docs/COLUMN_DESCRIPTIONS.md` | Every database field documented with type, source, and interpretation notes |
| `docs/BRAND_COMPANY_MAPPING.md` | Brand normalisation methodology, mapping structure, known complications |
| `docs/UI_LABELS.md` | Canonical stored-code → display-label mapping for the Streamlit app |
| `docs/OBSERVATIONS.md` | Data quality findings and market-pattern observations from development |
| `docs/LIMITATIONS.md` | Data source limits, ODbL licensing, methodology and extraction caveats |
| `docs/ADR.md` | Architecture Decision Records — why the system was built the way it was |

---

## Contributing

Contributions welcome. Most useful areas:

- Extending the ingredient marker dictionary — German, Spanish, and
  Arabic variants
- Notebook contributions — model benchmarks, OCR quality analysis,
  prompt experiments
- New category analysis — dairy products, plant-based foods, sports
  nutrition
- Extending `db_summary.py`'s reporting fields — several per-claim-type
  percentage fields are documented as a planned, low-effort extension in
  its module docstring

Please open an issue before submitting a pull request.

---

*Data from Open Food Facts · openfoodfacts.org · ODbL license*
*Built with Python · No advertising, no sponsored content*
