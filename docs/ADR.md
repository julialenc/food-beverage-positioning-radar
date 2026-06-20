# Architecture Decision Records

## Food & Beverage Positioning Radar

**Version:** 2.0
**Date:** June 2026
**Status:** Active
**Author:** Julia Lenc

---

## What is this document?

An Architecture Decision Record documents why the system was built the way
it was — not just what it does. It is written for three audiences: a
developer picking up the project in six months, a data analyst extending
the analysis, and a technical reviewer evaluating the project's
reproducibility.

Every significant design decision is recorded here with its rationale,
alternatives considered, and consequences. This makes the architecture
auditable and the scope choices defensible.

---

## Project overview

Food & Beverage Positioning Radar is a data pipeline and analysis system
that maps how packaged food and beverage products position themselves
through claims, ingredients, nutrition, processing, and product design.
It ingests product data from Open Food Facts (OFF), cleans and enriches
it, applies ingredient-based analysis and front-of-pack claim extraction,
computes positioning and benchmark metrics, and stores results for
Streamlit and Power BI consumption.

**Core analytical question:** How do packaged foods and beverages position
themselves through claims, ingredients, nutrition, processing, and product
design?

One analytical lens compares front-of-pack positioning with composition
indicators, but the broader system is designed for market intelligence:
product segments, claim territories, ingredient systems, category
patterns, benchmark intersections, and product-level evidence.

---

## Decision log

---

### ADR-001 — Data source: Open Food Facts API + bulk export

**Date:** 18 May 2026
**Status:** Active

**Decision:** Use Open Food Facts (OFF) as the primary data source,
combining the Live JSON API for development and weekly incremental updates,
and the OFF bulk CSV export for production-scale analysis.

**Rationale:** OFF is the only open, crowdsourced, global food product
database with structured nutritional data, ingredient lists, NOVA group
classifications, and Nutri-Score grades at scale. Commercial
product-intelligence databases (Nielsen, Mintel, Innova Market Insights)
are enterprise subscription products and are not reproducible or
redistributable in the same way as an open-data pipeline. OFF data is
licensed under ODbL — open for analysis, attribution required,
share-alike for derivative databases.

**Alternatives considered:**

- Scraping retailer websites (Carrefour, Tesco, Amazon Fresh): legally
  risky, technically fragile, no nutritional data
- USDA FoodData Central: US-only, limited to approximately 600,000
  products, no NOVA group
- Commercial databases: cost-prohibitive for a self-funded project, and
  non-reproducible by the intended technical audience

**Consequences:**

- Coverage bias toward Western Europe, especially France (see OBS-001)
- Data quality is crowdsourced — variable completeness (see OBS-002)
- No sales volume data — analysis is based on product presence and claim
  distribution, not market share (documented in `docs/LIMITATIONS.md`)
- Fully reproducible by anyone with internet access

**Production strategy (OBS-012):**

- Week 0: download full OFF bulk export (approximately 9GB compressed,
  4.4M products), filter to relevant categories, load into SQLite
- Weekly: query API for products with `last_modified_t` > 7 days,
  INSERT OR REPLACE on barcode
- No full table scan required — `last_modified_t` index makes
  weekly diff fast

---

### ADR-002 — API fields: selective pull, not full record

**Date:** 18 May 2026
**Status:** Active

**Decision:** Pull 16 fields from the OFF API rather than full product
records.

**Fields pulled:** code, product_name, brands, categories,
ingredients_text, nutriments, nutriscore_grade, nova_group,
countries_tags, labels_tags, quantity, packaging, created_t,
last_modified_t, additives_tags, image_url.

**Rationale:** OFF records have 180+ fields. Full records are large and
slow. We pull only what the analysis requires. `additives_tags` is
included because OFF pre-parses E-numbers from ingredient lists, saving
detection work in `analyze.py`. `image_url` is included to support
front-of-pack image extraction in the vision pipeline.

**Fields deliberately excluded from v1 (available for future versions):**

- `allergens_tags` — useful for dietary analysis extensions
- `ecoscore_grade` — environmental impact, relevant for sustainability
  positioning analysis
