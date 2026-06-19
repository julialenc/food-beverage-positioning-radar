# Food & Beverage Positioning Radar

**A neutral market intelligence tool for analyzing how packaged foods and
beverages position themselves through claims, ingredients, nutrition,
processing, and product design.**

[![Data License: ODbL](https://img.shields.io/badge/Data%20License-ODbL-blue)](https://opendatacommons.org/licenses/odbl/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org/)
[![Data: Open Food Facts](https://img.shields.io/badge/Data-Open%20Food%20Facts-orange)](https://world.openfoodfacts.org/)

---

## What this is

Food & Beverage Positioning Radar maps how packaged food and beverage
products position themselves through claims, ingredients, nutrition,
processing, and product design. It ingests product data from Open Food
Facts, extracts front-of-pack claims using OCR and LLM analysis, applies
ingredient-based composition scoring, and computes positioning and
benchmark metrics for exploration in Streamlit and Power BI-ready outputs.

**Main question:** How do packaged foods and beverages position themselves
through claims, ingredients, nutrition, processing, and product design?

One analytical lens compares front-of-pack positioning with composition
indicators, but the tool's broader purpose is market intelligence: product
segments, claim territories, ingredient systems, category patterns, and
positioning signals.

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
claims, ingredients, nutrition, processing, and product design. It is
especially relevant for smaller companies, startups, consultants, and
analysts who need a lightweight market-intelligence layer rather than a
full enterprise subscription or retail audit system.

---

## Who this is for

**Primary — CPG professionals, insight managers, market analysts,
consultants:** A market intelligence tool for identifying claim
territories, product segments, ingredient systems, and
positioning-to-composition patterns across packaged food and beverage
categories. Not a market share tool, retail audit, legal assessment,
consumer recommendation app, or product-verdict ranking system.

**Secondary — nutritionists, dietitians, nutrition coaches:** An education
and category-literacy tool for understanding how packaged products are
positioned and what they contain. Useful for finding coaching examples and
product-pattern illustrations. Not a meal-planning app, barcode scanner,
diet prescription tool, or consumer recommendation system.

**Technical — AI engineers, ML engineers, data scientists:** An applied
LLM/OCR pipeline for extracting and classifying product-positioning
signals from real-world packaging. Supports model, prompt, cost, OCR
quality, and structured-output comparisons. The technical audience is
served through this repository, notebooks, and benchmark documentation —
not through the main Streamlit UX.

The UX and roadmap are not optimized for legal/regulatory assessment,
investigative reporting, consumer advocacy, retail product-feed management,
or consumer purchase guidance. See `docs/METHODOLOGY.md` for the full
scope statement.

---

## Deliverables

| Deliverable | Status | Role |
|---|---|---|
| Streamlit app (`app.py`) | Main product | Search, filter, rank, and inspect products. Product card shows pack image, extracted claims, brand/category, nutrition, processing indicators, benchmark flags, and positioning-to-composition views. |
| Power BI insight deck (`powerbi/`) | Planned — secondary | Category maps, claim territories, brand/company summaries, benchmark intersections, and segment views. Fast aggregate storytelling; Streamlit for deeper inspection. |
| This repository | Active | Code, methodology, column descriptions, prompt and model experiments, notebooks, and benchmark tables. Serves the AI engineering audience without changing the main UX. |

---

## Key metrics

Every metric has a definition, a scope statement, and a non-scope
statement. The table below summarizes the main metrics; see
`docs/METHODOLOGY.md` for the full definitions.

| Metric | What it measures |
|---|---|
| Claim taxonomy | Groups pack claims into FUNCTIONAL, FREE_OF, NATURAL_ORGANIC, OTHER, or NO_CLAIM — and a secondary sub-category |
| Composition marker score | Severity-weighted count of ingredient-processing markers in the ingredient list (0–40) |
| Positioning-to-composition gap | Composite of composition markers, claim weight, and processing/nutrition context (0–100) |
| Nutrition benchmark flags | Nutrients above selected UK FSA front-of-pack reference thresholds; reference signal only, not a health or legal verdict |
| Claim-benchmark intersections | Rule-based co-occurrences of a pack claim with a relevant nutrition, ingredient, or processing benchmark signal; not an indication that a claim is false or misleading |
| Completeness score | Percentage of key structured fields populated — a data quality indicator, not a product quality score |
| Product segment | Planned — product groupings by claim, ingredient, nutrition, processing, and design profile |

---

## Repository structure

```
food-beverage-positioning-radar/
│
├── pipeline/
│   ├── ingest.py            # OFF API pull with pagination and retry
│   ├── clean.py             # Cleaning, language detection, completeness
│   ├── analyze.py           # Ingredient marker analysis, composition score
│   ├── load.py              # SQLite storage + Power BI CSV export
│   ├── smart_sample.py      # Tiered sampling for vision analysis
│   ├── vision_extract.py    # Azure Vision OCR + LLM claim extraction
│   ├── merge_scores.py      # Joins composition + vision → gap metric
│   ├── tag_claims.py        # Claim taxonomy + benchmark flags
│   ├── validate_tags.py     # Tag validation and QA checks
│   ├── db_summary.py        # Ad-hoc DB summary queries
│   ├── export_schema.py     # Schema export utility
│   └── verify_schema.py     # Schema verification utility
│
├── app.py                   # Streamlit main product
│
├── notebooks/               # Model benchmarks, exploratory analysis
│
├── database/
│   └── schema.sql           # SQLite schema (human-readable reference)
│
├── data/
│   ├── reference/
│   │   └── company_brand_mapping.csv   # 276 brands → parent company
│   └── sample/              # Pipeline CSVs (gitignored)
│
├── docs/
│   ├── METHODOLOGY.md         # Metric definitions, scope statements
│   ├── COLUMN_DESCRIPTIONS.md # All database fields documented
│   ├── BRAND_COMPANY_MAPPING.md # Mapping methodology and caveats
│   ├── OBSERVATIONS.md        # Data quality and market-pattern findings
│   ├── LIMITATIONS.md         # Known limitations for interpretation
│   └── ADR.md                 # Architecture Decision Records
│
├── powerbi/                 # Power BI deck
│
├── .env.example             # Environment variable template
├── requirements.txt
└── CITATION.md
```

---

## How to run

**Prerequisites:** Python 3.12+, approximately 500MB disk space for
development data, Azure Vision and Azure OpenAI credentials (for
vision pipeline only — all other steps run offline).

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

# 3. Run the core pipeline
python pipeline/ingest.py       # Pull products from Open Food Facts API
python pipeline/clean.py        # Clean, detect language, score completeness
python pipeline/analyze.py      # Ingredient marker analysis
python pipeline/load.py         # Load into SQLite, export CSVs

# 4. Vision pipeline (requires Azure credentials, incurs API cost)
python pipeline/smart_sample.py    # Select products for image analysis
python pipeline/vision_extract.py  # OCR + LLM claim extraction
python pipeline/merge_scores.py    # Join composition + vision results

# 5. Claim taxonomy and benchmark flags
python pipeline/tag_claims.py

# 6. Launch Streamlit app
streamlit run app.py
```

**Note on API availability:** The Open Food Facts API is hosted on
non-profit infrastructure and may return 503 errors during European peak
hours. Running `ingest.py` before 08:00 or after 21:00 CET improves
reliability. The retry logic handles transient failures automatically.

**For production scale:** See `docs/ADR.md` ADR-001 for the bulk export
strategy (one-time download of the full 4.4M product database, weekly
API diff for new products).

---

## Data source and license

Data is sourced from [Open Food Facts](https://world.openfoodfacts.org/),
licensed under the **Open Database License (ODbL)**:

- Use and analyze the data freely, subject to ODbL terms
- Attribution required: "Data from Open Food Facts — openfoodfacts.org"
- Derivative databases produced from Open Food Facts data may have
  share-alike obligations
- Analysis outputs such as charts, summaries, reports, and dashboards may
  be treated differently from redistributed structured databases,
  depending on the use case

Review the ODbL terms before redistributing datasets derived from this
pipeline. See `docs/LIMITATIONS.md` for coverage gaps, crowdsourced data
quality caveats, and the absence of sales volume data.

This repository's code is MIT licensed. See `CITATION.md` for citation
guidance.

---

## Development status

The table below describes pipeline capability layers rather than
sequential product versions. Layers are independent — vision extraction
(v3) is complete while the core pipeline is being rebuilt under the new
schema. This is not a contradiction; the vision results are archived and
will be re-tagged once the rebuild is complete.

| Layer | Status | Description |
|---|---|---|
| Core pipeline | 🔄 Rebuilding | Schema rename, production run, and Streamlit rebuild pending; pipeline logic validated in prior repo |
| Ingredient analysis | ✅ Validated | Rule-based composition-marker analysis (EN/FR) |
| Vision extraction | ✅ Complete for test run | Pack-image claim extraction on ~4,700 products; results archived |
| Segmentation + Power BI | 📋 Planned | Product segment analysis + Power BI insight deck |
| Model benchmark | 📋 Planned | gpt-4.1-nano vs gpt-4o-mini vs Claude Haiku on cost, quality, and structured output (~50 CHF budget) |
| Production deployment | 📋 Planned | Full OFF bulk export, weekly scheduler, public Streamlit app |

See `docs/ADR.md` for the full rationale behind each layer decision.

---

## Documentation

| Document | Contents |
|---|---|
| `docs/METHODOLOGY.md` | Metric definitions, scope and non-scope statements, extraction process |
| `docs/COLUMN_DESCRIPTIONS.md` | Every database field documented with type, source, and interpretation notes |
| `docs/BRAND_COMPANY_MAPPING.md` | Brand normalisation methodology, mapping structure, known complications |
| `docs/OBSERVATIONS.md` | Data quality findings and market-pattern observations from development |
| `docs/LIMITATIONS.md` | Data source limits, ODbL licensing, methodology caveats |
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

Please open an issue before submitting a pull request.

---

*Data from Open Food Facts · openfoodfacts.org · ODbL license*
*Built with Python · No advertising, no sponsored content*
