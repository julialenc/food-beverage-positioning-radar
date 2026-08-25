# Column descriptions

This document describes the core database tables currently documented for the
project: `products`, `product_analysis`, `weekly_brand_summary`, and
`ingestion_log`. It is the canonical reference for field meaning, expected
values, and source for those tables. Some newer reporting, audit, and Streamlit
precompute outputs are noted at the end for a later schema-documentation pass.

**Interpretation principle:** every field below is an analytical signal, not a
verdict. Fields describe observed or derived attributes — claims, ingredients,
nutrition values, benchmark positions, and co-occurrence patterns. No field
should be read as saying that a product is healthy, unhealthy, misleading,
legal, illegal, good, or bad.

## Table: `products`

One row per product (identified by barcode), sourced from Open Food Facts and
enriched by the launch-stage cleaning, brand-normalization, company-mapping,
and nutrition-quality governance layers.

**Brand interpretation note:** `primary_brand` is now a legacy
compatibility/provenance field. The current preferred app brand is
`normalized_brand` when available. Company / owner is stored separately in
`resolved_company`; manual review is a backend status, not a visible launch
company name.

**Nutrition interpretation note:** raw OFF nutrition values are preserved in
the `*_off_raw` columns. Working nutrition columns and inclusion flags support
the app and aggregate analysis, but source values should remain traceable.