- `serving_size` — needed for serving-based claim analysis
- `stores` — retailer names, useful for market coverage analysis

---

### ADR-003 — Language scope: EN and FR only for ingredient analysis in v1

**Date:** 18 May 2026
**Status:** Active

**Decision:** Ingredient marker analysis applies only to products with EN,
FR, or BOTH ingredient text. OTHER and UNKNOWN language products are
retained in the dataset with null ingredient analysis scores.

**Rationale:** Language distribution in the production sample: FR=69%,
EN=11%, BOTH=3%, OTHER=14%, UNKNOWN=3%. The ingredient marker dictionary
covers EN and FR — applying it to Arabic, Bulgarian, or German ingredient
text produces silent false negatives (no markers detected where markers
are present). This is worse than transparently flagging as ineligible.
The `ingredient_analysis_eligible` boolean column makes this visible in
every downstream table.

**German as v1.5 candidate (OBS-009):** German ingredient vocabulary
shares significant overlap with EN/FR (maltodextrin, lecithin,
glucose-sirup, palmöl). Extension is low-effort and planned for v1.5
after EN/FR coverage is validated at scale.

**Consequences:** Approximately 16% of products are not analyzed by
ingredient markers in v1. These products retain valid nutritional data
and are included in benchmark flag computation and future segmentation.

---

### ADR-004 — Ingredient analysis approach: rule-based in v1

**Date:** 18 May 2026
**Status:** Active

**Decision:** Use rule-based keyword matching for ingredient marker
detection in v1. No ML models, no external NLP libraries beyond standard
Python.

**Options evaluated:**

- **Option A (chosen): Rule-based/keyword matching** — bilingual EN/FR
  keyword dictionary, zero dependencies, transparent, auditable, fast,
  works offline
- **Option B: K-Means clustering** — groups products by macronutrient
  profile, useful for market segmentation, no claim detection capability
- **Option C: LLM extraction** — extracts claims from packaging
  text/images, highest analytical value for pack-image analysis, requires
  API credits and infrastructure

**Why Option A for v1:** Rule-based ingredient analysis produces fully
auditable results. Every detected marker can be traced to a specific
keyword in a specific ingredient field. This is essential for a
reproducible market intelligence tool — every signal must be
independently verifiable. Option A also produces the
`composition_marker_score` that feeds the ingredient-analysis layer of
the positioning-to-composition gap metric.

**Validation methodology:** Validate the ingredient dictionary on a small
known sample before scaling. Three false positives were identified and
fixed during development (OBS-010, OBS-013): curcuma as colorant,
chicory fibre as texture ingredient, whey as confectionery ingredient.
Manual review of the top 20 scored products is recommended before any
new category or language is added.

---

### ADR-005 — v2 (K-Means segmentation) deferred

**Date:** 19 May 2026
**Status:** Deferred — no deadline

**Decision:** K-Means clustering on product composition data (Option B)
is not implemented in v1. The infrastructure is ready but it is not
prioritised ahead of the vision pipeline.

**Rationale:** The vision pipeline (v3) has higher analytical value for
the positioning-to-composition gap metric and was prioritised. K-Means
segmentation costs nothing computationally at the point of need and can
be added at any time. The `product_segment_label` column is present as
NULL in both `clean.py` output and the SQLite schema — when implemented,
it requires changes only to `analyze.py` with no schema migration.

**What segmentation adds:** Automatic grouping of products into market
segments based on macronutrient profiles, claim patterns, and processing
level. Intended to surface product clusters such as high-protein/lower-sugar
products vs high-energy/high-claim products within a category — described
by their centroid characteristics, not by health verdicts. Useful for
Power BI scatter plots (e.g. sugar vs protein, coloured by segment) and
for the "emerging product segments" business question in the brief.

**Stub in place:** `clean.py` adds `product_segment_label = None`.
The SQLite schema includes `product_segment_label TEXT` in the
`product_analysis` table.

---

### ADR-006 — Vision pipeline (v3) prioritised before segmentation

