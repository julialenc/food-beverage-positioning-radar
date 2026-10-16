# Column descriptions

This document describes the working database's twelve application/audit tables,
the compact deployment schema, and the separate presentation CSV evidence.
Schema and owning scripts were inspected on 2026-10-16. Grouped column families
below share a definition; they do not imply new columns or a schema migration.

The full local `database/positioning_radar.db` is the audit/build source.
Stage 17 publishes a compact database with seven tables: `products`,
`product_analysis`, `axis_range_config`, `market_chart_bands`,
`region_category_benchmarks`, `profile_intersections` and
`category_region_averages`. Its `products` table keeps selected display,
nutrition, mapping, warning and inclusion fields. Its `product_analysis` keeps
only `barcode`, `pack_claims_found` and `claim_source`; the OCR, prompt, release
and sampling metadata documented below remain in the working database.
Stage 17 selects the latest ingested product snapshot within launch scopes and
the latest precompute snapshots. Do not expect the public artifact to contain
the full audit schema or treat local counts as a live-deployment check.

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
| `query_category` | TEXT | Project category, initially assigned through OFF retrieval and subsequently subject to governed format rules and exact reviewed category overrides, including OUT_OF_SCOPE. It is not an immutable raw source category; see off_categories for source evidence. |
| `off_categories` | TEXT | The full, raw category string as recorded in Open Food Facts, often containing multiple nested category tags. Used to refine `query_category`. |
| `countries` | TEXT | Pipe-separated list of country tags as recorded in Open Food Facts. |
| `primary_country` | TEXT | The first country extracted from `countries`. Reflects where the product was recorded in Open Food Facts, not necessarily where it is sold (see `docs/03_PROJECT_REFERENCE/03_LIMITATIONS.md`). |
| `observed_market_region_codes` | TEXT | Pipe-separated market-region codes derived from OFF country tags and `data/01_reference_inputs/01_country_region_mapping.csv`. Used by Streamlit region filters and market-scoped ownership logic. |
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
| `include_in_aggregates` | INTEGER (1/0) | Compatibility/audit-history field. Current Market Overview calculations use the Product Explorer hard gate as the exclusion boundary; records that pass `include_in_product_table = 1` remain aggregate-eligible even when warning flags are present. |
| `include_in_charts` | INTEGER (1/0) | Compatibility/audit-history field. Current Product Map display starts from Product Explorer-valid records with non-null selected axes and applies selected chart-range bands; chart ranges affect visualization only. |
| `nutrition_quality_reason` | TEXT | Semicolon-separated or rule-style reasons for the nutrition-quality status and inclusion flags. |
| `warning_flag` | INTEGER (1/0) | Whether an audit warning is present after nutrition governance; a warning alone does not fail the hard gate. |
| `warning_types` | TEXT | Stored warning codes for energy-macro mismatch and/or within-brand plausibility concerns. |
| `warning_summary` | TEXT | Human-readable warning explanation for review/display; does not correct source nutrition. |
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
populated by `stage_04_build_product_analysis.py`; pack-image metadata and legacy/internal composite
fields are populated by `stage_11_merge_vision_results.py`; claim taxonomy and benchmark fields
are populated by `stage_12_build_claim_taxonomy.py`. A null value in a later-stage field may mean
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
claim extraction — a subset of the full product table. As checked on 2026-10-16,
the working database has **23,403** rows with `claim_source = 'vision'`.
This combines the original country samples with targeted private-label
enrichment; 17,127 is the historical original-release count. It is not a
representative market sample or a check of the live app. See
`docs/02_PACK_IMAGE_ANALYSIS/01_FRONT_PACK_CLAIM_EXTRACTION.md` for the sampling design, prompt history, release
IDs, and extraction limitations. All fields in this section are declared in
the schema upfront but populated by `stage_11_merge_vision_results.py`, not by `stage_04_build_product_analysis.py`.

