# Pipeline retention audit — 2026-10-16

Scope: all 76 non-cache files in `pipeline/` at the start of this cleanup:
56 executable scripts, 11 package markers, eight prompt files and the navigation
README. The review covered imports, calls, path construction, generated filenames,
references in code/documentation, and the relationship to production or retained
private-label evidence.

## Disposition

| Treatment | Result |
| --- | --- |
| Keep available for GitHub | 51 scripts, nine package markers and five active prompts |
| Keep on Julia's machine only | Five scripts, two package markers and three superseded prompts |
| Preserve additional historical remnants locally | Two Python 3.12 bytecode files whose source scripts were not found |
| Permanently delete | 66 regenerable bytecode files; no analytical source scripts |
| Supporting documentation | Updated navigation and this audit record |

The local archive is `pipeline/local_only/`, excluded by the root `.gitignore`.
Previously tracked originals appear as deletions in the working tree; their
relocated copies remain on disk and will not be added by an ordinary Git add.
This does not erase earlier Git history. No staging, commit or push is part of
this cleanup.

An absence of imports alone is not evidence that a manual governance tool is
disposable. Mapping review, correction and validation tools are retained as
support for the reviewed reference inputs and derived production mappings.
They remain separate from the ordered pipeline stages.

## Public script inventory

Paths below are relative to `pipeline/`. Retention does not authorize rerunning
a tool that changes mappings, databases or paid OCR/LLM results.

