# Architecture Decision Records

## Food & Beverage Positioning Radar

**Version:** 2.2  
**Date:** September 2026  
**Status:** Active  
**Author:** Julia Lenc

---

## Purpose

This document records the major architectural decisions behind Food & Beverage
Positioning Radar and the reasons they were made.

It is intentionally narrower than the methodology and governance documents:

- `docs/METHODOLOGY.md` explains what the analytical outputs mean;
- `docs/LIMITATIONS.md` catalogs interpretation caveats;
- `docs/CATEGORY_CLEANUP.md` defines category governance;
- `docs/BRAND_COMPANY_MAPPING.md` defines brand/company mapping governance;
- `docs/NUTRITION_OUTLIER_GOVERNANCE.md` defines nutrition-quality rules;
- `docs/CLAIM_EXTRACTION.md` documents sampling, prompts, and extraction history.

The ADR should explain **why the system is structured this way**, not duplicate
those documents.

## Project overview

Food & Beverage Positioning Radar is a reproducible market-intelligence pipeline
for packaged foods and beverages. It combines Open Food Facts product data with
category cleanup, brand/company normalization, ingredient analysis, nutrition
governance, front-of-pack claim extraction, and reporting layers for Streamlit
and downstream analysis.

Core analytical question:

> How do packaged foods and beverages position themselves through claims,
> ingredients, nutrition, processing, and product design?

---

# Decision log

## ADR-001 — Use Open Food Facts as the primary product source

**Date:** 18 May 2026  
**Status:** Active

**Decision:** Use Open Food Facts (OFF) as the primary product source. Use the
bulk export for production-scale bootstrap and the API for development and
incremental updates.

**Rationale:** OFF is open, global, structured, reproducible, and includes the
nutrition, ingredient, category, NOVA, Nutri-Score, and image fields required by
the project. Commercial product-intelligence databases are not reproducible or
redistributable in the same way.

**Consequences:**

- source coverage and completeness are uneven;
- product counts are not sales or market share;
- ODbL attribution/share-alike obligations apply to OFF-derived data;
- project-level governance is required rather than treating OFF fields as clean
  analytical truth.

See `docs/LIMITATIONS.md`.

---

## ADR-002 — Pull only the OFF fields required by the pipeline

**Date:** 18 May 2026  
**Status:** Active

**Decision:** Use a selective OFF field set rather than full records.

Core fields include product identity, product name, brands, categories,
ingredients, nutriments, Nutri-Score, NOVA, country tags, labels, quantity,
packaging, timestamps, additives, and image URL.

**Rationale:** Full OFF records are large and contain many fields irrelevant to
the MVP. A selective contract reduces transfer, storage, and processing cost
while remaining explicit and reproducible.

**Consequence:** New analytical dimensions such as allergens, Eco-Score, serving
size, or retailer-store coverage require an intentional schema/input extension.

---

## ADR-003 — Limit ingredient-marker analysis to supported languages

**Date:** 18 May 2026  
**Status:** Active

**Decision:** Run ingredient-marker analysis only when ingredient text is
English, French, or bilingual EN/FR. Retain other products but leave the
ingredient-analysis output ineligible/null.

**Rationale:** Applying an unsupported dictionary would create silent false
negatives, which is worse than an explicit missing analytical layer.

**Consequence:** Nutrition, brand, category, company, and image-based analysis
can still be used for products outside the ingredient-language scope.

---

## ADR-004 — Use transparent rule-based ingredient analysis

**Date:** 18 May 2026  
**Status:** Active

**Decision:** Use auditable keyword/rule logic for ingredient-marker detection
rather than an opaque ML classifier.

**Rationale:** Every ingredient signal should be traceable to source text and a
known rule. Rule-based detection is fast, reproducible, dependency-light, and
appropriate for the EN/FR MVP vocabulary.

**Consequence:** The dictionary requires explicit maintenance and language
expansion. Historical composite fields derived from these markers remain
internal rather than user-facing scores.

---

## ADR-005 — Defer product segmentation until the evidence layers are stable

