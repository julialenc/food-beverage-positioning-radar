```text
pipeline/ # Production pipeline code, governance utilities, validation checks, prompts, and exports
|-- __init__.py # Package marker for pipeline imports
|-- README_NAVIGATING_PIPELINE.md # Tree map of pipeline folders and files
|-- PIPELINE_RETENTION_AUDIT.md # File classifications and dependency checks from the 2026-10-16 cleanup
|-- rules/ # Shared rules imported by pipeline stages and checks
|   |-- __init__.py # Package marker for rules imports
|   |-- category_rules.py # Category query, inclusion, exclusion, and cleanup rules
|   |-- population_policy.py # Approved retained population; tested on a copy, not yet integrated into production
|   |-- incremental_ingestion.py # Copy-only atomic processed batches, source ordering, replay checks and row history
|   |-- proxy_wave.py # Pinned bulk scan, preserved raw observations and September proxy cutoff decisions on a copy
|   |-- governed_ingestion.py # Govern eligible staged observations and connect the transactional copy-only writer
|   `-- claim_freshness.py # Match stored observations to original extraction image and prompt-context evidence
|-- stages/ # Ordered backbone scripts for building the product dataset, app tables, and deployment database
|   |-- __init__.py # Package marker for stage imports
|   |-- stage_01a_bootstrap_from_off_bulk.py # Bulk one-off download from Open Food Facts zip files
|   |-- stage_01b_ingest_from_off_api.py # Ongoing download from Open Food Facts via API
|   |-- stage_02_clean_products.py # Clean raw OFF data into analysis-ready product records
|   |-- stage_03_build_nutrition_quality_flags.py # Build nutrition-quality handoff file and audit outputs
|   |-- stage_04_build_product_analysis.py # Compute ingredient, claim-signal, and positioning-analysis fields
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
|   |-- check_06_baseline_capture.py # Verify read-only SQLite backup, WAL handling and population inventory
|   |-- check_07_population_policy.py # Test retained membership with real stage-05 upserts on disposable databases
|   |-- check_08_incremental_ingestion.py # Test transactional copy-only ingestion, rollback, replay and preserved history
|   |-- check_09_proxy_wave.py # Offline collection/cutoff/resume checks and optional full-size staging validation
|   |-- check_10_governed_ingestion.py # Governed writer integration, rollback, replay and full-size copy validation
|   |-- check_11_incremental_release.py # Retained release selection, cutoff reporting and claim freshness checks
|   `-- review_06_claim_taxonomy.py # Sample claim taxonomy outputs for manual inspection
|-- vision_ops/ # Operational tools for paid/manual pack-image release runs
|   |-- __init__.py # Package marker for vision-ops imports
|   |-- op_01_make_regional_samples.py # Split the smart sample into regional release sample files
|   |-- op_02_preflight_images.py # Check image URLs before spending on OCR
|   |-- op_03_reset_release_rows.py # Clear vision fields for selected release rows before rerun
|   |-- op_04_normalize_results.py # Apply deterministic cleanup to final vision result CSVs
|   |-- op_05_clear_stale_observations.py # Clear superseded vision observations outside the current release
|   |-- op_06_summarize_release.py # Summarize release-scoped claim prevalence and brand misses
|   |-- op_07_review_panel_context.py # Test panel-context review logic on saved OCR text
|   |-- op_08_prepare_targeted_retailer_ocr_llm_run.py # Resolve reviewed retailer OCR-LLM selections to GTIN sample files
|   `-- op_12_prepare_uk_claim_recall_final_09_2026.py # Final UK recall run provenance; original population guard retained
|-- governance/ # Audit and maintenance tools for category and brand/company governance
|   |-- __init__.py # Package marker for governance imports
|   |-- category_scope/ # Category-scope cleanup and audit utilities
|   |   |-- __init__.py # Package marker for category-scope imports
|   |   `-- cat_01_apply_category_cleanup.py # Audit or apply conservative category cleanup in SQLite
|   `-- brand_company_mapping/ # Brand, company, private-label, and orphan-mapping governance tools
|       |-- __init__.py # Package marker for brand/company governance imports
|       |-- map_01_build_brand_alias_review.py # Generate bottom-up brand alias review candidates
|       |-- map_02_build_company_mapping_review.py # Audit normalized-brand company mapping coverage
|       |-- map_03_build_top9_prefix_orphan_candidates.py # Find unmapped brands resembling Top 9 portfolio prefixes
|       |-- map_04_apply_top9_prefix_orphan_decisions.py # Apply reviewed Top 9 prefix-orphan decisions to reference CSVs
|       |-- map_05_cleanup_top9_reference_layers.py # Clean Top 9 reference mapping layers while preserving mapped output
|       |-- map_06_diagnose_brand_extraction.py # Diagnose alternative primary-brand extraction candidates
|       |-- map_07_export_orphan_candidates.py # Export high-volume unmapped regional/category brand candidates
|       `-- map_08_diagnose_brand_mapping.py # Run brand mapping counts, coverage, brand checks, and unmapped diagnostics
|-- maintenance/ # Reviewed mapping corrections and private-label analysis refresh tools
|   |-- capture_database_baseline.py # Preserve a consistent local baseline and provenance report without modifying source data
|   |-- prepare_population_policy_trial.py # Encode approved membership on a new local copy of the preserved baseline
|   |-- run_incremental_ingestion_trial.py # Create a new copy and apply explicit processed input or synthetic validation fixtures
|   |-- collect_off_snapshot.py # Resumable bulk evidence download with pinned source identity; no product writes
|   |-- stage_proxy_wave.py # Stage a completed snapshot and cutoff decisions on a fresh copy; supports scan resume
|   |-- connect_governed_wave.py # Process a completed staged wave and commit it transactionally on the same copy
|   |-- build_incremental_release.py # Rebuild downstream outputs and a separate completed release candidate with freshness audit
|   |-- apply_aldi_trader_joes_mapping_correction.py # Apply exact reviewed Aldi/Trader Joe's GTIN corrections
|   |-- validate_aldi_trader_joes_mapping_correction.py # Check those corrections in local database outputs
|   |-- apply_auchan_brand_renaming.py # Apply reviewed Auchan brand overrides
|   |-- expand_private_label_macro_benchmarks.py # Refresh retailer medians using the retained regional baseline
|   `-- refresh_aldi_private_label_analysis_exports.py # Refresh Aldi detail, investigation and protein exports into a new directory
|-- exports/ # Read-only exports for documentation and downstream analysis
|   |-- __init__.py # Package marker for export imports
|   |-- export_aldi_lidl_claims_evidence.py # Reconstruct reviewed Aldi/Lidl claims from frozen local snapshots; --check validates without writes
|   |-- export_schema.py # Export live SQLite schema to database/schema.sql
|   `-- export_retailer_product_details.py # Export local product inputs for mainstream-retailer analysis
|-- vision_prompts/ # Prompts used by the current extraction profiles
|   `-- current/
|       |-- prompt_en_context_review.txt # Active English panel-context review prompt
|       |-- prompt_fr_context_review.txt # Active French panel-context review prompt
|       |-- prompt_v5_en.txt # Active English claim-extraction prompt
|       |-- prompt_v5_fr.txt # Active French claim-extraction prompt
|       `-- prompt_uk_test_09.2026_final.txt # Active final UK profile; historical name/version preserved
`-- local_only/ # Ignored by Git; retained on Julia's machine
    |-- README.md # Archive inventory and usage cautions
    |-- export_vision_analyzed_dataset.py # Exploratory modeling export; output also stays here
    |-- nutrition_quality/historical/ # Four historical nutrition review scripts and original package markers
    |-- vision_prompts/historical/ # Three superseded prompt files
    `-- orphaned_bytecode/ # Two earlier UK test caches whose Python source files were not found
```