**Date:** 19 May 2026
**Status:** Active — complete

**Decision:** Proceed directly to front-of-pack image claim extraction
(v3) before implementing K-Means segmentation (v2).

**Rationale:** Front-of-pack claim extraction has higher analytical value
for the core positioning question — it captures pack communication signals
that cannot be inferred from ingredient text alone. The vision pipeline
supplies the front-of-pack evidence layer needed to compute the
positioning-to-composition composite signal in `merge_scores.py`.
Without pack-image claims, the metric is ingredient-only and cannot
represent front-of-pack positioning.

**Smart sampling strategy:** Do not analyze all products. Prioritize
brands and categories where positioning claims are most likely to be
present (see `pipeline/smart_sample.py` for the four-tier sampling logic).
Actual coverage: approximately 4,700 products.

**Actual cost and model (post-run):** Azure AI Vision Read API for OCR
plus Azure OpenAI `gpt-4.1-nano` for structured claim extraction.
Total cost for the full run: approximately 8 CHF. Haiku and gpt-4o-mini
were evaluated but gpt-4.1-nano was selected on cost/quality grounds.

**v3 output joins to v1 on barcode:** `composition_marker_score` (from
`analyze.py`) + extracted pack claims (from `vision_extract.py`) →
`positioning_composition_gap` (computed in `merge_scores.py`).

---

### ADR-007 — Storage: SQLite + CSV dual output

**Date:** 20 May 2026
**Status:** Active — schema extended by ADR-012

**Decision:** Store all pipeline output in SQLite with concurrent CSV
export for Power BI and notebooks.

**Schema (six tables, two groups):**

Core/load tables (owned by `load.py`):
- `products` — identity and nutrition, UPSERT on barcode
- `product_analysis` — ingredient markers, extracted claims, benchmark
  flags, and positioning metrics, UPSERT on barcode
- `weekly_brand_summary` — ingredient-stage QA / early summary only,
  computed at `load.py` time before pack-image claims or claim taxonomy
  exist. NOT the final Power BI market-intelligence table — see
  `weekly_brand_positioning_summary` below and ADR-012.
- `ingestion_log` — one row per pipeline run, full audit trail

Final reporting tables (owned by `db_summary.py`, see ADR-012):
- `weekly_brand_positioning_summary` — the actual pre-aggregated
  market-intelligence summary for Power BI trend charts, computed from
  the full database snapshot after `merge_scores.py` and `tag_claims.py`
  have run
- `positioning_example_products` — curated product-level examples for
  Streamlit/Power BI overview pages

**Why SQLite not PostgreSQL:** Single-developer research project. SQLite
is zero-infrastructure, file-based, version-controllable (schema.sql),
and sufficient for hundreds of thousands of rows. Migration to PostgreSQL
requires changing one connection string and no other code.

**Why pre-aggregate for Power BI:** DAX calculations on 100,000+ raw
rows are slow. `weekly_brand_positioning_summary` pre-computes
brand-level metrics in Python so Power BI does only rendering. This
pattern scales to any dataset size.

**UPSERT logic:** INSERT OR REPLACE on barcode primary key. Safe to run
multiple times. Handles Open Food Facts contributor corrections to
existing products automatically.

**WAL mode:** `PRAGMA journal_mode=WAL` enables safe concurrent reads
while Python writes — important when Power BI or Streamlit is connected.

---

### ADR-008 — Brand normalisation: primary_brand extraction

**Date:** 20 May 2026
**Status:** Active — company mapping complete

**Decision:** Extract `primary_brand` (first comma-separated token from
the `brands` field, lowercased, accent-stripped) as a normalisation step.
Full company-to-brand mapping table maintained in
`data/reference/company_brand_mapping.csv`.

**Problem:** The OFF `brands` field is free-text, contributor-entered.
The same company appears as multiple strings: `nestlé`, `nestle`,
`nestlé, nesquik`, `fitness` (Nestlé sub-brand), `perrier` (Nestlé
water brand). This makes brand-level aggregation inconsistent without
normalisation (see OBS-014).