| Column | Type | Description |
|---|---|---|
| `barcode` | TEXT (primary key) | Product barcode (GTIN/EAN), the unique product identifier across all tables. |
| `product_name` | TEXT | Product name as recorded in Open Food Facts. |
| `brands` | TEXT | Raw brand string from Open Food Facts; may contain multiple comma-separated values (e.g. parent brand and sub-brand) exactly as entered by contributors. |
| `primary_brand` | TEXT | Legacy compatibility/provenance brand field retained for older dependencies. It should not be treated as the preferred launch brand when `normalized_brand` is available. |
| `off_brands_raw` | TEXT | Raw OFF brand evidence copied from `brands` before brand-entity extraction and alias normalization. |
| `off_brand_tokens` | TEXT | Parsed OFF brand tokens used for brand-entity extraction and audit. |
| `legacy_primary_brand` | TEXT | The previous first-token brand interpretation preserved for traceability and comparison with the new brand layer. |
| `brand_entity_raw` | TEXT | Conservative consumer-facing brand entity selected before alias normalization. May come from OFF brand tokens, curated private-label mapping, top-company portfolio evidence, or controlled product-name recovery where explicitly approved. |
| `brand_entity_source` | TEXT | Source/rule that selected `brand_entity_raw`, such as OFF-token fallback, curated Carrefour private-label mapping, mapped brand token, or controlled Nestlé product-name recovery. |
| `normalized_brand` | TEXT | Preferred launch brand used by Streamlit where available. This is the cleaned consumer-facing brand or stable brand line after alias normalization; it is separate from parent-company ownership. |
| `brand_family` | TEXT | Broader brand umbrella where useful for analysis, while keeping `normalized_brand` specific. Example: `Cadbury Dairy Milk` can have `brand_family = Cadbury`. |
| `brand_alias_source` | TEXT | Source/rule for the alias-normalization decision, such as curated mechanical alias, top-company portfolio alias, curated Carrefour mapping, or fallback/no alias. |
| `brand_alias_review_status` | TEXT | Review status for the alias-normalization decision, for example confirmed, manual-review, or unresolved depending on the relevant rule output. |
| `resolved_company` | TEXT | Launch company / owner value used for Streamlit company filtering. This is a directional reporting owner, not a legal ownership guarantee. Unresolved launch rows should use a neutral value such as `Other / not mapped to a company`, not visible `Manual review`. |
| `company_ownership_resolution_status` | TEXT | Backend ownership-routing status, such as `direct`, `market_scoped`, `licensed_or_partnered`, `recently_changed_market_scoped`, `mapped_from_manual_review_replacement`, or `manual_review`. This field preserves audit nuance even when the visible company is not `Manual review`. |
| `company_mapping_source` | TEXT | Source/rule for the company mapping, such as reference mapping, top-company portfolio routing, manual-review replacement proposal, or no mapping match. |
| `quantity` | TEXT | Pack size / quantity as recorded in Open Food Facts (e.g. "500g", "1.15L"). European decimal commas are normalized to periods. |
| `packaging` | TEXT | Packaging material/type as recorded in Open Food Facts. |
| `query_category` | TEXT | The category used when this product was retrieved from Open Food Facts during data collection (e.g. snacks, beverages, cereals). |
| `off_categories` | TEXT | The full, raw category string as recorded in Open Food Facts, often containing multiple nested category tags. Used to refine `query_category`. |
| `countries` | TEXT | Pipe-separated list of country tags as recorded in Open Food Facts. |
| `primary_country` | TEXT | The first country extracted from `countries`. Reflects where the product was recorded in Open Food Facts, not necessarily where it is sold (see `docs/LIMITATIONS.md`). |
| `observed_market_region_codes` | TEXT | Pipe-separated market-region codes derived from OFF country tags and `data/country_region_mapping.csv`. Used by Streamlit region filters and market-scoped ownership logic. |
| `labels` | TEXT | Pipe-separated list of label/certification tags as recorded in Open Food Facts (e.g. organic, fair trade). |
| `ingredients_text` | TEXT | Raw ingredients list as recorded in Open Food Facts, used as input for ingredient-based analysis. |
| `additives_tags` | TEXT | Pipe-separated list of E-number additive tags, pre-parsed by Open Food Facts. |
| `energy_kcal` | REAL | Working energy per 100g (or 100ml for liquids), in kilocalories, used by the app and analysis after launch-stage cleaning/governance. See `energy_kcal_off_raw` for the preserved raw OFF value. |
| `fat_100g` | REAL | Working total fat per 100g/100ml. See `fat_100g_off_raw` for the preserved raw OFF value. |
| `saturated_fat_100g` | REAL | Working saturated fat per 100g/100ml. See `saturated_fat_100g_off_raw` for the preserved raw OFF value. |
| `carbs_100g` | REAL | Working total carbohydrates per 100g/100ml. See `carbs_100g_off_raw` for the preserved raw OFF value. |
| `sugars_100g` | REAL | Working sugars per 100g/100ml (subset of total carbohydrates). See `sugars_100g_off_raw` for the preserved raw OFF value. |
| `fiber_100g` | REAL | Working fibre per 100g/100ml. Fibre is often missing in source data because labelling rules differ by market. See `fiber_100g_off_raw` for the preserved raw OFF value. |
| `protein_100g` | REAL | Working protein per 100g/100ml. See `protein_100g_off_raw` for the preserved raw OFF value. |
| `salt_100g` | REAL | Working salt per 100g/100ml. See `salt_100g_off_raw` for the preserved raw OFF value. |
| `nutriscore_grade` | TEXT (A–E) | Nutri-Score letter grade as recorded in Open Food Facts, where available. The scale runs A to E, summarizing nutrition profile under the Nutri-Score system; it is a reference signal only and does not represent a product recommendation. |
| `nova_group` | REAL (1–4) | NOVA processing classification as recorded in Open Food Facts. 1 = unprocessed/minimally processed, 4 = ultra-processed. A reference classification, not a standalone verdict. |
| `completeness_score` | INTEGER (0–100) | Data-quality indicator: the percentage of eleven key fields (product name, brands, ingredients text, six nutrition values, Nutri-Score, NOVA group) that are populated for this product. Calculated as `round(filled_fields / 11 * 100)`. Reflects completeness of the source record, not the quality of the product itself. |
| `ingredients_lang` | TEXT (enum) | Detected language of `ingredients_text`: `EN`, `FR`, `BOTH` (bilingual packaging), `OTHER` (a different language, still retained), or `UNKNOWN` (text too short to classify). Keyword-based detection, not a language-ID model. |
| `ingredient_analysis_eligible` | INTEGER (1/0) | Whether this product's ingredient text is eligible for ingredient-based analysis (true for `EN`, `FR`, `BOTH`). Products in `OTHER`/`UNKNOWN` retain full nutrition data but are excluded from ingredient-marker analysis to avoid silent false negatives from an English/French-only dictionary. |
| `created_t` | TEXT | Product creation timestamp in Open Food Facts, converted from Unix time. |
| `last_modified_t` | TEXT | Last modification timestamp in Open Food Facts, converted from Unix time. Used to identify products to re-pull on incremental updates. |
| `ingested_at` | TEXT | When this row was loaded into this database. |
| `image_url` | TEXT | Front-of-pack image URL from Open Food Facts. A placeholder value containing `/invalid/` indicates no real image is available; such rows are excluded before image-based analysis. |
| `energy_kcal_off_raw` | REAL | Raw OFF energy value before nutrition-quality governance handling. |
| `fat_100g_off_raw` | REAL | Raw OFF total fat value before nutrition-quality governance handling. |
| `saturated_fat_100g_off_raw` | REAL | Raw OFF saturated fat value before nutrition-quality governance handling. |
| `carbs_100g_off_raw` | REAL | Raw OFF carbohydrate value before nutrition-quality governance handling. |
| `sugars_100g_off_raw` | REAL | Raw OFF sugars value before nutrition-quality governance handling. |
| `fiber_100g_off_raw` | REAL | Raw OFF fibre value before nutrition-quality governance handling. |
| `protein_100g_off_raw` | REAL | Raw OFF protein value before nutrition-quality governance handling. |
| `salt_100g_off_raw` | REAL | Raw OFF salt value before nutrition-quality governance handling. |
| `nutrition_quality_status` | TEXT | Launch nutrition-quality status, such as `valid`, `data_quality_error`, `energy_macro_inconsistency`, `genuine_outlier`, `category_scope_outlier`, or `manual_review`. |
| `outlier_type` | TEXT | Optional grouped outlier type used for audit and downstream filtering. |
| `include_in_product_table` | INTEGER (1/0) | Whether the product should be visible in product-level tables/Product Explorer. Hard data-quality errors are excluded; imperfect but useful records can remain visible. |
| `include_in_aggregates` | INTEGER (1/0) | Whether the record is eligible for Market Overview aggregate calculations. Records with hard data-quality errors, material energy-macro inconsistency, or approved aggregate-exclusion outlier rules are excluded. |
| `include_in_charts` | INTEGER (1/0) | Whether the record is eligible for Market Overview charts. This may be stricter than product-level visibility to avoid chart distortion. |
| `nutrition_quality_reason` | TEXT | Semicolon-separated or rule-style reasons for the nutrition-quality status and inclusion flags. |
| `energy_kcal_missing` | INTEGER (1/0) | Whether the source/working energy value is missing. Missing is not zero. |
| `fat_100g_missing` | INTEGER (1/0) | Whether total fat is missing. Missing is not zero. |
| `saturated_fat_100g_missing` | INTEGER (1/0) | Whether saturated fat is missing. Missing is not zero. |
| `carbs_100g_missing` | INTEGER (1/0) | Whether carbohydrates are missing. Missing is not zero. |
| `sugars_100g_missing` | INTEGER (1/0) | Whether sugars are missing. Missing is not zero. |
| `fiber_100g_missing` | INTEGER (1/0) | Whether fibre is missing. Missing is not zero. |
| `protein_100g_missing` | INTEGER (1/0) | Whether protein is missing. Missing is not zero. |
| `salt_100g_missing` | INTEGER (1/0) | Whether salt is missing. Missing is not zero. |

