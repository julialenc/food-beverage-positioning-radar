# Column descriptions

This document describes every field in the four database tables: `products`,
`product_analysis`, `weekly_brand_summary`, and `ingestion_log`. It is the
canonical reference for field meaning, expected values, and source.

**Interpretation principle:** every field below is an analytical signal, not a
verdict. Fields describe observed or derived attributes — claims, ingredients,
nutrition values, benchmark positions, and co-occurrence patterns. No field
should be read as saying that a product is healthy, unhealthy, misleading,
legal, illegal, good, or bad.

## Table: `products`

One row per product (identified by barcode), sourced from Open Food Facts.

| Column | Type | Description |
|---|---|---|
| `barcode` | TEXT (primary key) | Product barcode (GTIN/EAN), the unique product identifier across all tables. |
| `product_name` | TEXT | Product name as recorded in Open Food Facts. |
| `brands` | TEXT | Raw brand string from Open Food Facts; may contain multiple comma-separated values (e.g. parent brand and sub-brand) exactly as entered by contributors. |
| `primary_brand` | TEXT | A single normalized brand value derived from `brands` (first comma-separated token, lowercased, accent-stripped), used for brand-level filtering and aggregation throughout the pipeline. |
| `quantity` | TEXT | Pack size / quantity as recorded in Open Food Facts (e.g. "500g", "1.15L"). European decimal commas are normalized to periods. |
| `packaging` | TEXT | Packaging material/type as recorded in Open Food Facts. |
| `query_category` | TEXT | The category used when this product was retrieved from Open Food Facts during data collection (e.g. snacks, beverages, cereals). |
| `off_categories` | TEXT | The full, raw category string as recorded in Open Food Facts, often containing multiple nested category tags. Used to refine `query_category`. |
| `countries` | TEXT | Pipe-separated list of country tags as recorded in Open Food Facts. |
| `primary_country` | TEXT | The first country extracted from `countries`. Reflects where the product was recorded in Open Food Facts, not necessarily where it is sold (see `docs/LIMITATIONS.md`). |
| `labels` | TEXT | Pipe-separated list of label/certification tags as recorded in Open Food Facts (e.g. organic, fair trade). |
| `ingredients_text` | TEXT | Raw ingredients list as recorded in Open Food Facts, used as input for ingredient-based analysis. |
| `additives_tags` | TEXT | Pipe-separated list of E-number additive tags, pre-parsed by Open Food Facts. |
| `energy_kcal` | REAL | Energy per 100g (or 100ml for liquids), in kilocalories. Values above 900 are treated as data errors and set to null. |
| `fat_100g` | REAL | Total fat per 100g/100ml. |
| `saturated_fat_100g` | REAL | Saturated fat per 100g/100ml. |
| `carbs_100g` | REAL | Total carbohydrates per 100g/100ml. |
| `sugars_100g` | REAL | Sugars per 100g/100ml (subset of total carbohydrates). |
| `fiber_100g` | REAL | Fibre per 100g/100ml. The most commonly missing nutrient in the source data, since fibre labelling is not mandatory in all markets. |
| `protein_100g` | REAL | Protein per 100g/100ml. |
| `salt_100g` | REAL | Salt per 100g/100ml. |
| `nutriscore_grade` | TEXT (A–E) | Nutri-Score letter grade as recorded in Open Food Facts, where available. The scale runs A to E, summarizing nutrition profile under the Nutri-Score system; it is a reference signal only and does not represent a product recommendation. |
| `nova_group` | REAL (1–4) | NOVA processing classification as recorded in Open Food Facts. 1 = unprocessed/minimally processed, 4 = ultra-processed. A reference classification, not a standalone verdict. |
| `completeness_score` | INTEGER (0–100) | Data-quality indicator: the percentage of eleven key fields (product name, brands, ingredients text, six nutrition values, Nutri-Score, NOVA group) that are populated for this product. Calculated as `round(filled_fields / 11 * 100)`. Reflects completeness of the source record, not the quality of the product itself. |
| `ingredients_lang` | TEXT (enum) | Detected language of `ingredients_text`: `EN`, `FR`, `BOTH` (bilingual packaging), `OTHER` (a different language, still retained), or `UNKNOWN` (text too short to classify). Keyword-based detection, not a language-ID model. |
| `nlp_eligible` | INTEGER (1/0) | Whether this product's ingredient text is eligible for ingredient-based analysis (true for `EN`, `FR`, `BOTH`). Products in `OTHER`/`UNKNOWN` retain full nutrition data but are excluded from ingredient-marker analysis to avoid silent false negatives from an English/French-only dictionary. |
| `created_t` | TEXT | Product creation timestamp in Open Food Facts, converted from Unix time. |
| `last_modified_t` | TEXT | Last modification timestamp in Open Food Facts, converted from Unix time. Used to identify products to re-pull on incremental updates. |
| `ingested_at` | TEXT | When this row was loaded into this database. |
| `image_url` | TEXT | Front-of-pack image URL from Open Food Facts. A placeholder value containing `/invalid/` indicates no real image is available; such rows are excluded before image-based analysis. |