**v1 fix:** `primary_brand` = first token, lowercased, accent-stripped
(NFKD normalisation). Reduces fragmentation significantly at low effort.

**Company mapping:** `data/reference/company_brand_mapping.csv` covers
276 brands across approximately 40 parent companies. Enables company-level
filtering and roll-up views in Power BI and Streamlit. All pattern
metrics are computed at brand level; company-level views are aggregations
of those brand-level results. See `docs/BRAND_COMPANY_MAPPING.md` for
mapping methodology and known complications.

---

### ADR-009 — Category scope: snacks, beverages, cereals in v1

**Date:** 18 May 2026
**Status:** Active — to be expanded with bulk export

**Decision:** Query three OFF categories in v1: snacks, beverages,
cereals.

**Rationale:** These three categories have the highest concentration of
functional, free-from, and organic/natural positioning claims in the
dataset and cover the core use cases: protein bars, energy drinks,
fortified breakfast cereals, plant-based drinks. They are also the
categories most relevant to the primary audience (CPG professionals,
insight managers, market analysts) described in the brief.

**Known limitation:** OFF categories are contributor-assigned folksonomy
tags, not a controlled vocabulary. Misclassification occurs (e.g. water
appearing in snacks). Category definitions are refined using the
`off_categories` field, which contains the full nested OFF category
hierarchy per product.

**Planned expansion:** With the full bulk export, add dairy products and
plant-based foods (growing claim territory, already partially covered
via beverages). UK and US market filtering applied via `countries_tags`.

**UK/US rationale:** The current sample is French-dominant (69% FR
language). UK and US markets show higher density of functional and
free-from claim language in these categories — protein bars, clean-label
snacks, and superfood positioning are well-represented in Anglo-Saxon
markets. OFF coverage of UK/US products is sufficient for trend and
claim-territory analysis.

---

### ADR-010 — Architectural pivot: Component B and C fed by vision, not ingredient text

**Date:** 22 May 2026
**Status:** Active — implemented from v3 onward

**Decision:** The `positioning_composition_gap` Components B (claim
weight) and C (processing/nutrition context weight) are fed exclusively
by Azure Vision front-of-pack extraction output, not by ingredient text
analysis.

**Rationale:** Component B in the original v1 design used ingredient text
as a proxy for front-of-pack claims. This produced systematic false
positives at scale:

- Enriched flour vitamins (niacin, riboflavin) triggering a fortification
  signal
- Milk proteins as texture ingredients triggering a protein signal
- Natural colorants (curcumin, paprika) triggering an adaptogen signal
- Energy drinks making tautological energy claims

Root cause: ingredient text describes what a product contains. Front-of-pack
describes what a brand communicates. These are different information
sources requiring different detection methods.

**New architecture (implemented in v3):**

Component A — ingredient composition score (0–40 points):
Source: `ingredients_text` + `additives_tags` (keyword dictionary).
Stored as `composition_marker_score`. Unchanged from v1.

Component B — claim weight (0–30 points):
Source: Azure Vision OCR → `gpt-4.1-nano` structured extraction.
Populated by `vision_extract.py` output, joined on barcode.
Zero for products without vision data.

Component C — context signal (0–30 points):
Source: vision claims × NOVA group × Nutri-Score.
Populated after v3 merge in `merge_scores.py`.
Only fires when Component B > 0.

Full composite stored as `positioning_composition_gap` (0–100).
See `docs/METHODOLOGY.md` for the complete formula and its known
limitations as a composite rather than a pure gap metric.

**Actual cost and model:** Azure AI Vision Read API (OCR) + Azure OpenAI
`gpt-4.1-nano` (claim extraction). Total run cost: approximately 8 CHF
for 4,700 products.

**False positives eliminated by this change:** Enriched flour vitamins,
milk proteins as texture ingredients, natural colorants, tautological
energy claims, protein-as-ingredient. See OBS-010 through OBS-017 in
`docs/OBSERVATIONS.md`.

---

### ADR-011 — Brand-level reporting and positioning typology

**Date:** 25 May 2026
**Status:** Active — informs sampling and reporting strategy