| Script | Reason for retention |
| --- | --- |
| `exports/export_aldi_lidl_claims_evidence.py` | Reconstructs and checks final Aldi/Lidl claims evidence from frozen local inputs. |
| `exports/export_retailer_product_details.py` | Supplies product-level inputs to the standalone mainstream-retailer analyses. |
| `exports/export_schema.py` | Exports the production database schema for documentation. |
| `governance/brand_company_mapping/map_01_build_brand_alias_review.py` | Builds alias review proposals and Carrefour mapping audit evidence. |
| `governance/brand_company_mapping/map_02_build_company_mapping_review.py` | Audits the primary-brand versus normalized-brand company mapping layers; supports mapping QA. |
| `governance/brand_company_mapping/map_03_build_top9_prefix_orphan_candidates.py` | Produces candidate files for reviewed Top 9 orphan mapping decisions. |
| `governance/brand_company_mapping/map_04_apply_top9_prefix_orphan_decisions.py` | Applies reviewed decisions to reference files consumed by stages 02 and 05. |
| `governance/brand_company_mapping/map_05_cleanup_top9_reference_layers.py` | Maintains reference layers with pre/post equality checks for locked mapped results. |
| `governance/brand_company_mapping/map_06_diagnose_brand_extraction.py` | Diagnoses portfolio-aware brand extraction and supports review of stage-02 mapping behavior. |
| `governance/brand_company_mapping/map_07_export_orphan_candidates.py` | Exports regional/category orphan candidates used by mapping governance. |
| `governance/brand_company_mapping/map_08_diagnose_brand_mapping.py` | Provides mapping coverage, brand and unmapped-product QA. |
| `governance/category_scope/cat_01_apply_category_cleanup.py` | Audits/applies reviewed category cleanup for existing database rows. |
| `maintenance/apply_aldi_trader_joes_mapping_correction.py` | Implements the reviewed exact-GTIN correction in derived mapping fields. |
| `maintenance/apply_auchan_brand_renaming.py` | Writes reviewed exact-GTIN overrides and derived Auchan brand corrections. |
| `maintenance/expand_private_label_macro_benchmarks.py` | Produces retailer nutrition medians against the retained regional baseline. |
| `maintenance/refresh_aldi_private_label_analysis_exports.py` | Refreshes Aldi detail, investigation and protein exports into a separate directory. |
| `maintenance/validate_aldi_trader_joes_mapping_correction.py` | Validates the reviewed Aldi/Trader Joe's correction. |
| `rules/category_rules.py` | Shared ingestion/category rules imported by production and validation. |
| `stages/stage_01a_bootstrap_from_off_bulk.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_01b_ingest_from_off_api.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_02_clean_products.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_03_build_nutrition_quality_flags.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_04_build_product_analysis.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_05_load_database.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_06_detect_sampling_signals.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_07_assign_sampling_bands.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_08_classify_formulation_families.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_09_build_vision_sample.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_10_extract_pack_claims.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_11_merge_vision_results.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_12_build_claim_taxonomy.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_13_build_app_summaries.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_14_compute_region_benchmarks.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_15_compute_profile_intersections.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_16_build_chart_ranges.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `stages/stage_17_build_deployment_database.py` | Ordered production build, sampling, enrichment or deployment stage. |
| `validation/check_01_category_rules.py` | Validation or manual QA for production rules, schema or pack claims. |
| `validation/check_02_nutrition_quality.py` | Validation or manual QA for production rules, schema or pack claims. |
| `validation/check_03_beverage_segments.py` | Validation or manual QA for production rules, schema or pack claims. |
| `validation/check_04_schema.py` | Validation or manual QA for production rules, schema or pack claims. |
| `validation/check_05_vision_release.py` | Validation or manual QA for production rules, schema or pack claims. |
| `validation/review_06_claim_taxonomy.py` | Validation or manual QA for production rules, schema or pack claims. |
| `vision_ops/op_01_make_regional_samples.py` | Operational preparation, normalization or QA for the production vision release. |
| `vision_ops/op_02_preflight_images.py` | Operational preparation, normalization or QA for the production vision release. |
| `vision_ops/op_03_reset_release_rows.py` | Operational preparation, normalization or QA for the production vision release. |
| `vision_ops/op_04_normalize_results.py` | Operational preparation, normalization or QA for the production vision release. |
| `vision_ops/op_05_clear_stale_observations.py` | Operational preparation, normalization or QA for the production vision release. |
| `vision_ops/op_06_summarize_release.py` | Operational preparation, normalization or QA for the production vision release. |
| `vision_ops/op_07_review_panel_context.py` | QA for the actual stage-10 panel-context reviewer using saved OCR. |
| `vision_ops/op_08_prepare_targeted_retailer_ocr_llm_run.py` | Prepares reviewed retailer selections for stage 10, including private-label runs. |
| `vision_ops/op_12_prepare_uk_claim_recall_final_09_2026.py` | Records the completed final UK recall workflow; its historical population guard prevents rerunning on changed inputs. |

The five published prompts are the three extraction prompts (English, French
and the final September UK profile) and two panel-context prompts. The UK
prompt's filename and profile/version identifiers are preserved. Only its
location and loader path changed.

## Local-only files and dependency reasoning

| Original location | New local location | Why retain locally |
| --- | --- | --- |
| `governance/nutrition_quality/historical/nut_hist_01_exclusion_reduction_review.py` | `local_only/nutrition_quality/historical/nut_hist_01_exclusion_reduction_review.py` | Historical exclusion-reduction experiment; produces the review input used by the two following scenario scripts. |
| `governance/nutrition_quality/historical/nut_hist_02_scenario_c_review.py` | `local_only/nutrition_quality/historical/nut_hist_02_scenario_c_review.py` | Historical Scenario C experiment; no production consumer of its proposed outputs. |
| `governance/nutrition_quality/historical/nut_hist_03_scenario_c2_review.py` | `local_only/nutrition_quality/historical/nut_hist_03_scenario_c2_review.py` | Historical Scenario C2 experiment; explains earlier governance choices. |
| `governance/nutrition_quality/historical/nut_hist_04_distributional_plausibility_review.py` | `local_only/nutrition_quality/historical/nut_hist_04_distributional_plausibility_review.py` | Historical tail-distribution research, documented in nutrition governance; its outputs remain local audit evidence. |
| `exports/export_vision_analyzed_dataset.py` | `local_only/export_vision_analyzed_dataset.py` | Exploratory formulation-versus-claims modeling export; no current downstream consumer was found. |
| `vision_prompts/historical/` (three prompt files) | `local_only/vision_prompts/historical/` | Superseded prompt versions retained as experiment history; not loaded by any current profile. |
| `governance/nutrition_quality/` (two package markers) | `local_only/nutrition_quality/` (same relative locations) | Preserved with their historical modules. |

The nutrition scripts read production-generated `nutrition_quality_flags.csv`;
the production stage does not read their experimental outputs. Scenario C and
C2 still read the review CSV generated by historical script 01. Their relative
directory depth, repository root resolution and data paths are unchanged.
Same-named helper functions in the production nutrition stage are independently
defined there, not imported from these historical scripts.

The modeling export continues to import the live stage-12 claim taxonomy. Its
repository root remains valid at the new depth. Its output is now
`pipeline/local_only/vision_analyzed_dataset.csv`, so a future exploratory export
cannot accidentally appear as a publishable CSV in the pipeline root.
No export was regenerated.

Two source-less caches were preserved under `local_only/orphaned_bytecode/`:
`op_10_prepare_tesco_52_claims_test_09_2026.cpython-312.pyc` and
`op_11_prepare_sainsbury_claims_test_09_2026.cpython-312.pyc`.
These are historical remnants, not readable source or validated runnable tools.
The other 66 caches had corresponding source files and were deleted.

## Move provenance

SHA-256 values below identify the original files before moving. The historical
nutrition files, their package markers, all three older prompts and the active
UK prompt were moved without changing their bytes. Only the local modeling
export's usage/output paths were edited.

| Original path (relative to pipeline) | Original SHA-256 |
| --- | --- |
| `exports/export_vision_analyzed_dataset.py` | `924516a5787b0911c2f20e54d26a43244a75741ddbf3ee79e1c1909fe2760933` |
| `governance/nutrition_quality/__init__.py` | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| `governance/nutrition_quality/historical/__init__.py` | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| `governance/nutrition_quality/historical/nut_hist_01_exclusion_reduction_review.py` | `7412aad3f46a3439caa045c55e956b5082d8dced62638f9a17af2b43e79d294f` |
| `governance/nutrition_quality/historical/nut_hist_02_scenario_c_review.py` | `fe5ce1b0be562770c5bb1416aefe201a271d28fdac6075e3af1cf2546a368cc9` |
| `governance/nutrition_quality/historical/nut_hist_03_scenario_c2_review.py` | `c0b077d2092c34b9e19e56b5ff17b03e5f879c93e960378d3bc76cc0fcb03301` |
| `governance/nutrition_quality/historical/nut_hist_04_distributional_plausibility_review.py` | `ddb94f9c155271e18f979a2192f5e4e11c7a3dc09edfe3f97019692c5e914804` |
| `vision_prompts/historical/prompt_v1_v2.txt` | `fe79c41da1395875a7481facf162008689fa7ba4264173b01daf3d75978efc9e` |
| `vision_prompts/historical/prompt_v3.txt` | `f839a1499a4e582aa8cb15eef55f084b2cc87a0faad882ddd2405309dac572f5` |
| `vision_prompts/historical/prompt_v4.txt` | `07e9a88eaf3cfbfa6cbe8bf85ab214ba0940f55576d6afac6862d49cb051dbe5` |
| `vision_prompts/prompt_uk_test_09.2026_final.txt` | `0b5a2edc8e01a8d1d9b676dcb395c28fed181334d9f5991876091a8749c5f0b0` |

A complete before-cleanup file inventory and the deleted cache filenames are
retained locally in `local_only/cleanup_inventory_20261016.json`.

## Constraints and follow-up

- Clarified during documentation review on 2026-10-16: the working database
  records 919 vision observations for the final UK recall release and prompt.
  The preparation script expects the original 919 `NO_CLAIM_IDENTIFIED`
  candidates; current retained exports contain 504. The historical run is
  recorded, not unfinished. A future selection requires separate population
  review; the guard must not be relaxed to manufacture historical inputs.
- Several manual mapping/retailer tools require local review CSVs or a local
  database. Publishing their code does not publish those inputs or make a fresh
  GitHub checkout sufficient to reproduce every historical run.
- Raw data, mapping reference values, presentation snapshots, aggregates, PDF
  files and databases were outside this change. No analytical rebuild or paid
  OCR/LLM run was performed.
- At cleanup closeout, documentation alignment was deferred. The 2026-10-16
  documentation pass subsequently aligned the non-root-README Markdown files.
  Julia then approved the root README update, which is now complete, including
  presentation scope, the portfolio summary image and direct PDF navigation.
  The next step is review of the GitHub publication set; no staging, commit or
  push has been performed.

## Validation

- All 67 Python files (public and local) compile without creating bytecode.
- Public pipeline/shared import targets resolve; no public script imports the
  local archive. All five relocated scripts retain correct repository roots.
- All three extraction profiles load their prompt text and resolve their context
  prompts. Prompt bytes and version identifiers are unchanged.
- The 73 original files outside the three intentionally edited files retain
  their original SHA-256 hashes at their current locations. The two edited
  scripts differ only in the documented loader/usage/output paths, allowing
  newline normalization. The third edited file is the pipeline navigation guide.
- SHA-256 checks preserve 53 protected files, including reference inputs,
  presentation evidence/PDFs, the root README and the Git index. Database sizes
  and modification times are unchanged at microsecond resolution.
- All 14 local archive files, including its README and inventory, are ignored;
  the active UK prompt remains eligible for publication.
- Category validation: 135/135 cases passed. Nutrition-quality and beverage
  validation passed. The nutrition check initially failed from machine memory
  exhaustion, then passed with numerical-library threading limited to one.
- Aldi/Lidl evidence check: 78 territory cells and eight scope summaries passed;
  the four documented differences from the original PDF remain unchanged.
- Git whitespace checks passed. Obsolete active-path references were removed;
  original paths remain only as provenance in the audit and frozen local files.

These are targeted dependency and regression checks, not an end-to-end data
rebuild. No external API calls or database-writing stages were run.