**Date:** 19 May 2026  
**Status:** Deferred

**Decision:** Do not prioritize K-Means/product segmentation ahead of the vision
and governance layers.

**Rationale:** Front-of-pack evidence, category quality, brand/company routing,
and nutrition governance provide more immediate analytical value and are
prerequisites for trustworthy segmentation.

**Consequence:** `product_segment_label` can remain unpopulated until a later
segmentation phase without blocking the MVP.

---

## ADR-006 — Prioritize front-of-pack vision extraction

**Date:** 19 May 2026  
**Status:** Active — implemented

**Decision:** Build front-of-pack OCR/LLM extraction before product
segmentation.

**Rationale:** Ingredient text describes what a product contains; front-of-pack
analysis captures what the product communicates. The positioning question
requires both evidence layers.

**Consequence:** Image-based extraction is a distinct pipeline stage with its
own sampling, validation, model, prompt, and release metadata.

See `docs/CLAIM_EXTRACTION.md`.

---

## ADR-007 — Use SQLite as the analytical store, with CSV outputs for QA

**Date:** 20 May 2026  
**Status:** Active

**Decision:** Store the working analytical database in SQLite and emit CSV
outputs at relevant pipeline stages for QA, review, and downstream analysis.

**Rationale:** SQLite is appropriate for a single-developer research product:
zero infrastructure, portable, inspectable, and sufficient for the project
scale. CSV exports make intermediate states easy to audit.

**Key consequences:**

- product tables use barcode/GTIN as the primary identity;
- idempotent reruns use UPSERT/replace logic where appropriate;
- WAL mode supports concurrent reads during writes;
- reporting tables can be precomputed rather than recalculated interactively in
  Streamlit.

---

## ADR-008 — Separate consumer brand from company / owner

**Date:** 20 May 2026  
**Status:** Active — launch architecture finalized September 2026

**Decision:** Treat brand normalization and company routing as separate layers:

1. preserve raw OFF brand evidence;
2. extract the most useful consumer-facing brand entity;
3. normalize approved spelling/punctuation/aliases;
4. optionally retain a broader `brand_family`;
5. resolve company/owner separately for navigation and filtering.

The preferred launch brand is `normalized_brand`. `primary_brand` is retained
only for legacy compatibility/provenance.

**Rationale:** OFF brand strings frequently mix consumer brands, parent
companies, retailer banners, private-label ranges, legal entities, and noisy
contributor text. Flattening these too early destroys useful market structure.

**Company principle:** `resolved_company` is directional analytical routing, not
a universal legal ownership register. Market, product form, licensing,
joint-venture, private-label, and transaction timing can require scoped
outcomes.

**Conservative rule:** If ownership cannot be established with sufficiently
strong evidence, keep `Other / not mapped to a company`. A false negative is
preferred to a false-positive owner assignment.

See `docs/BRAND_COMPANY_MAPPING.md`.

---

## ADR-009 — Use four governed launch categories

**Date:** 18 May 2026  
**Status:** Active — launch governance finalized September 2026

**Decision:** The launch analytical categories are:

```text
snacks
beverages
cereals
dairies
```

The app displays `dairies` as **Dairy**.

**Rationale:** These categories cover the project's main positioning use cases
while remaining manageable enough for explicit cleanup and validation.

**Architecture:** Category assignment is governed by product format and
commercial use case, not simply by OFF parent tags. Shared deterministic rules
are used in both bulk and incremental ingestion, while exact reviewed GTIN
overrides handle product-specific exceptions.

A reviewed product may be:

- kept in its current category;
- routed to another launch category;
- assigned `OUT_OF_SCOPE`.

`OUT_OF_SCOPE` removes the product from the app-facing four-category universe
without deleting its underlying source/provenance record.

**Launch state:** Snacks and cereals received detailed manual category cleanup
across France, UK/Ireland, and US/Canada. The September mapping/orphan audits
also added exact category corrections across France and US/Canada.