**Decision:** Analytical metrics are reported at brand level, not company
level. The `company_brand_mapping.csv` enables company-level roll-up
views in Power BI and Streamlit but all scoring, segmentation, and
benchmark intersection detection runs at `primary_brand` level.

**Rationale:** Company portfolios are too heterogeneous for company-level
metric averages to be meaningful (a conglomerate whose portfolio spans
mineral water and ultra-processed snacks produces a meaningless average).
Brand-level analysis is precise; company-level is navigational.

**Three brand positioning typologies observed in the dataset:**

Type 1 — Dedicated functional or specialty brands: entire portfolio
built around a specific positioning claim territory. Examples: Chiefs,
Fiber One, Atkins, Muscle Milk. High metric scores expected and
consistent with product intent. Useful as reference points for claim
intensity benchmarking.

Type 2 — Mainstream brands with a dedicated functional product line:
core portfolio carries minimal claims; a functional sub-line is added
to address a specific positioning territory. Examples: Snickers Protein,
Emmi Energy Milk, Emmi PUR, Mars Bar Protein, Special K Protein. Most
illustrative for positioning-to-composition gap analysis — mainstream
brand equity applied to a focused claim territory.

Type 3 — Mainstream brands with portfolio-wide positioning architecture:
claims appear consistently across the entire portfolio as part of brand
identity. Examples: Kellogg's (fortification across all cereals), Danone
(coordinated sub-brand claim territories), Alpro/Oatly (plant-based
positioning across the full range). Most useful for studying how claim
architecture varies across category and sub-brand.

**Two analytical dimensions for positioning analysis:**

Dimension 1 — Communication approach (HOW brands make claims):

1. Authorized health-claim style language: jurisdiction-specific
   approved wording applied to specific nutrient-delivery formats.
   Example: Actimel uses EU Regulation 432/2012 language for vitamins
   B6 and D. Describes the communication style observed, not a
   compliance assessment by this tool.
2. Numeric precision: hard numbers as primary differentiators. Example:
   Kellogg's Special K "12g protein", "HIGH FIBRE", "VITAMINS B6 B12 D".
3. Transparency positioning: ingredient simplicity used as a positioning
   claim. Example: Kind "ingredients you can see and pronounce".
4. Proprietary positioning marks: branded nutrient or ingredient systems
   used as a product concept. Examples: Nestlé OPTI-START, OPTI-GROW,
   OPTI-DÉJ, ACTIVGO.

Dimension 2 — Benefit territory (WHAT is claimed):

- Protein: largest claim territory; numeric and comparative claims dominant
- Sugar reduction: no added sugar + comparative % reduction
- Gut health: probiotic + fibre combined positioning
- Fortification: vitamins and minerals; often via proprietary marks
- Natural / clean label: transparency + origin + no artificial
- Plant-based: product-identity and substitution positioning
- Immune support: authorized health-claim style language territory
- Energy / performance: duration and endurance claims
- Free-from: gluten-free, lactose-free, dairy-free

The intersection of both dimensions identifies specific product
positioning patterns, for example: Protein × Numeric (Special K
"12g PROTEIN MEAL BARS"), Immune × Authorized health-claim style
(Actimel vitamins B6+D), Natural × Transparency (Kind), Fortification ×
Proprietary (Nestlé OPTI-GROW).

**Implications for analysis:**

- Filter brand-level summary views to n ≥ 20 products per brand to
  surface Type 3 portfolio-scale patterns
- Type 1 brands dominate raw metric rankings but are less analytically
  informative for positioning-to-composition gap analysis
- Type 2 brands are the most illustrative case studies for the gap
  between ingredient composition and front-of-pack communication
- Vegan and plant-based claims are classified as product-identity and
  substitution positioning rather than a nutritional benefit claim

---

### ADR-012 — Final reporting aggregation layer separated from claim tagging

**Date:** June 2026
**Status:** Active

**Decision:** `db_summary.py` is a dedicated final reporting aggregation
layer, run after `merge_scores.py` and `tag_claims.py`, kept separate
from `tag_claims.py` itself.