## Private-label analysis maintenance

- `exports/export_aldi_lidl_claims_evidence.py` rebuilds or validates the Aldi/Lidl
  aggregate evidence from local snapshots and exact reviewed territory decisions.
  It is a standalone analysis export, not a production pipeline stage.
- `maintenance/refresh_aldi_private_label_analysis_exports.py` requires a new
  `--output-dir` outside `presentations/private_label_analysis/`. Its investigation
  selection comes from `presentations/private_label_analysis/aldi_lidl/archive/`
  by default. It no longer
  creates the redundant Aldi reduced macro export.
- `maintenance/expand_private_label_macro_benchmarks.py` requires a new `--output`
  outside `presentations/private_label_analysis/`. It reads the retained regional baseline and
  recalculates retailer rows from SQLite without overwriting publication evidence.

`exports/export_retailer_product_details.py` writes local-only retailer exports
under `presentations/private_label_analysis/mainstream_*`. The optional
`vision_ops/op_12_prepare_uk_claim_recall_final_09_2026.py` reads its UK exports
there. These are supporting analysis workflows, not Streamlit dependencies.

Migration validation on 2026-10-16 found that the UK recall script's retained
guard expects 919 `NO_CLAIM_IDENTIFIED` rows, while current exports contain 504.
Subsequent read-only verification found the completed 919-observation release
in the working database. Preparation cannot be repeated on the changed current
population without a new selection review; the historical run is not unfinished.

See `presentations/private_label_analysis/aldi_lidl/README.md`
for local evidence locations, run examples and publication status.

## Operating boundaries

Ordered stages build the app dataset. Manual governance and maintenance tools
are retained for their dependency or audit role, not scheduled for automatic
execution. Private-label exporters support the independent
[presentation evidence collection](../presentations/private_label_analysis/README.md).
Its frozen inputs and PDFs are separate from fresh pipeline output.

The latest UK extraction profile uses the final September prompt and approved
text rescues. The final recall release has 919 observations recorded in the
working database. Its preparation script's 919-row guard rejects the current
504-candidate input population; that is not an unfinished historical run.
See the [extraction guide](../docs/02_PACK_IMAGE_ANALYSIS/01_FRONT_PACK_CLAIM_EXTRACTION.md)
before planning any new paid run.

The [retention audit](PIPELINE_RETENTION_AUDIT.md) explains the public/local
split. Historical nutrition scripts and old prompts remain under the ignored
`local_only/` archive. A public checkout does not contain all local inputs
needed by retained manual tools.

## Incremental-readiness work

The original baseline capture was checksum-verified and moved to
`G:\My Drive\Food Beverage Positioning Radar\wave_archives\baseline_20261016T180817_168296Z\`.
Population-policy trial outputs remain local under
`data/06_brand_governance_outputs/population_policy_trials/`. The trial adds
membership metadata to a separate database copy; production stages and
Streamlit have not yet been connected to it. See the
[approved population policy](../docs/03_PROJECT_REFERENCE/06_INCREMENTAL_POPULATION_POLICY.md)
for counts, date provenance, test coverage and remaining integration work.

The separate copy-only transactional writer and its validation outputs use
`data/06_brand_governance_outputs/incremental_ingestion_trials/`. The October 17
OFF export was collected, staged against the September 29 eligibility cutoff,
governed and written on a marked copy. The completed release candidate is in
`release_real_proxy_20261018_v1/` under that trials directory. It checks claim
provenance and rebuilds downstream outputs with explicit retained population
and completed-release selection. The source export stays local under
`data/02_raw_off_downloads/incremental_snapshots/`. Paid vision refresh remains
a separate operation. The legacy file-discovery pipeline is not the monthly
incremental entry point.