Restaurant/menu observations are not packaged CPG products and should be
filtered upstream when a safe source/type discriminator exists. Broad
restaurant-brand exclusions are unsafe because the same brand can also appear
on packaged retail products.

See `docs/CATEGORY_CLEANUP.md`.

---

## ADR-010 — Front-of-pack claim evidence must come from pack observation

**Date:** 22 May 2026  
**Status:** Active

**Decision:** Confirmed front-of-pack claim evidence comes from image
observation via OCR + LLM extraction, not from ingredient text or product-name
inference.

**Rationale:** Ingredient text and pack communication are different evidence
layers. Ingredient-derived proxies created systematic false positives when
treated as claims.

**Consequences:**

- ingredient/name-derived signals may remain for internal QA or fallback
  analysis;
- they must not be presented as confirmed pack observations;
- a valid observed no-claim pack must remain a true no-claim result;
- historical `positioning_composition_gap` remains legacy/internal and is not a
  user-facing proprietary score.

See `docs/METHODOLOGY.md` and `docs/CLAIM_EXTRACTION.md`.

---

## ADR-011 — Analyze primarily at product and brand level; use company for navigation

**Date:** 25 May 2026  
**Status:** Active

**Decision:** Product and brand are the primary analytical units.
Company/owner is primarily a navigation, filtering, and portfolio roll-up layer.

**Rationale:** Company portfolios can span fundamentally different categories
and product architectures. Company-level averages can therefore obscure more
than they explain, while brand/product/category analysis retains meaningful
positioning structure.

**Consequences:**

- metrics and benchmark intersections should be interpreted at product,
  normalized-brand, brand-family, and category levels;
- company views require the scoped ownership resolver;
- company aggregation must not imply legal ownership certainty or commercial
  market share.

---

## ADR-012 — Keep final reporting aggregation separate from product tagging

**Date:** June 2026  
**Status:** Active

**Decision:** `tag_claims.py` remains a product-level classification step, while
`db_summary.py` owns final aggregate reporting tables.

**Rationale:** Product classification and reporting aggregation have different
responsibilities, testing needs, and lifecycles.

**Reporting rules:**

- `weekly_brand_summary` is an earlier ingredient-stage QA summary;
- `weekly_brand_positioning_summary` is the final reporting aggregation layer;
- `positioning_example_products` is a refreshed example set, not a time series;
- final summaries are recomputed from the full current database snapshot, not
  only from products changed in the latest incremental update.

This prevents "products changed this week" from being mistaken for "the observed
market this week."

---

## ADR-013 — Separate bulk bootstrap from weekly incremental ingestion

**Date:** 12 July 2026  
**Status:** Active

**Decision:** Use two ingestion paths:

1. OFF bulk export via the bootstrap path for initial/full population;
2. API-based incremental ingestion for new or recently modified products.

**Rationale:** OFF provides bulk exports for large-scale retrieval. The search
API is appropriate for incremental lookup, not for repeatedly scraping the full
database.

**Consequence:** Production cadence keeps weekly API batches small and
purpose-specific while retaining a reproducible full-bootstrap path.

---

## ADR-014 — Use curated sampling before scaling paid vision extraction

**Date:** 12 July 2026  
**Status:** Active

**Decision:** Run OCR/LLM claim extraction on a curated image-eligible sample
rather than automatically processing the entire product universe.

The sample combines a probability-oriented backbone with purposive and
calibration components.

**Rationale:**

- most OFF products do not require expensive claim extraction for taxonomy
  development;
- the project should validate prompts, taxonomy, and panel handling before
  scaling cost;
- the design supports both observed sample proportions and approximate
  backbone design-weighted estimates within the image-eligible OFF frame.

**Consequence:** Products outside the extraction sample have no confirmed
front-pack claim observation and must not be silently assigned one from
ingredient/name inference.

See `docs/CLAIM_EXTRACTION.md`.

---

## ADR-015 — Use reviewed reference layers, exact overrides, and lock/regression validation

**Date:** September 2026  
**Status:** Active — launch mapping architecture locked