## Table: `product_analysis`

One row per product (joined to `products` on `barcode`), containing all
ingredient-based, claim, and benchmark analysis. This table was previously
named `nlp_results`; the new name better reflects that it now holds both
text-based and image-based analysis, not only NLP output. A row may exist
with mostly empty fields if a product has not yet been through analysis.

### Identification

| Column | Type | Description |
|---|---|---|
| `barcode` | TEXT (primary key, foreign key) | Links to `products.barcode`. |
| `analyzed_at` | TEXT | When this row was last computed or updated. |

### Ingredient-based markers (composition only, no claims)

These fields are derived purely from `ingredients_text` and `additives_tags`,
independent of any pack claim or marketing language.

| Column | Type | Description |
|---|---|---|
| `upf_marker_count` | INTEGER | Count of distinct ingredient-processing marker categories detected in `ingredients_text` (one count per category, even if multiple keyword variants for that category appear). |
| `upf_markers_found` | TEXT | Pipe-separated list of the specific marker categories detected (e.g. `emulsifier`, `glucose_syrup`, `artificial_sweetener`). |
| `upf_max_severity` | INTEGER (0–3) | The highest severity weight among detected markers for this product. |
| `has_ultra_processed` | INTEGER (1/0) | Whether at least one processing-related marker was detected. |
| `e_number_count` | INTEGER | Count of distinct flagged E-numbers detected in `additives_tags`. |
| `e_numbers_found` | TEXT | Pipe-separated list of the specific E-numbers detected. |
| `has_artificial_sweetener` | INTEGER (1/0) | Whether an artificial sweetener was detected, via either `additives_tags` or ingredient-text keywords. |
| `composition_marker_score` | REAL (0–40) | A score summarizing ingredient-processing markers, calculated as the capped, severity-weighted sum of unique marker categories detected: each of roughly sixty known markers (sweeteners, emulsifiers, preservatives, glucose syrups, modified starches, artificial colours, and similar) carries a pre-assigned severity of 1, 2, or 3; at most one marker counts per category even if several keyword variants appear; the score is `min(40, 3 × sum of severities of unique categories detected)`. Example: three detected categories at severities 1, 2, and 3 sum to 6, giving a score of 18. This is a composition-only signal: it does not reference any pack claim and does not assess healthiness. |
| `composition_marker_band` | TEXT (enum) | Categorical band for `composition_marker_score`: `Extensive markers` (≥30), `Moderate markers` (≥20), `Limited markers` (≥10), `Minimal markers` (<10). Stored as text in the database; values should be updated if this band scale changes. |

### Ingredient-and-name-based claim signals

These fields scan `ingredients_text` (with mandatory-enrichment parentheticals
stripped, to avoid false positives such as "(niacin, riboflavin)" on enriched
flour) combined with `product_name`, or `product_name` combined with `labels`.
They detect claim-adjacent language present in the product record, distinct
from claims printed on the front of pack.

| Column | Type | Description |
|---|---|---|
| `ingredient_based_claim_signal_count` | INTEGER | Count of distinct claim-signal categories detected from ingredients text and product name. |
| `ingredient_based_claim_signals_found` | TEXT | Pipe-separated list of the specific signals detected (e.g. `protein_claim`, `fortification_claim`, `vegan_claim`). These are not pack claims; they are composition/name-derived signals, used as a fallback when image-based extraction is unavailable. |
| `absence_reduction_claim_count` | INTEGER | Count of distinct absence/reduction signals detected from product name and labels. |
| `absence_reduction_claims_found` | TEXT | Pipe-separated list of the specific signals detected (e.g. `no_added_sugar`, `no_gluten`, `natural_claim`), scanned from `product_name` and `labels`. |

### Pack-image-based claims (vision + LLM extraction)

These fields are populated only for products that have undergone image-based
claim extraction — a subset of the full product table. Coverage to date is
roughly 4,700 products, selected via a tiered sampling strategy (see
`docs/METHODOLOGY.md`).