**Derived Streamlit/audit field:** `beverage_view_segment` is not part of the
`products` table DDL. It is derived for beverage Market Overview filtering and
audit outputs to separate ready-to-drink beverages from beverage preparations /
alcohol and unknown beverage segments.

## Table: `product_analysis`

One row per product (joined to `products` on `barcode`), containing all
ingredient-based, claim, and benchmark analysis. This table was previously
named `nlp_results`; the new name better reflects that it now holds both
text-based and image-based analysis, not only NLP output. A row may exist
with mostly empty fields if a product has not yet been through analysis.

**Null-interpretation note:** `product_analysis` declares its full schema
upfront, but fields are populated in stages. Ingredient-stage fields are
populated by `analyze.py`; pack-image metadata and legacy/internal composite
fields are populated by `merge_scores.py`; claim taxonomy and benchmark fields
are populated by `tag_claims.py`. A null value in a later-stage field may mean
that pipeline step has not run yet, or that the product was not selected for
that stage of analysis — not necessarily that the product has no such signal.
Use `release_run_id`, `pack_analysis_attempted`, `claim_source`, and
`pack_claims_found` together when checking claim coverage.

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
| `processing_marker_count` | INTEGER | Count of distinct ingredient-processing marker categories detected in `ingredients_text` (one count per category, even if multiple keyword variants for that category appear). |
| `processing_markers_found` | TEXT | Pipe-separated list of the specific marker categories detected (e.g. `emulsifier`, `glucose_syrup`, `artificial_sweetener`). |
| `processing_marker_max_severity` | INTEGER (0–3) | The highest severity weight among detected markers for this product. |
| `has_processing_markers` | INTEGER (1/0) | Whether at least one processing-related marker was detected. |
| `e_number_count` | INTEGER | Count of distinct flagged E-numbers detected in `additives_tags`. |
| `e_numbers_found` | TEXT | Pipe-separated list of the specific E-numbers detected. |
| `has_artificial_sweetener` | INTEGER (1/0) | Whether an artificial sweetener was detected, via either `additives_tags` or ingredient-text keywords. |
| `composition_marker_score` | REAL (0–40) | Legacy/internal score summarizing ingredient-processing markers, calculated as the capped, severity-weighted sum of unique marker categories detected: each of roughly sixty known markers (sweeteners, emulsifiers, preservatives, glucose syrups, modified starches, artificial colours, and similar) carries a pre-assigned severity of 1, 2, or 3; at most one marker counts per category even if several keyword variants appear; the score is `min(40, 3 × sum of severities of unique categories detected)`. Example: three detected categories at severities 1, 2, and 3 sum to 6, giving a score of 18. This is a composition-only internal signal: it does not reference any pack claim, does not assess healthiness, and is not displayed as a user-facing proprietary score in the current Streamlit MVP. |
| `composition_marker_band` | TEXT (enum) | Categorical band for the legacy/internal `composition_marker_score`: `Extensive markers` (≥30), `Moderate markers` (≥20), `Limited markers` (≥10), `Minimal markers` (<10). Stored as text in the database; values should be updated if this band scale changes. |

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
claim extraction — a subset of the full product table. The current US/UK and
France analytical releases contain 17,127 valid front-of-pack observations,
drawn from sampled, image-eligible Open Food Facts products. See
`docs/CLAIM_EXTRACTION.md` for the sampling design, prompt history, release
IDs, and extraction limitations. All fields in this section are declared in
the schema upfront but populated by `merge_scores.py`, not by `analyze.py`.