**Decision:** Treat curated reference files and reviewed GTIN overrides as
governed production inputs with explicit precedence, rather than as loose lookup
tables.

Final precedence:

```text
1. Region-scoped reviewed GTIN override
2. Unscoped reviewed GTIN override
3. Explicit market / product-form / category scoped company rule
4. Exact normalized brand -> company rule
5. Safe validated brand alias
6. Non-exact matching for candidate generation only
7. Other / not mapped to a company
```

Exact reviewed product overrides can correct:

- normalized brand;
- resolved company;
- analytical category;
- `OUT_OF_SCOPE` status.

They do **not** automatically create reusable aliases or broad brand/category
rules.

**Rationale:** The final retailer, manufacturer, and orphan audits exposed
collisions, licensing differences, market-specific ownership, private-label
architecture, imported products, stale OFF metadata, and product-level category
errors that cannot be handled safely through global aliases.

**Orphan completion rule:** A qualifying orphan is a normalized brand still
under `Other / not mapped to a company` with at least 100 products within one
specific `region × category` bucket.

France and US/Canada contained qualifying orphan candidates and were audited.
UK/Ireland had no qualifying orphan candidates at that threshold.

The launch success criterion is now satisfied: no qualifying normalized brand
remains under `Other / not mapped to a company` without reviewed resolution.
Individual products may still remain under `Other` when evidence is genuinely
insufficient.

**Lock model:** Once a reviewed manufacturer, retailer, or regional mapping
scope is locked, later changes must regression-test that locked architecture.
A new exact correction may override stale or contaminated evidence, but broad
rules must not silently reassign previously validated products.

See `docs/BRAND_COMPANY_MAPPING.md`.

---

# Modular pipeline contract

The pipeline is deliberately layered so stages can evolve without requiring a
full redesign:

```text
OFF bulk/API
    ↓
ingest / bootstrap
    ↓
clean
    ├─ category governance
    ├─ brand normalization
    └─ company routing
    ↓
analyze
    └─ ingredient-based analysis
    ↓
load → SQLite
    ↓
smart_sample
    ↓
vision_extract
    └─ OCR + structured claim extraction
    ↓
merge_scores
    ↓
tag_claims
    └─ claim taxonomy + benchmark intersections
    ↓
db_summary
    └─ final reporting aggregates
    ↓
Streamlit / QA / exports
```

Cross-cutting governance layers include:

- `data/reference/brand_alias_mapping.csv`;
- `data/reference/company_brand_mapping.csv`;
- `data/reference/private_label_brand_mapping.csv`;
- `data/reference/reviewed_product_mapping_overrides.csv`;
- nutrition-quality flags and category rules.

The contract principle is stable identifiers plus explicit derived fields:
later stages enrich products rather than overwriting source provenance.

---

# Current architectural boundaries

The following are deliberate boundaries rather than unresolved design mistakes:

- OFF is the reproducible source, but not a sales/market-share dataset;
- ingredient analysis remains EN/FR scoped;
- image-based claims exist only for sampled image-eligible products;
- category/company layers are governed analytical classifications, not universal
  taxonomy or legal ownership truth;
- nutrition governance controls analytical eligibility rather than correcting
  OFF source values;
- beverage segmentation is a comparability layer, not a full market taxonomy;
- segmentation remains a future analytical extension.

For interpretation details, use `docs/LIMITATIONS.md`.

---

# Capability status

| Capability | Status |
|---|---|
| OFF bulk bootstrap + incremental API | Active |
| Rule-based ingredient analysis | Active |
| Category cleanup / exact category overrides | Active and launch-locked |
| Brand normalization / company routing | Active and launch-locked |
| Retailer/private-label mapping | Complete and locked |
| Top-9 manufacturer mapping | Complete and locked |
| Regional orphan-brand completion | Complete and locked |
| Nutrition-quality governance | Active |
| Vision/OCR/LLM claim extraction | Active |
| Final reporting aggregation | Active |
| Product segmentation | Deferred / future |

---

*This document is updated when a material architectural decision changes.*