| Column | Type | Description |
|---|---|---|
| `pack_analysis_attempted` | INTEGER (1/0) | **Recommended new column.** Whether this product was actually submitted for image-based claim extraction, regardless of outcome. Needed because a product that was analyzed and found to have no claims is otherwise indistinguishable from a product never analyzed at all — both currently leave `pack_claims_found` empty. Source: the OCR/LLM success status already computed in the claim-merging step; requires writing one additional field to the database. |
| `pack_claims_found` | TEXT | Pipe-separated list of claims identified directly from the front-of-pack image via OCR and structured extraction (e.g. `protein_claim`, `no_added_sugar`, `vegan_claim`, `heritage_claim`). The primary source for claim taxonomy when available. |

### Claim taxonomy (two-cut classification)

| Column | Type | Description |
|---|---|---|
| `claim_category_1` | TEXT (enum) | Broad claim category: `FUNCTIONAL` (claims of having or doing something — protein, fibre, vitamins, gut health, immune support, energy); `FREE_OF` (claims of not having something, or having reduced amounts — no added sugar, gluten-free, dairy-free, vegan, plant-based, no artificial ingredients); `NATURAL_ORGANIC` (organic, natural, clean-label, minimal-ingredient, or origin/naturalness claims); `OTHER` (heritage, comparative, sustainability, artisan); `NO_CLAIM` (no claim identified). Vegan and plant-based claims are classified under `FREE_OF` since they typically function as absence/substitution claims (free from animal-derived ingredients); this can be revisited if a dedicated lifestyle-claim category is needed later. |
| `claim_category_2` | TEXT (enum) | A more specific sub-category within `claim_category_1` (e.g. `protein`, `gut_health`, `no_added_x`, `free_from`, `natural`, `organic`, `heritage`, `comparative`). |
| `claim_source` | TEXT (enum) | **Recommended new column** (currently computed in memory only, not persisted). `vision` if `pack_claims_found` is non-empty, `nlp_only` otherwise. Note this does not by itself distinguish "never analyzed" from "analyzed, no claims found" — pair with `pack_analysis_attempted` for accurate coverage reporting. |

### Benchmark flags and intersections

| Column | Type | Description |
|---|---|---|
| `nutrition_benchmark_flags` | TEXT | Pipe-separated list of nutrients whose declared per-100g/100ml value exceeds a reference threshold for sugar, saturated fat, fat, or salt. Thresholds follow the UK Food Standards Agency's front-of-pack labelling guidance (also referenced informally across other European markets); the EU's mandatory nutrition declaration, Regulation 1169/2011, requires these nutrient values to be stated on pack but does not itself define high/low thresholds — that was deliberately left to individual schemes. Liquid vs solid is determined by an energy-density proxy (under 100 kcal/100ml is treated as liquid), so this is an approximation, not a direct product-type field. Computed independently of any claim; not a health verdict or legal assessment. |
| `claim_benchmark_intersections` | TEXT | Pipe-separated list of specific instances where an extracted claim co-occurs with a nutrition value above its reference threshold for the same attribute (e.g. a protein claim alongside high saturated fat, or a no-added-sugar claim alongside high total sugar). Describes co-occurrence only; does not indicate that a claim is false, illegal, or misleading. |

### Named intersection patterns

These flags identify specific, recurring claim/composition patterns observed
during manual validation, distinct from the general-purpose
`claim_benchmark_intersections` field above.