| Column | Type | Description |
|---|---|---|
| `pack_analysis_attempted` | INTEGER (1/0) | Whether this product was submitted for image-based claim extraction, regardless of outcome. Pair with `release_run_id`, `claim_source`, and `pack_claims_found` when interpreting coverage. |
| `ocr_text` | TEXT | Raw text extracted from the front-of-pack image by OCR. Used for auditability, prompt evaluation, and error analysis. Null for products without a usable image or where OCR failed. |
| `ocr_status` | TEXT | Status of the OCR step (e.g. success, no usable image, OCR failure, insufficient readable text). Exact values follow the vision pipeline implementation in `vision_extract.py`. |
| `llm_status` | TEXT | Status of the LLM claim-extraction step (e.g. success, parsing failure, empty output, skipped because OCR was unavailable). Exact values follow the vision pipeline implementation. |
| `vision_model` | TEXT | Model or deployment used for pack-image claim extraction (e.g. `gpt-4.1-nano`). Recorded for reproducibility, cost review, and prompt/model calibration — see `docs/CLAIM_EXTRACTION.md`, `docs/METHODOLOGY.md`, and `docs/ADR.md`. |
| `prompt_version` | TEXT | Version identifier for the prompt/extraction schema used during LLM claim extraction. Avoids mixing outputs from incompatible extraction logic when prompts are revised. |
| `pack_analysis_timestamp` | TEXT | When pack-image analysis was performed or merged into the database. Distinct from `analyzed_at`, which reflects the most recent write to the row from any pipeline stage. |
| `pack_claims_found` | TEXT | Front-pack claim observation state. `NULL` means no valid pack observation exists (not analyzed, non-front image, or extraction failure). `""` means a valid front pack was assessed and no taxonomy claim was found. A pipe-separated string (e.g. `protein_claim|vegan_claim`) contains claims identified directly from front-pack OCR/LLM extraction. Only `NULL` should trigger ingredient/name fallback in claim taxonomy; `""` is a true no-claim observation. |