| Column | Type | Description |
|---|---|---|
| `pack_analysis_attempted` | INTEGER (1/0) | Whether this product was submitted for image-based claim extraction, regardless of outcome. Pair with `release_run_id`, `claim_source`, and `pack_claims_found` when interpreting coverage. |
| `ocr_text` | TEXT | Raw text extracted from the front-of-pack image by OCR. Used for auditability, prompt evaluation, and error analysis. Null for products without a usable image or where OCR failed. |
| `ocr_status` | TEXT | Status of the OCR step (e.g. success, no usable image, OCR failure, insufficient readable text). Exact values follow the vision pipeline implementation in `stage_10_extract_pack_claims.py`. |
| `llm_status` | TEXT | Status of the LLM claim-extraction step (e.g. success, parsing failure, empty output, skipped because OCR was unavailable). Exact values follow the vision pipeline implementation. |
| `vision_model` | TEXT | Model or deployment used for pack-image claim extraction (e.g. `gpt-4.1-nano`). Recorded for reproducibility, cost review, and prompt/model calibration — see `docs/02_PACK_IMAGE_ANALYSIS/01_FRONT_PACK_CLAIM_EXTRACTION.md`, `docs/03_PROJECT_REFERENCE/02_METHODOLOGY.md`, and `docs/03_PROJECT_REFERENCE/01_ADR.md`. |
| `prompt_version` | TEXT | Version identifier for the prompt/extraction schema used during LLM claim extraction. Avoids mixing outputs from incompatible extraction logic when prompts are revised. |
| `pack_analysis_timestamp` | TEXT | When pack-image analysis was performed or merged into the database. Distinct from `analyzed_at`, which reflects the most recent write to the row from any pipeline stage. |
| `pack_claims_found` | TEXT | Front-pack claim observation state. `NULL` means no valid pack observation exists (not analyzed, non-front image, or extraction failure). `""` means a valid front pack was assessed and no taxonomy claim was found. A pipe-separated string (e.g. `protein_claim|vegan_claim`) contains extracted claim codes, including approved contextual text rescues for the latest UK profile. Thus not every UK code is supported by OCR text alone. Only `NULL` should trigger ingredient/name fallback in claim taxonomy; `""` is a true no-claim observation. |

### Pack context, run provenance and sampling

These working-database fields are populated through stage 11 and retained for
audit. `claim_source = vision` denotes valid stored observations, not one
specific release or a uniform prompt method.

| Column | Type | Description |
|---|---|---|
| `image_context` | TEXT | Panel classification: front_of_pack, mixed_pack_text, ingredient_or_legal_panel, nutrition_label, price_sticker or uncertain. |
| `claim_extraction_status` | TEXT | Completed, non-front, unreadable or other extraction outcome; use with OCR/LLM status to distinguish absence from failure. Stored status codes follow stage 10. |
| `detected_claim_phrases` | TEXT | Serialized phrases captured by extraction and approved rescue rules; recorded text does not itself guarantee a mapped taxonomy claim. |
| `claims_json` | TEXT | Serialized structured extraction payload retained for audit, alongside the aggregate pipe-separated claim codes. |
| `release_run_id` | TEXT | Run/release identifier used to separate historical releases and targeted retailer updates. |
| `sampling_region` | TEXT | Region assigned to the extraction sample; distinct from a product's potentially multiple observed market tags. |
| `sampling_category` | TEXT | Category assigned at sampling time; may differ from a subsequently corrected product category. |
| `sample_component` | TEXT | Original backbone/matrix/calibration component or targeted-run label. |
| `primary_stratum_id` | TEXT | Stored sampling stratum identifier; interpretation depends on the run design. |
| `sampling_weight` | REAL | Approximate design weight where defined; missing for purposive/targeted samples, not zero. |
| `weight_status` | TEXT | Explains weight availability/type, including targeted_unweighted for targeted recall inputs. |