| Column | Type | Description |
|---|---|---|
| `sugar_positioning_intersection_flag` | INTEGER (1/0) | A sugar-reduction or absence claim (`no_added_sugar`, `reduced_sugar`) co-occurring with sugar content above the reference threshold (>8g/100g in current detection logic, evaluated independently of `nutrition_benchmark_flags`'s threshold). |
| `protein_fat_intersection_flag` | INTEGER (1/0) | A protein claim co-occurring with energy above 400 kcal/100g or saturated fat above 5g/100g. |
| `fibre_sugar_processing_intersection_flag` | INTEGER (1/0) | A fibre or prebiotic claim co-occurring with NOVA group 4 and sugar above 15g/100g. |
| `plant_based_nutrition_intersection_flag` | INTEGER (1/0) | A fortification claim on a plant-milk category product with energy above 60 kcal/100ml (the approximate dairy-milk benchmark). |

### Planned (not yet implemented)

| Column | Type | Description |
|---|---|---|
| `product_segment_label` | TEXT | Reserved column (previously `cluster_label`), currently always null. Intended to hold a market-segment grouping derived from claims, ingredients, nutrition, and processing indicators once segmentation analysis is built. |

### Removed from this table (carried in prior schema, not brought forward)

Ten individual boolean columns (`v3_immune_claim`, `v3_gender_targeting_claim`,
`v3_vegan_claim`, `v3_organic_claim`, `v3_dairy_free_claim`,
`v3_plant_based_claim`, `v3_heritage_claim`, `v3_gluten_free_claim`,
`v3_minimal_ingredients_claim`, `v3_no_palm_oil_claim`) existed in the prior
schema but were never written by any pipeline step — the merge step only ever
persists the aggregate `pack_claims_found` string. They are dropped here
rather than carried forward as permanently empty columns.

## Table: `weekly_brand_summary`

Pre-aggregated brand/category statistics, computed so that downstream
reporting tools never need to query raw product rows for trend views.

**Two changes from the prior schema, flagged for awareness:** the prior
version grouped by the raw `brands` field rather than the normalized
`primary_brand` used everywhere else in the pipeline, fragmenting brand
totals inconsistently with every other aggregation; this table now groups by
`primary_brand` instead. The prior version also included `high_score_count`
(score ≥ 70) and `medium_score_count` (score 45–69) columns that were
structurally impossible to populate, since the underlying score is capped at
40 — these counting/bucketing columns are removed rather than re-thresholded,
since count-based buckets read as verdict-adjacent regardless of the
underlying bug.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (primary key) | Auto-incrementing row identifier. |
| `week_ending` | TEXT | ISO date marking the end of the aggregation period. |
| `primary_brand` | TEXT | Normalized brand (see `products.primary_brand`). |
| `query_category` | TEXT | Product category for this aggregation row. |
| `product_count` | INTEGER | Number of products included in this brand/category/week grouping. |
| `avg_composition_marker_score` | REAL | Average `composition_marker_score` across products in this grouping. |
| `pct_nova4` | REAL | Percentage of products in this grouping classified as NOVA group 4. |
| `pct_with_ingredient_based_claim_signals` | REAL | Percentage of products with at least one detected ingredient-based claim signal. |
| `pct_with_artificial_sweetener` | REAL | Percentage of products containing an artificial sweetener. |
| `top_claim_type` | TEXT | The most frequently detected claim signal in this grouping. |
| `run_timestamp` | TEXT | When this aggregation row was computed. |

## Table: `ingestion_log`

One row per pipeline run, providing an audit trail of what was loaded, when,
and with what outcome.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (primary key) | Auto-incrementing row identifier. |
| `run_timestamp` | TEXT | When this pipeline run occurred. |
| `source` | TEXT | `api` or `bulk_export`, indicating the data source for this run. |
| `input_file` | TEXT | Filename of the input CSV processed in this run. |
| `category` | TEXT | `all`, or a specific product category, for this run. |
| `rows_in_file` | INTEGER | Number of rows in the input file. |
| `products_inserted` | INTEGER | Number of new rows inserted into `products`. |
| `products_updated` | INTEGER | Number of existing rows updated in `products`. |
| `analysis_inserted` | INTEGER | Number of new rows inserted into `product_analysis` (previously `nlp_inserted`). |
| `analysis_updated` | INTEGER | Number of existing rows updated in `product_analysis` (previously `nlp_updated`). |
| `status` | TEXT | `success`, `partial`, or `failed`. |
| `notes` | TEXT | Free-text notes, typically an error message on failed runs. |

## Open items for review

A few things surfaced while compiling this that go beyond pure renaming and
are worth a deliberate decision rather than a silent default:

1. **`positioning_composition_gap`'s actual behavior.** The full score is
Component A (ingredient markers, 0–40, identical to `composition_marker_score`)
plus Component B (claim-weight count, 0–30, zero if no claims) plus Component C
(a NOVA/Nutri-Score penalty, 0–30, but only triggered if Component B is
already above zero). This means a product with zero pack claims but a severe
ingredient profile can still score up to 40 — the name "gap" is accurate for
roughly 60 of the 100 points and only loosely descriptive of the rest. No
formula change is proposed here; the description above states this plainly so
the methodology document doesn't overclaim what the number means.
2. **`pack_analysis_attempted` and `claim_source` are new, not yet implemented**
columns requiring a small addition to the claim-merging step, not just a
rename. Confirm before they're treated as part of the schema.
3. **`composition_marker_band` and `positioning_composition_gap_band` band
labels** (`Extensive/Moderate/Limited/Minimal markers`; presumably similar
neutral labels for the gap score, not yet finalized) are proposed defaults —
these are stored as literal text in the database, so confirm wording before
the rename is applied in code.
