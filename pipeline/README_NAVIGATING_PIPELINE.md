```text
pipeline/ # Production pipeline code, governance utilities, validation checks, prompts, and exports
|-- __init__.py # Package marker for pipeline imports
|-- README_NAVIGATING_PIPELINE.md # Tree map of pipeline folders and files
|-- rules/ # Shared rules imported by pipeline stages and checks
|   |-- __init__.py # Package marker for rules imports
|   `-- category_rules.py # Category query, inclusion, exclusion, and cleanup rules
|-- stages/ # Ordered backbone scripts for building the product dataset, app tables, and deployment database
|   |-- __init__.py # Package marker for stage imports
|   |-- stage_01a_bootstrap_from_off_bulk.py # Bulk one-off download from Open Food Facts zip files
|   |-- stage_01b_ingest_from_off_api.py # Ongoing download from Open Food Facts via API
|   |-- stage_02_clean_products.py # Clean raw OFF data into analysis-ready product records
|   |-- stage_03_build_nutrition_quality_flags.py # Build nutrition-quality flags and audit outputs
|   |-- stage_04_build_product_analysis.py # Compute derived nutrition, category, brand, and positioning fields
|   |-- stage_05_load_database.py # Load processed product data into the project SQLite database
|   |-- stage_06_detect_sampling_signals.py # Detect candidate positioning signals for pack-image sampling outputs
|   |-- stage_07_assign_sampling_bands.py # Assign sampling bands used to balance the vision sample
|   |-- stage_08_classify_formulation_families.py # Classify products into formulation families for sampling outputs
|   |-- stage_09_build_vision_sample.py # Build the targeted product sample in data/04_vision_sampling
|   |-- stage_10_extract_pack_claims.py # Run OCR and LLM extraction on selected pack-image sample files
|   |-- stage_11_merge_vision_results.py # Merge extracted pack-image results back into product analysis
|   |-- stage_12_build_claim_taxonomy.py # Convert extracted signals into claim tags and benchmark fields
|   |-- stage_13_build_app_summaries.py # Build app-facing summary tables and example-product records
|   |-- stage_14_compute_region_benchmarks.py # Compute region/category benchmark tables
|   |-- stage_15_compute_profile_intersections.py # Compute intersections between product profiles and benchmarks
|   |-- stage_16_build_chart_ranges.py # Compute chart axis ranges and Market Overview display bands
|   `-- stage_17_build_deployment_database.py # Build the trimmed SQLite database used for deployment
|-- validation/ # Checks and manual review samplers that guard production runs
|   |-- __init__.py # Package marker for validation imports
|   |-- check_01_category_rules.py # Validate category assignment rules before bootstrap or ingest
|   |-- check_02_nutrition_quality.py # Validate nutrition-quality flag logic
|   |-- check_03_beverage_segments.py # Validate beverage segmentation rules
|   |-- check_04_schema.py # Compare live SQLite schema against current pipeline DDL
|   |-- check_05_vision_release.py # Run QA checks on final vision release files
|   `-- review_06_claim_taxonomy.py # Sample claim taxonomy outputs for manual inspection
|-- vision_ops/ # Operational tools for paid/manual pack-image release runs
|   |-- __init__.py # Package marker for vision-ops imports
|   |-- op_01_make_regional_samples.py # Split the smart sample into regional release sample files
|   |-- op_02_preflight_images.py # Check image URLs before spending on OCR
|   |-- op_03_reset_release_rows.py # Clear vision fields for selected release rows before rerun
|   |-- op_04_normalize_results.py # Apply deterministic cleanup to final vision result CSVs
|   |-- op_05_clear_stale_observations.py # Clear superseded vision observations outside the current release
|   |-- op_06_summarize_release.py # Summarize release-scoped claim prevalence and brand misses
|   `-- op_07_review_panel_context.py # Test panel-context review logic on saved OCR text
|-- governance/ # Audit and maintenance tools for category, brand/company, and nutrition governance
|   |-- __init__.py # Package marker for governance imports
|   |-- category_scope/ # Category-scope cleanup and audit utilities
|   |   |-- __init__.py # Package marker for category-scope imports
|   |   `-- cat_01_apply_category_cleanup.py # Audit or apply conservative category cleanup in SQLite
|   |-- brand_company_mapping/ # Brand, company, private-label, and orphan-mapping governance tools
|   |   |-- __init__.py # Package marker for brand/company governance imports
|   |   |-- map_01_build_brand_alias_review.py # Generate bottom-up brand alias review candidates
|   |   |-- map_02_build_company_mapping_review.py # Audit normalized-brand company mapping coverage
|   |   |-- map_03_build_top9_prefix_orphan_candidates.py # Find unmapped brands resembling Top 9 portfolio prefixes
|   |   |-- map_04_apply_top9_prefix_orphan_decisions.py # Apply reviewed Top 9 prefix-orphan decisions to reference CSVs
|   |   |-- map_05_cleanup_top9_reference_layers.py # Clean Top 9 reference mapping layers while preserving mapped output
|   |   |-- map_06_diagnose_brand_extraction.py # Diagnose alternative primary-brand extraction candidates
|   |   |-- map_07_export_orphan_candidates.py # Export high-volume unmapped regional/category brand candidates
|   |   `-- map_08_diagnose_brand_mapping.py # Run brand mapping counts, coverage, brand checks, and unmapped diagnostics
|   `-- nutrition_quality/ # Nutrition-quality governance helpers and historical reviews
|       |-- __init__.py # Package marker for nutrition-quality governance imports
|       `-- historical/ # Historical nutrition-quality review scripts retained for audit traceability
|           |-- __init__.py # Package marker for historical nutrition review imports
|           |-- nut_hist_01_exclusion_reduction_review.py # Review exclusion-rate impact from nutrition hard gates
|           |-- nut_hist_02_scenario_c_review.py # Review historical Scenario C nutrition governance candidates
|           |-- nut_hist_03_scenario_c2_review.py # Review historical Scenario C2 nutrition governance candidates
|           `-- nut_hist_04_distributional_plausibility_review.py # Review distributional plausibility thresholds
|-- exports/ # Read-only exports for documentation and downstream analysis
|   |-- __init__.py # Package marker for export imports
|   |-- export_schema.py # Export live SQLite schema to database/schema.sql
|   `-- export_vision_analyzed_dataset.py # Export vision-analyzed products for modeling and analysis
`-- vision_prompts/ # Versioned OCR and LLM prompt files for pack-image analysis
    |-- current/ # Active prompt files loaded by the vision extraction stage
    |   |-- prompt_en_context_review.txt # Active English panel-context review prompt
    |   |-- prompt_fr_context_review.txt # Active French panel-context review prompt
    |   |-- prompt_v5_en.txt # Active English claim-extraction prompt
    |   `-- prompt_v5_fr.txt # Active French claim-extraction prompt
    `-- historical/ # Older prompt versions retained for audit traceability
        |-- prompt_v1_v2.txt # Historical prompt versions 1 and 2
        |-- prompt_v3.txt # Historical prompt version 3
        `-- prompt_v4.txt # Historical prompt version 4
```