The final UK profile combines product-name, brand and OCR text for the approved
rescue function. Inspect `prompt_version` and `release_run_id` before comparing
observations from different evidence rules. Full behavior is documented in
[the extraction guide](../02_PACK_IMAGE_ANALYSIS/01_FRONT_PACK_CLAIM_EXTRACTION.md#64-approved-ukireland-rescue-rules--september-2026).

### Legacy/internal positioning-to-composition fields

| Column | Type | Description |
|---|---|---|
| `positioning_composition_gap` | REAL (0–100) | Legacy/internal composite score combining `composition_marker_score` (Component A, 0–40, applies regardless of whether any claim is present) with a claim-weight component (Component B, 0–30, zero if no claims) and a processing/Nutri-Score context component (Component C, 0–30, only triggered if Component B is above zero). Despite the name, this is not a pure "claim vs composition" gap: a product with zero pack claims but a severe ingredient profile can still score up to 40. Retained for historical/internal compatibility and not displayed as a user-facing proprietary score in the current Streamlit MVP. Populated by `stage_11_merge_vision_results.py`. |
| `positioning_composition_gap_band` | TEXT (enum) | Categorical band for the legacy/internal `positioning_composition_gap`: `High positioning-composition signal` (≥70), `Moderate positioning-composition signal` (≥45), `Low positioning-composition signal` (≥20), `Minimal positioning-composition signal` (<20). Labels describe composite-signal strength, not a claim-vs-composition comparison. Stored as text in the database. Populated by `stage_11_merge_vision_results.py`. |

### Claim taxonomy (two-cut classification)

| Column | Type | Description |
|---|---|---|
| `claim_category_1` | TEXT (enum) | Broad claim category: `FUNCTIONAL` (claims of having or doing something — protein, fibre, vitamins, gut health, immune support, energy); `FREE_OF` (claims of not having something, or having reduced amounts — no added sugar, gluten-free, dairy-free, vegan, plant-based, no artificial ingredients, no palm oil); `NATURAL_ORGANIC` (organic, natural, clean-label, minimal-ingredient, or origin/naturalness claims); `OTHER` (heritage, comparative, sustainability, artisan, weight-management positioning); `NO_CLAIM` (no claim identified). Vegan and plant-based claims are classified under `FREE_OF` since they typically function as absence/substitution claims (free from animal-derived ingredients); this can be revisited if a dedicated lifestyle-claim category is needed later. Stores the enum code only — see `docs/02_PACK_IMAGE_ANALYSIS/02_CLAIM_TAXONOMY_LABELS.md` for display labels used in `app.py`. Reflects the single highest-priority category present, not a complete count of every claim territory on pack — use `pack_claims_found` for that when `claim_source = vision`. Populated by `stage_12_build_claim_taxonomy.py`. |
| `claim_category_2` | TEXT (enum) | A more specific sub-category within `claim_category_1` (e.g. `protein`, `gut_health`, `no_added_x`, `free_from`, `natural`, `organic`, `heritage`, `comparative`). Populated by `stage_12_build_claim_taxonomy.py`. |
| `claim_source` | TEXT (enum) | Indicates the evidence layer used for claim taxonomy classification. Values: `vision` when a valid front-pack claim observation is available; `ingredient_text_only` when classification relies on product name, labels, or ingredient/name-derived signals because no valid pack observation exists. Fallback-derived classifications are weaker evidence and must not be displayed as front-pack observations. Pair with `release_run_id`, `pack_analysis_attempted`, and `pack_claims_found` to distinguish "never analyzed", "non-front/failed", "front assessed with no claims", and "front assessed with claims". Populated by `stage_12_build_claim_taxonomy.py`. |

### Benchmark flags and intersections

| Column | Type | Description |
|---|---|---|
| `nutrition_benchmark_flags` | TEXT | Pipe-separated list of neutral codes (`sugar_above_reference`, `saturated_fat_above_reference`, `fat_above_reference`, `salt_above_reference`) for nutrients whose declared per-100g/100ml value exceeds a reference threshold. Stores codes, not display text — see `docs/02_PACK_IMAGE_ANALYSIS/02_CLAIM_TAXONOMY_LABELS.md` for the code-to-label mapping used by `app.py`. Thresholds follow the UK Food Standards Agency's front-of-pack labelling guidance and are used here as a single reference scheme for cross-product comparison. The EU's mandatory nutrition declaration, Regulation 1169/2011, requires these nutrient values to be stated on pack but does not itself define high/low thresholds — that was deliberately left to individual schemes. In the MVP, liquid vs solid is approximated using an energy-density proxy (under 100 kcal/100ml treated as liquid); this may misclassify some categories and should be reviewed if benchmark flags become a central reporting layer. Computed independently of any claim; not a health verdict or legal assessment. Populated by `stage_12_build_claim_taxonomy.py`. |
| `claim_benchmark_intersections` | TEXT | Pipe-separated list of specific instances where detected positioning co-occurs with a relevant nutrition, ingredient, or processing benchmark signal (e.g. "Protein positioning with saturated fat above reference threshold", "Sugar-reduction positioning with sugar above reference threshold"). When valid pack claims are not available, may fall back to combined ingredient/name-derived evidence (`ingredient_based_claim_signals_found` + `absence_reduction_claims_found`); such rows should be interpreted as weaker evidence through `claim_source`. Describes co-occurrence only; does not indicate that a claim is false, illegal, or misleading. Populated by `stage_12_build_claim_taxonomy.py`. |

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
intelligence summary.** It is computed inside `stage_05_load_database.py`, which runs
before `stage_11_merge_vision_results.py` and `stage_12_build_claim_taxonomy.py` enrich the database — so it
necessarily reflects ingredient-analysis-stage signals only (composition
markers, NOVA, ingredient-based claim signals). It does not include pack
claim distribution, claim taxonomy shares, benchmark intersection rates,
or `positioning_composition_gap`. Stage 13 already supplies the separate
`weekly_brand_positioning_summary` after enrichment, as documented below.
This table is useful for early pipeline QA, not as the final Streamlit or
reporting export source. `stage_05_load_database.py` deletes existing rows for the current day's
`week_ending` before inserting, so rerunning on the same day does not
create duplicate trend rows — for production weekly reporting, this
should instead reflect the full database snapshot, not a same-day-only
guard. See `docs/03_PROJECT_REFERENCE/01_ADR.md`.

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

## Reporting and precompute tables

These tables have different populations and denominators. Their names do not
make them substitutes for the frozen private-label CSVs or the current
Market Overview query population. The following describes the stored output
and implementation, without changing the locked governance rules.

### `weekly_brand_positioning_summary`

Owner: `pipeline/stages/stage_13_build_app_summaries.py`. Grain:
`week_ending` + `source_scope` + `primary_brand` + `query_category`, with
`id` (INTEGER) and `run_timestamp` (TEXT). Replaces that period/scope on rerun.
Brand keys here are legacy `primary_brand`, not necessarily the preferred
`normalized_brand`.

| Columns | Type | Meaning / denominator |
|---|---|---|
| `product_count` | INTEGER | Products in the brand/category group. |
| `pack_analyzed_count`, `pct_pack_analyzed` | INTEGER, REAL | Count where pack_analysis_attempted=1 and percentage of product_count. This is an attempted-analysis denominator, not automatically valid completed packs. |
| `pct_with_pack_claims`, `pct_with_pack_claims_among_analyzed` | REAL | Nonempty pack-claim records divided by product_count or pack_analyzed_count, respectively. Not interchangeable with presentation claim incidence. |
| `positioning_gap_scored_count`, `pct_positioning_gap_scored` | INTEGER, REAL | Non-null legacy gap values; coverage share of product_count. |
| `claim_tagged_count`, `pct_claim_tagged` | INTEGER, REAL | Non-null claim_category_1 values; coverage share of product_count. |
| `pct_functional`, `pct_free_of`, `pct_natural_organic`, `pct_other_claim`, `pct_no_claim` | REAL | Highest-priority category shares among all group products, potentially including ingredient/name fallback. Not multi-territory shares among claim-bearing packs. |
| `top_claim_category_1`, `top_claim_category_2` | TEXT | Most frequent category, including the no-claim/none category. |
| `top_detected_claim_category_1`, `top_detected_claim_category_2` | TEXT | Most frequent non-null category excluding NO_CLAIM/none. |
| `avg_composition_marker_score`, `avg_positioning_composition_gap` | REAL | Means over available legacy/internal scores; missing scores are excluded. |
| `pct_nova4`, `pct_with_artificial_sweetener` | REAL | Records meeting the stored signal divided by product_count. |
| `pct_with_nutrition_benchmark_flags`, `pct_with_claim_benchmark_intersections` | REAL | Records with nonempty fields divided by product_count. |
| `pct_sugar_above_reference`, `pct_saturated_fat_above_reference`, `pct_fat_above_reference`, `pct_salt_above_reference` | REAL | Records carrying the indicated benchmark flag divided by product_count. |

### `positioning_example_products`

Owner: stage 13. Replaced on each run; a product may have several
`selection_reason` rows. `id` is INTEGER, `barcode` and `selection_reason` are
TEXT, and `run_timestamp` is TEXT. Selection is illustrative, not ranking.

Copied TEXT fields: `product_name`, `primary_brand`, `query_category`,
`claim_category_1`, `claim_category_2`, `pack_claims_found`,
`nutrition_benchmark_flags`, `claim_benchmark_intersections`,
`nutriscore_grade`, `image_url`. Copied REAL fields:
`positioning_composition_gap`, `composition_marker_score`, `nova_group`.
They retain the product/analysis meanings above. This working-table history
is not part of the compact deployment schema.

### `market_trend_weekly`

Owner: stage 13; DDL also declared by stage 05. Grain: `week_ending` and
`query_category`, replaced for that period on rerun; `id` INTEGER and
`run_timestamp` TEXT. It describes a changing database snapshot, not sales
trends, launches or an effect of any treatment.

| Columns | Type | Meaning / denominator |
|---|---|---|
| `product_count` | INTEGER | Category records in the reporting input. |
| `new_product_count` | INTEGER | Records whose created_t can be parsed as a numeric Unix timestamp within 90 days; not a verified product-launch count. Unparseable dates do not count. |
| `pack_analyzed_count`, `pct_pack_analyzed` | INTEGER, REAL | Attempted pack analyses and their share of product_count. |
| `avg_protein_per_kcal` | REAL | Mean protein grams per 100 kcal over non-null protein and positive energy. |
| `pct_high_protein` | REAL | Records with protein_100g >=20 divided by product_count; an internal threshold, not legal claim eligibility. |
| `avg_fiber_per_carb`, `avg_sugar_per_carb` | REAL | Mean fibre/carbohydrate and sugar/carbohydrate ratios over available values with positive carbohydrates. |
| `pct_nova1`, `pct_nova2`, `pct_nova3`, `pct_nova4` | REAL | NOVA group counts divided by all product_count, including records missing NOVA in that denominator. |
| `nova4_to_nova1_ratio` | REAL | NOVA 4 count / NOVA 1 count; null when NOVA 1 count is zero. |
| `median_pack_size_g` | REAL | Median recognized g/kg pack weight, kg converted to g; volume units omitted. |
| `pct_functional_claims`, `pct_free_of_claims`, `pct_natural_organic_claims`, `pct_no_claim` | REAL | Highest-priority taxonomy shares among product_count, potentially including fallback evidence. |
| `avg_additives_count`, `pct_with_additives` | REAL | Mean count of pipe-separated OFF additive tags and share with tags. The implementation fills missing tags with empty strings, so these measure recorded tag coverage, not confirmed additive absence. |

### `category_region_averages`

Owner: `stage_05_load_database.py::compute_category_region_averages`.
Key fields `snapshot`, `query_category` and `region` are TEXT.
`energy_kcal`, `protein_per_kcal`, `fiber_per_kcal`, `satfat_per_kcal`,
`sugars_per_kcal`, `sugars_100g` and `salt_100g` are REAL means over available
values, requiring at least ten values per metric. Ratio fields are grams per
100 kcal despite their names.

This Product Explorer cache is built from the stage input with usable brand and
positive energy. Region is derived from `primary_country`, with OTHER and ALL
groups. It is not the same population/statistic as the region-tag-based medians
below or the private-label CSV. Missing metric values are omitted.

### `region_category_benchmarks`

Owner: stage 14. `id` INTEGER; `snapshot`, `region_code`, `category`,
`computed_at` TEXT; `product_count` INTEGER. Uses latest ingested records,
usable legacy brand, product-table and aggregate inclusion flags, and observed
region tags. Each metric also has hard-validity and non-null checks.

| Column families | Type | Meaning |
|---|---|---|
| `energy_median`, `energy_p25`, `energy_p75`, `energy_valid_n` | REAL statistics, INTEGER count | Energy kcal per 100g/100ml median and quartiles, plus valid observations. |
| `protein_eff_*`, `fibre_eff_*`, `satfat_eff_*`, `sugars_eff_*` | REAL statistics, INTEGER valid_n | Nutrient grams per 100 kcal; suffixes median, p25, p75, valid_n. Positive energy required. |
| `protein_ml_*`, `fibre_ml_*`, `satfat_ml_*`, `sugars_ml_*` | REAL statistics, INTEGER valid_n | Raw nutrient values per 100g/100ml; stable beverage comparison without dividing by energy. Same four suffixes. |
| `nova_classified_n`, `nova4_n`, `nova4_pct` | INTEGER, INTEGER, REAL | Valid NOVA 1–4 base, NOVA 4 count and share of that classified base. |

Statistics are null below ten valid metric values; valid_n remains recorded.
These precomputed medians are not the separately retained presentation
baseline. Current Market Overview treatment is defined in nutrition governance.

### `profile_intersections`

Owner: stage 15, after stage 14. `id` INTEGER; `snapshot`, `region_code`,
`category`, `full_subset_key`, `sub_collection_key`, `computed_at` TEXT.
`eligible_count` and `matching_count` are INTEGER.

The full key identifies the complete selected profile dimensions; the
sub-collection identifies a subset of those conditions. All steps use the
same population valid on every dimension in the full profile. Matching counts
satisfy the subset within that eligible base; benchmark conditions read stage
14 medians. These are composition-profile intersections, distinct from
product_analysis.claim_benchmark_intersections and future product segmentation.

### `axis_range_config` and `market_chart_bands`

Owner: stage 16. Both have `id` INTEGER and TEXT `snapshot`, `region_code`,
`category`, `beverage_view_segment` and `computed_at`. Include the segment
in joins; one barcode can occur in multiple market scopes.

| Table / columns | Type | Meaning |
|---|---|---|
| axis_range_config: `metric_key` | TEXT | Axis metric identifier. |
| `hard_min`, `hard_max` | REAL | Metric plausibility bounds used in range computation. |
| `p03`, `p97` | REAL | Current central-range display cutoffs. |
| `p99_5`, `display_max` | REAL | Retained upper-tail/legacy display diagnostics; not the current central-range policy. |
| `n_valid`, `n_flagged_invalid` | INTEGER | Valid metric values and non-null values outside metric bounds. |
| `n_ratio_unstable` | INTEGER | Valid ratio values flagged by the low-energy diagnostic. |
| `n_below_p03`, `n_above_p97`, `n_trimmed` | INTEGER | Below/above central cutoffs and their sum; display counts, not aggregate exclusions. |
| `n_outside_display_range` | INTEGER | Values above the stored display_max diagnostic. |
| market_chart_bands: `barcode` | TEXT | Product identity within the full scope key. |
| `energy_chart_band`, `protein_chart_band`, `fat_chart_band`, `saturated_fat_chart_band`, `carbs_chart_band`, `sugars_chart_band`, `fiber_chart_band`, `salt_chart_band` | TEXT | Precomputed chart-band assignments for raw axes. |
| `protein_per_kcal_chart_band`, `satfat_per_kcal_chart_band`, `fiber_per_kcal_chart_band`, `sugars_per_kcal_chart_band` | TEXT | Equivalent assignments for energy-normalized axes. |

Chart bands control drawing only. They do not change the hard-gate population
used for Market Overview calculations. See
[the locked nutrition governance](../01_PRODUCT_DATA_GOVERNANCE/03_NUTRITION_QUALITY_GOVERNANCE.md).

## Standalone presentation CSV evidence

These files live under `presentations/private_label_analysis/` and are not
Streamlit table inputs. See [the evidence guide](../../presentations/private_label_analysis/README.md)
for file locations and [the methodology](02_METHODOLOGY.md#private-label-analysis)
for interpretation.

| File / columns | Meaning |
|---|---|
| nutrition_values_vs_market_median_all_retailers.csv: `scope`, `region`, `category`, `company`, `brand`, `product` | Region/category and retailer scope identifiers; ALL_BRANDS / CATEGORY_MEDIAN indicate aggregated company rows. |
| `energy_kcal_per_100g`, `protein_per_100g`, `fat_per_100g`, `saturated_fat_per_100g`, `carbohydrates_per_100g`, `sugars_per_100g`, `fiber_per_100g` | Category nutrient medians in source per-100g/100ml units, not means of brand medians. |
| `NOVA`, `Nutriscore` | Text distributions of recorded classifications, not medians. |
| Claims check: `claim_codes_counted`, `numerator_products_with_territory` | Explicit code union and territory-bearing product count. Territories can overlap. |
| `denominator_claimed_products` / UK `denominator_claimed_products_requested` | Claim-bearing analyzed base, used by corresponding pct_among_claimed_products columns (with requested in UK names). |
| `denominator_analyzed_products_including_no_claim` | All analyzed packs, including confirmed no-claim observations; corresponding percentage columns use this base. |
| Claims summary: `total_products`, `analyzed_products_including_no_claim`, `claimed_products_denominator` (UK: suffix _requested), `no_claim_identified_products` | Coverage and claim-incidence bases; analyzed = claimed + confirmed no-claim. |
| `claim_detection_rate_among_analyzed_pct` | Claim-bearing / analyzed, multiplied by 100. |
| Slide comparison fields | Retained PDF percentage, percentage-point difference and/or rounded denominator match; presence and naming vary by analysis. UK comparison preserves the all-analyzed slide base alongside the requested claim-bearing view. |

The Aldi/Lidl check additionally separates `code_only_numerator_products_with_territory`,
`reviewed_context_additions` and the reviewed numerator, with reviewed GTINs,
rules version, input/review/PDF hashes and PDF differences. Its summary includes
not-analyzed counts and original-tag stacking, with regional and pooled
`ALL_REGIONS_RECORDS` scopes. The [Aldi/Lidl guide](../../presentations/private_label_analysis/aldi_lidl/README.md)
defines rounding, zero denominators, territory rules and snapshot provenance.
Do not silently standardize historical column names or denominators.
