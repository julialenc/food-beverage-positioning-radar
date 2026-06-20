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
ingredient-based composition scoring, and computes positioning and
benchmark metrics for exploration in a Streamlit app and a Power BI deck.

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
| Streamlit app (`app.py`) | Main product | Search, filter, sort, and inspect products. Product card shows pack image, extracted claims, brand/category, nutrition, processing indicators, benchmark flags, and positioning-to-composition views. |
| Power BI deck (`powerbi/`) | Secondary insight layer | Category maps, claim territories, brand/company summaries, benchmark intersections, and, once implemented, segment views, built from `db_summary.py`'s final reporting exports. Fast aggregate storytelling; Streamlit for deeper inspection. |
| This repository | Technical and reproducibility layer | Code, methodology, column descriptions, prompt and model experiments, notebooks, and benchmark tables. Serves the AI engineering audience without changing the main UX. |

---

## Key metrics

Every metric has a definition, a scope statement, and a non-scope
statement in `docs/METHODOLOGY.md`. Stored values are short, stable codes
(not display text) — see `docs/UI_LABELS.md` for the canonical
code-to-label mapping used by the Streamlit app and Power BI deck.

| Metric | What it measures |
|---|---|
| Claim taxonomy (`claim_category_1`/`2`) | Groups pack claims into `FUNCTIONAL`, `FREE_OF`, `NATURAL_ORGANIC`, `OTHER`, or `NO_CLAIM`, plus a sub-category. Sourced from pack-image extraction where available (`claim_source` = `vision`), otherwise from combined ingredient/name-derived signals |
| Composition marker score | Weighted ingredient-processing marker score (0–40), with a reference band (`Extensive`/`Moderate`/`Limited`/`Minimal markers`) |
| Positioning-to-composition gap | Composite of composition markers, claim weight, and processing/nutrition context (0–100), with a reference band (`High`/`Moderate`/`Low`/`Minimal positioning-composition signal`) |
| Nutrition benchmark flags | Nutrients (sugar, saturated fat, fat, salt) above UK FSA front-of-pack reference thresholds, stored as neutral codes |
| Claim-benchmark intersections | Co-occurrences of a detected positioning with a relevant nutrition or composition benchmark signal |
| Completeness score | Percentage of key structured fields populated per product (data quality indicator, not product quality) |
| Product segment | Planned — K-Means groupings by claim, ingredient, nutrition, and processing profile |

---

## Repository structure

```
food-beverage-positioning-radar/
│
├── pipeline/
│   ├── ingest.py            # OFF API pull with pagination and retry
│   ├── clean.py              # Cleaning, language detection, completeness
│   ├── analyze.py            # Ingredient marker analysis, composition score
│   ├── load.py                # SQLite storage + Power BI CSV export
│   ├── smart_sample.py        # Purposive tiered sample for vision analysis
│   ├── vision_extract.py     # Azure Vision OCR + LLM claim extraction
│   ├── merge_scores.py       # Joins composition + vision → positioning gap
│   ├── tag_claims.py          # Claim taxonomy + nutrition benchmark flags
│   ├── db_summary.py          # Final reporting aggregation layer
│   ├── validate_tags.py      # Manual QA sampler for claim taxonomy
│   ├── export_schema.py      # Exports live DB schema to schema.sql
│   ├── verify_schema.py      # Checks live DB against current DDL
│   └── __init__.py
│
├── app.py                    # Streamlit main product
│
├── notebooks/                # Model benchmarks, exploratory analysis
│
├── database/
│   └── schema.sql            # Auto-generated schema reference (see export_schema.py)
│
├── data/
│   ├── reference/
│   │   └── company_brand_mapping.csv   # 276 brands → parent company
│   ├── raw/                  # Raw OFF API JSON (gitignored)
│   └── sample/                # Pipeline CSVs (gitignored)
│
├── docs/
│   ├── METHODOLOGY.md          # Metric definitions, scope statements, reporting layers
│   ├── COLUMN_DESCRIPTIONS.md  # Every database field documented
│   ├── BRAND_COMPANY_MAPPING.md # Brand/company mapping methodology
│   ├── UI_LABELS.md             # Stored-code → display-label mapping
│   ├── OBSERVATIONS.md          # Data quality and market-pattern findings
│   ├── LIMITATIONS.md           # Known limitations for interpretation
│   └── ADR.md                   # Architecture Decision Records
│
├── powerbi/                  # Power BI deck
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
python pipeline/ingest.py       # Pull products from Open Food Facts API
python pipeline/clean.py        # Clean, detect language, score completeness
python pipeline/analyze.py      # Ingredient marker analysis
python pipeline/load.py         # Load into SQLite, export CSVs
                                 # (use --source bulk_export for a full bulk-export run)
```

**Vision pipeline** (requires Azure credentials, incurs API cost — see
`docs/METHODOLOGY.md` and `docs/ADR.md` for historical cost estimates):

```bash
python pipeline/smart_sample.py            # Select a purposive sample for image analysis
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
| v1 | 🔄 Rebuilding | Rule-based ingredient analysis, composition marker score — pipeline logic validated; schema rename, production run, and Streamlit rebuild pending |
| v1.5 | 📋 Planned | German ingredient dictionary, UK/US bulk export filtering |
| v2 | 📋 Planned | K-Means product segmentation + Power BI insight deck |
| v3 | ✅ Complete | Vision pipeline, pack-image claim extraction, ~4,700 products analyzed |
| v3.5 | 📋 Planned | Extended vision run (~50 CHF budget); model benchmark comparing gpt-4.1-nano, gpt-4o-mini, and Claude Haiku on cost, quality, and structured output reliability |
| Production | 📋 Planned | Full OFF bulk export, weekly scheduler, Streamlit public deployment |

---

## Documentation

| Document | Contents |
|---|---|
| `docs/METHODOLOGY.md` | Metric definitions, scope and non-scope statements, extraction process, the ingredient-stage vs final-summary reporting distinction |
| `docs/COLUMN_DESCRIPTIONS.md` | Every database field documented with type, source, and interpretation notes |
| `docs/BRAND_COMPANY_MAPPING.md` | Brand normalisation methodology, mapping structure, known complications |
| `docs/UI_LABELS.md` | Canonical stored-code → display-label mapping for the Streamlit app and Power BI deck |
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