### Legacy/internal positioning-to-composition fields

| Column | Type | Description |
|---|---|---|
| `positioning_composition_gap` | REAL (0–100) | Legacy/internal composite score combining `composition_marker_score` (Component A, 0–40, applies regardless of whether any claim is present) with a claim-weight component (Component B, 0–30, zero if no claims) and a processing/Nutri-Score context component (Component C, 0–30, only triggered if Component B is above zero). Despite the name, this is not a pure "claim vs composition" gap: a product with zero pack claims but a severe ingredient profile can still score up to 40. Retained for historical/internal compatibility and not displayed as a user-facing proprietary score in the current Streamlit MVP. Populated by `merge_scores.py`. |
| `positioning_composition_gap_band` | TEXT (enum) | Categorical band for the legacy/internal `positioning_composition_gap`: `High positioning-composition signal` (≥70), `Moderate positioning-composition signal` (≥45), `Low positioning-composition signal` (≥20), `Minimal positioning-composition signal` (<20). Labels describe composite-signal strength, not a claim-vs-composition comparison. Stored as text in the database. Populated by `merge_scores.py`. |

### Claim taxonomy (two-cut classification)

| Column | Type | Description |
|---|---|---|
| `claim_category_1` | TEXT (enum) | Broad claim category: `FUNCTIONAL` (claims of having or doing something — protein, fibre, vitamins, gut health, immune support, energy); `FREE_OF` (claims of not having something, or having reduced amounts — no added sugar, gluten-free, dairy-free, vegan, plant-based, no artificial ingredients, no palm oil); `NATURAL_ORGANIC` (organic, natural, clean-label, minimal-ingredient, or origin/naturalness claims); `OTHER` (heritage, comparative, sustainability, artisan, weight-management positioning); `NO_CLAIM` (no claim identified). Vegan and plant-based claims are classified under `FREE_OF` since they typically function as absence/substitution claims (free from animal-derived ingredients); this can be revisited if a dedicated lifestyle-claim category is needed later. Stores the enum code only — see `docs/UI_LABELS.md` for display labels used in `app.py`. Reflects the single highest-priority category present, not a complete count of every claim territory on pack — use `pack_claims_found` for that when `claim_source = vision`. Populated by `tag_claims.py`. |
| `claim_category_2` | TEXT (enum) | A more specific sub-category within `claim_category_1` (e.g. `protein`, `gut_health`, `no_added_x`, `free_from`, `natural`, `organic`, `heritage`, `comparative`). Populated by `tag_claims.py`. |
| `claim_source` | TEXT (enum) | Indicates the evidence layer used for claim taxonomy classification. Values: `vision` when a valid front-pack claim observation is available; `ingredient_text_only` when classification relies on product name, labels, or ingredient/name-derived signals because no valid pack observation exists. Fallback-derived classifications are weaker evidence and must not be displayed as front-pack observations. Pair with `release_run_id`, `pack_analysis_attempted`, and `pack_claims_found` to distinguish "never analyzed", "non-front/failed", "front assessed with no claims", and "front assessed with claims". Populated by `tag_claims.py`. |

### Benchmark flags and intersections

| Column | Type | Description |
|---|---|---|
| `nutrition_benchmark_flags` | TEXT | Pipe-separated list of neutral codes (`sugar_above_reference`, `saturated_fat_above_reference`, `fat_above_reference`, `salt_above_reference`) for nutrients whose declared per-100g/100ml value exceeds a reference threshold. Stores codes, not display text — see `docs/UI_LABELS.md` for the code-to-label mapping used by `app.py`. Thresholds follow the UK Food Standards Agency's front-of-pack labelling guidance and are used here as a single reference scheme for cross-product comparison. The EU's mandatory nutrition declaration, Regulation 1169/2011, requires these nutrient values to be stated on pack but does not itself define high/low thresholds — that was deliberately left to individual schemes. In the MVP, liquid vs solid is approximated using an energy-density proxy (under 100 kcal/100ml treated as liquid); this may misclassify some categories and should be reviewed if benchmark flags become a central reporting layer. Computed independently of any claim; not a health verdict or legal assessment. Populated by `tag_claims.py`. |
| `claim_benchmark_intersections` | TEXT | Pipe-separated list of specific instances where detected positioning co-occurs with a relevant nutrition, ingredient, or processing benchmark signal (e.g. "Protein positioning with saturated fat above reference threshold", "Sugar-reduction positioning with sugar above reference threshold"). When valid pack claims are not available, may fall back to combined ingredient/name-derived evidence (`ingredient_based_claim_signals_found` + `absence_reduction_claims_found`); such rows should be interpreted as weaker evidence through `claim_source`. Describes co-occurrence only; does not indicate that a claim is false, illegal, or misleading. Populated by `tag_claims.py`. |

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