**Rationale:** `tag_claims.py`'s job is product-level classification —
claim taxonomy, benchmark flags, claim-benchmark intersections. This is
analysis: it operates on one product at a time. `db_summary.py`'s job is
reporting: brand/category summaries, claim territory distributions,
benchmark intersection rates, and a curated set of product-level
examples for Streamlit and Power BI overview pages. These are different
responsibilities, and keeping them in separate scripts keeps each one
focused and independently testable.

**Full snapshot, not weekly diff:** `db_summary.py` always recomputes
its summary from the full current database snapshot, regardless of
whether that snapshot was built via a one-time bulk export or updated
incrementally via a weekly API diff. This avoids ever reporting
"products changed this week" as if it were "the observed market this
week" — a load-bearing rule for any future production/incremental run.

**Two new tables, two different lifecycles:**
- `weekly_brand_positioning_summary` — a time series (one row per
  `week_ending` per brand/category), enabling trend queries such as
  "% of products with a protein claim over time." Existing rows for the
  same `week_ending` are replaced on rerun; rows from prior periods are
  preserved.
- `positioning_example_products` — NOT a time series. A small, neutral
  showcase of curated product examples, fully replaced (truncate +
  reinsert) on every run, with no historical accumulation.

**Why these tables aren't declared upfront by `load.py`:** `load.py`'s
"declare the full schema upfront" pattern (ADR-010 update) applies to
`product_analysis`, a table multiple pipeline stages enrich over a
single product row's lifetime. These two reporting tables have a
different lifecycle entirely — periodic snapshots and full-replace
showcases, not progressively-enriched rows — so `db_summary.py` owns
its own DDL directly, the same way `load.py` owns the DDL for the
tables it's responsible for.

---

## Modular contract between pipeline layers

The pipeline is designed so that each layer can be replaced independently
without breaking adjacent layers. This is the property that makes v2
segmentation and future v4 additions non-breaking.

```
ingest.py         →  data/raw/*.json
                     data/sample/sample_all_*.csv
                     [contract: barcode, product fields, additives_tags,
                      image_url]

clean.py          →  data/sample/clean_*.csv
                     [contract: same columns + cleaned text, language
                      flags, completeness_score, ingredient_analysis_eligible,
                      primary_brand, primary_country,
                      product_segment_label (null)]

analyze.py        →  data/sample/analyzed_*.csv
                     [contract: all clean columns + ingredient analysis
                      output: composition_marker_score,
                      composition_marker_band, processing_markers_found,
                      ingredient_based_claim_signals_found,
                      absence_reduction_claims_found]

load.py           →  database/positioning_radar.db
                     data/sample/powerbi_products_*.csv
                     data/sample/powerbi_analysis_*.csv
                     [contract: full product_analysis schema declared
                      upfront via DDL_* constants — see ADR-010 update
                      below — including fields not yet populated by
                      analyze.py]

smart_sample.py   →  data/sample/smart_sample_*.csv
                     [contract: barcode, image_url, tier, sampling_reason
                      — a purposive priority sample, not a market-
                      representative one, selected for pack-image
                      extraction]

vision_extract.py →  data/reference/vision_results_*.csv
                     [contract: barcode, ocr_text, ocr_status,
                      llm_status, vision_model, prompt_version,
                      pack_analysis_timestamp, claims_json, v3_* raw
                      claim fields. Does NOT output pack_claims_found —
                      that is computed in merge_scores.py from the v3_*
                      fields via an explicit allowlist.]

merge_scores.py   →  database/positioning_radar.db (pack-image results
                     and positioning_composition_gap written)
                     data/sample/merged_results_*.csv
                     [contract: barcode join of analyzed + vision results;
                      writes attempt metadata for every product attempted
                      this run, result fields only where extraction
                      succeeded — never overwrites a prior successful
                      result with NULL on a failed rerun]

tag_claims.py     →  database/positioning_radar.db (claim taxonomy added)
                     data/sample/powerbi_tagged_*.csv
                     [contract: claim_source, claim_category_1,
                      claim_category_2, nutrition_benchmark_flags,
                      claim_benchmark_intersections — UPDATE only, no
                      ALTER TABLE, since load.py already declares these
                      columns]

db_summary.py     →  database/positioning_radar.db (weekly_brand_positioning_summary
                     and positioning_example_products written)
                     data/sample/powerbi_final_*.csv
                     [contract: queries the full current database
                      snapshot, not intermediate CSVs — recomputed from
                      scratch every run regardless of whether the
                      snapshot was built via bulk export or weekly API
                      diff, so a weekly reporting summary never gets
                      mistaken for "products changed this week" instead
                      of "the observed market this week". See ADR-012.]
```

**Supporting utilities** (not part of the core data-transformation chain,
run separately for QA/maintenance): `validate_tags.py` is a manual QA
sampler for spot-checking claim taxonomy output; `export_schema.py`
exports the live database's actual tables and indexes to
`database/schema.sql` for reference; `verify_schema.py` checks the live
database against the current code's DDL constants across all six
tables, to catch schema drift if `positioning_radar.db` was created
under an older version of the pipeline.

**v2 upgrade (segmentation):** Replace the stub in `analyze.py`. No
other files change. `product_segment_label` column populates
automatically.

**Future v4 upgrade:** New enrichment scripts (e.g. pricing data, retail
coverage) can join to `products` on barcode without modifying existing
pipeline steps.

---

## Known limitations

| Limitation | Impact | Status |
|---|---|---|
| FR language dominance (69%) | Ingredient analysis misses 16% of products | German planned for v1.5; bulk export adds UK/US coverage |
| Crowdsourced data quality | Variable completeness, some errors | Reality checks in `notebooks/`; `completeness_score` per product |
| No sales volume data | Cannot measure market share | Documented in `docs/LIMITATIONS.md` |
| Brand fragmentation | Conglomerate aggregations need care | Company mapping in `data/reference/`; category filters recommended |
| OFF category folksonomy | Some category misclassification | Refined using `off_categories` full hierarchy field |
| Image-based analysis covers a subset | Front-of-pack claim coverage is incomplete for non-sampled products; fallback taxonomy may rely on product name, labels, and ingredient/name-derived signals | ~4,700 products analyzed; `pack_analysis_attempted` flag indicates coverage |
| Sports nutrition context | Benchmark flags may reflect intended use, not unexpected profile | Documented in `docs/LIMITATIONS.md` |
| Liquid/solid classification is a proxy | Energy-density heuristic may misclassify some formats | MVP approximation; flagged for review if benchmark flags become central |

---

## Versioning summary

Version numbers refer to capability layers developed during the
project, not a strictly linear product-release sequence — this is why
v1 can show "rebuilding" status while v3 shows "complete": each
version tracks a distinct capability (ingredient analysis, vision
extraction, segmentation), not a sequential release train.

| Version | Status | Core deliverable |
|---|---|---|
| v1 | 🔄 Rebuilding | Rule-based ingredient analysis, composition marker score — pipeline logic validated in prior repo; schema rename, production run, and Streamlit rebuild pending |
| v1.5 | 📋 Planned | German ingredient dictionary, UK/US bulk export filtering |
| v2 | 📋 Planned | K-Means product segmentation + Power BI insight deck (category maps, claim territories, brand/company summaries, benchmark intersections, segment views) |
| v3 | ✅ Complete | Vision pipeline, pack-image claim extraction, ~4,700 products analyzed — vision results archived; re-tagging only if claim taxonomy changes |
| v3.5 | 📋 Planned | Extended vision run on additional products (~50 CHF budget); model benchmark comparing gpt-4.1-nano, gpt-4o-mini, and Claude Haiku on cost, extraction quality, and structured output reliability; results documented in `notebooks/` |
| Production | 📋 Planned | Full OFF bulk export, weekly scheduler, Streamlit public deployment |

---

*This document is updated as new decisions are made.*
*Last updated: June 2026 (ADR-012 added; modular contract corrected to
actual execution order and extended to db_summary.py and supporting
utilities)*