**Scope: this table is ingredient-stage only, not the final market-
intelligence summary.** It is computed inside `load.py`, which runs
before `merge_scores.py` and `tag_claims.py` enrich the database — so it
necessarily reflects ingredient-analysis-stage signals only (composition
markers, NOVA, ingredient-based claim signals). It does not include pack
claim distribution, claim taxonomy shares, benchmark intersection rates,
or `positioning_composition_gap`. A separate aggregation step, run after
the full pipeline completes and querying `product_analysis` directly, is
needed for the richer market-intelligence summary described in the brief.
This table is useful for early pipeline QA, not as the final Streamlit or
reporting export source. `load.py` deletes existing rows for the current day's
`week_ending` before inserting, so rerunning on the same day does not
create duplicate trend rows — for production weekly reporting, this
should instead reflect the full database snapshot, not a same-day-only
guard. See `docs/ADR.md`.

**Two changes from the prior schema, flagged for awareness:** the prior
version grouped by the raw `brands` field rather than the legacy normalized
`primary_brand`, fragmenting brand totals inconsistently with the historical
pipeline. This table now groups by `primary_brand`, but launch Streamlit views
prefer `products.normalized_brand` where available. The prior version also
included `high_score_count` (score >= 70) and `medium_score_count` (score
45-69) columns that were structurally impossible to populate, since the
underlying score is capped at 40 — these counting/bucketing columns are removed
rather than re-thresholded, since count-based buckets read as verdict-adjacent
regardless of the underlying bug.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (primary key) | Auto-incrementing row identifier. |
| `week_ending` | TEXT | ISO date marking the end of the aggregation period. |
| `primary_brand` | TEXT | Legacy normalized brand used by this early QA aggregation. For launch-facing brand views, prefer `products.normalized_brand` when available. |
| `query_category` | TEXT | Product category for this aggregation row. |
| `product_count` | INTEGER | Number of products included in this brand/category/week grouping. |
| `avg_composition_marker_score` | REAL | Average `composition_marker_score` across products in this grouping. |
| `pct_nova4` | REAL | Percentage of products in this grouping classified as NOVA group 4. |
| `pct_with_ingredient_based_claim_signals` | REAL | Percentage of products with at least one detected ingredient-based claim signal. |
| `pct_with_artificial_sweetener` | REAL | Percentage of products containing an artificial sweetener. |
| `top_ingredient_based_claim_signal` | TEXT | The most frequently detected ingredient/name-derived claim signal within this grouping, based on `ingredient_based_claim_signals_found`. Not necessarily the top front-of-pack claim — reflects the ingredient-analysis stage only and should not be used as a final claim taxonomy measure once `claim_category_1`/`claim_category_2` are available. (Renamed from `top_claim_type` for clarity.) |
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

1. **Legacy/internal composite fields remain documented because they still
exist in parts of the historical pipeline.** They are not user-facing Streamlit
MVP metrics. See `docs/METHODOLOGY.md` and `docs/LIMITATIONS.md`.
2. **`pack_analysis_attempted`, `claim_source`, and `pack_claims_found` must be
interpreted together.** The `NULL` versus `""` distinction in
`pack_claims_found` is semantically important and must be preserved when
reading or exporting CSVs.
3. **Some newer reporting/precompute tables still need a schema documentation
pass.** Known candidates include `weekly_brand_positioning_summary`,
`positioning_example_products`, `axis_range_config`,
`region_category_benchmarks`, and `profile_intersections`. Their full column
definitions should be added after inspecting the live schema and owning scripts,
not inferred here.
