# Wave 2 ingestion — public audit and local evidence

Wave 2 retrieval: **17 October 2026**. Reporting cutoff: **29 September 2026**. Wave 3 is outside this release.

[Corrected master contract](05_master_parquet/README.md) · [Master manifest](05_master_parquet/output/manifest.json) · [Locked claim rules](04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/RULES.md) · [Final approval](04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/final_approval.md) · [Analytical package](../04_analytical_package/ARTIFACT_INDEX.md)

## Authoritative current population

The corrected master contains **374,840 governed products and 382,527 unique barcode–region–category rows**. There are **12,161 matched claim observations**, including two analytically excluded assignments, and **370,366 unmatched rows with null claims**. The analytical package records 376,845 product-scope-eligible assignments. Apply question-specific availability and validity requirements afterward; do not create one universal nutrition-complete population.

The original population manifest records the earlier, pre-barcode-correction population (522,432 products and 535,129 country/category assignments). Those counts describe historical sampling provenance, not the current analytical denominator. OBS-028 documents the identity correction in the project observations. Original sampling records, GTIN spellings, image identities and evidence outcomes are preserved; alias-aware integration uses the corrected source without rewriting the observations.

## Consolidated ingestion decisions

| Stage | Accepted decision and retained evidence |
|---|---|
| Population | The governed OFF release defines admission. The original population pull and its manifest remain historical evidence. Corrected Wave 2, not the original candidate CSV, supplies current reporting and analytical product identities. |
| Nutrition and sampling | Exact reviewed exclusions outrank broad rules. RUN 02/03 diagnostics and RUN 04/04B groups supported pack-assessment sampling, not final nutritional segments. The approved grouping decisions, allocation rules and CHECK 04/05/06A approvals are public. Detailed matrices, candidate/reserve lists, diagnostics and source snapshots remain local. |
| Final selection | The main assessment selection held out US/Canada dairy and contained 11,902 records. The separate approved dairy selection contains 224 new jobs plus 35 separately identified historical reuses. Preserve both selection histories and image-review decisions. This is a selected evidence population, not a representative claims-prevalence sample. |
| Beverage method | BEVERAGE FINAL and benefit definitions v1.0.0 are locked. Approved eligibility, coconut and identity decisions remain distinct from preliminary proposals. Current effective rules are in beverage_final_v1/eligibility_decisions.csv. Earlier definitions and prompt/model experiments are historical, not authorized rerun candidates. |
| Execution | Main execution assessed all 11,902 records: the runner accepted 8,459, with 3,322 HOLD and 121 technical/missing-output cases. These operational outcomes are not the same as individual proposition usability. Saved images, dispatch history, receipts, reservations, raw/normalized model outputs and ledgers stay local and immutable. |
| Reconciliation | The approved lock contains 12,126 newly processed observations and 35 linked historical reuses, giving 12,161 exact join rows. Core outcomes, claim-specific assessment and independent beverage v6 states remain separate. Completion reports, six-case review and full reconciliation tables are retained locally; final approval supersedes pending proposals. |
| Claims | Positive, documented non-detection, uncertain and unassessed states remain distinct. Unmatched products retain null claims. Non-detection describes assessed evidence, not the whole pack. Preserve exact wording and provenance; sugar-related communication is broader than literal sugar-free wording. Use energy_positioning for the approved energy-positioning interpretation. |
| Master | The builder joins through exact text barcode, region and category after governed identity resolution. Source values, original barcode/category lineage, separate evidence cohorts and nullable claims are retained. No new OCR/LLM, enrichment or master rebuild is part of housekeeping. |

US/Canada core structured-nutrition coverage is approximately 14–15%, an investigated upstream OFF coverage limitation. It is not a newly unresolved ingestion defect. Missing nutrients stay missing; nutrition-empty records may still be useful for other questions. The 486 minimal-information assignments do not require blanket deletion or manual review. Questionable recorded values remain source observations with field-specific interpretation safeguards, rather than being converted to missing or globally excluded without an analytical reason.

The commercial/formulation research chapter is closed for the investigated families. Accepted descriptive profiles use research thresholds, not asserted natural clusters or market-prevalence estimates. The hierarchy is commercial identity → nutritional formulation → communicated positioning. See the public research audit in 03_lenses for completed analytical decisions.

## Public versus local artifacts

Public files below contain reproducible source, reviewed rules, approvals, schemas and concise audit evidence. Reviewed rule tables can contain exact product keys; they are retained as decisions, not bulk product exports. The original reports summarized above remain locally unchanged: consolidation does not delete or rewrite evidence.

All other ingestion files remain local, including master/claim Parquets, population/selection CSVs, saved pack images, human workbooks, OCR/model observations, detailed validation history, infrastructure records and execution databases. A local file is not disposable merely because it is derivable or has an unfamiliar extension. No deletions were performed in this publication.

| Published file | Role |
|---|---|
| [01_population/run_01/run_01_manifest.json](<01_population/run_01/run_01_manifest.json>) | Approval, definition or manifest/validation contract |
| [01_population/run_01/run_01_source_snapshot.py](<01_population/run_01/run_01_source_snapshot.py>) | Reproducible source or exact historical source snapshot |
| [02_nutrition_and_sampling/01_nutrition_and_exclusions/check_02_spearman_correlations.py.snapshot](<02_nutrition_and_sampling/01_nutrition_and_exclusions/check_02_spearman_correlations.py.snapshot>) | Reproducible source or exact historical source snapshot |
| [02_nutrition_and_sampling/01_nutrition_and_exclusions/run_01_followup_main.py.snapshot](<02_nutrition_and_sampling/01_nutrition_and_exclusions/run_01_followup_main.py.snapshot>) | Reproducible source or exact historical source snapshot |
| [02_nutrition_and_sampling/01_nutrition_and_exclusions/run_03_exclusions_v1.csv](<02_nutrition_and_sampling/01_nutrition_and_exclusions/run_03_exclusions_v1.csv>) | Approved/reviewed decision input |
| [02_nutrition_and_sampling/01_nutrition_and_exclusions/run_03_prepare_feature_matrices.py.snapshot](<02_nutrition_and_sampling/01_nutrition_and_exclusions/run_03_prepare_feature_matrices.py.snapshot>) | Reproducible source or exact historical source snapshot |
| [02_nutrition_and_sampling/02_sampling_groups/check_04_followup_v1/sampling_grouping_decisions.csv](<02_nutrition_and_sampling/02_sampling_groups/check_04_followup_v1/sampling_grouping_decisions.csv>) | Approved/reviewed decision input |
| [02_nutrition_and_sampling/03_candidate_frame_and_allocation/run_05_v1/check_04_approval.json](<02_nutrition_and_sampling/03_candidate_frame_and_allocation/run_05_v1/check_04_approval.json>) | Approval, definition or manifest/validation contract |
| [02_nutrition_and_sampling/03_candidate_frame_and_allocation/run_05_v1/check_05_approval.json](<02_nutrition_and_sampling/03_candidate_frame_and_allocation/run_05_v1/check_05_approval.json>) | Approval, definition or manifest/validation contract |
| [02_nutrition_and_sampling/03_candidate_frame_and_allocation/run_06a_v1/check_06a_approval.json](<02_nutrition_and_sampling/03_candidate_frame_and_allocation/run_06a_v1/check_06a_approval.json>) | Approval, definition or manifest/validation contract |
| [02_nutrition_and_sampling/03_candidate_frame_and_allocation/run_06a_v1/selection_rules.md](<02_nutrition_and_sampling/03_candidate_frame_and_allocation/run_06a_v1/selection_rules.md>) | Method, approval or consolidated audit documentation |
| [02_nutrition_and_sampling/04_final_selection/wave2_dairy_shortlist_v1/APPROVED_SELECTION.md](<02_nutrition_and_sampling/04_final_selection/wave2_dairy_shortlist_v1/APPROVED_SELECTION.md>) | Method, approval or consolidated audit documentation |
| [03_pack_evidence/01_beverage_method/approved_method/BEVERAGE 05B - Approved eligibility policy.md](<03_pack_evidence/01_beverage_method/approved_method/BEVERAGE 05B - Approved eligibility policy.md>) | Method, approval or consolidated audit documentation |
| [03_pack_evidence/01_beverage_method/approved_method/BEVERAGE 05C - Human review closure.md](<03_pack_evidence/01_beverage_method/approved_method/BEVERAGE 05C - Human review closure.md>) | Method, approval or consolidated audit documentation |
| [03_pack_evidence/01_beverage_method/approved_method/BEVERAGE FINAL - Implementation and lock.md](<03_pack_evidence/01_beverage_method/approved_method/BEVERAGE FINAL - Implementation and lock.md>) | Method, approval or consolidated audit documentation |
| [03_pack_evidence/01_beverage_method/approved_method/beverage_03_approved_v1/benefit_definition_registry_v1.0.0.json](<03_pack_evidence/01_beverage_method/approved_method/beverage_03_approved_v1/benefit_definition_registry_v1.0.0.json>) | Approval, definition or manifest/validation contract |
| [03_pack_evidence/01_beverage_method/approved_method/beverage_05b_decision_register.csv](<03_pack_evidence/01_beverage_method/approved_method/beverage_05b_decision_register.csv>) | Approved/reviewed decision input |
| [03_pack_evidence/01_beverage_method/approved_method/beverage_05c_coconut_decisions_human_reviewed.csv](<03_pack_evidence/01_beverage_method/approved_method/beverage_05c_coconut_decisions_human_reviewed.csv>) | Approved/reviewed decision input |
| [03_pack_evidence/01_beverage_method/approved_method/beverage_05d_identity_decisions.csv](<03_pack_evidence/01_beverage_method/approved_method/beverage_05d_identity_decisions.csv>) | Approved/reviewed decision input |
| [03_pack_evidence/01_beverage_method/approved_method/beverage_final_v1/eligibility_decisions.csv](<03_pack_evidence/01_beverage_method/approved_method/beverage_final_v1/eligibility_decisions.csv>) | Approved/reviewed decision input |
| [03_pack_evidence/01_beverage_method/approved_method/beverage_final_v1/final_lock_manifest.json](<03_pack_evidence/01_beverage_method/approved_method/beverage_final_v1/final_lock_manifest.json>) | Approval, definition or manifest/validation contract |
| [03_pack_evidence/01_beverage_method/approved_method/beverage_final_v1/manifest.json](<03_pack_evidence/01_beverage_method/approved_method/beverage_final_v1/manifest.json>) | Approval, definition or manifest/validation contract |
| [04_reviewed_claims/02_reconciliation_and_exceptions/CLAIM_STATE_DENOMINATORS_CHECK.md](<04_reviewed_claims/02_reconciliation_and_exceptions/CLAIM_STATE_DENOMINATORS_CHECK.md>) | Method, approval or consolidated audit documentation |
| [04_reviewed_claims/02_reconciliation_and_exceptions/ENERGY_DRINK_COVERAGE_CHECK.md](<04_reviewed_claims/02_reconciliation_and_exceptions/ENERGY_DRINK_COVERAGE_CHECK.md>) | Method, approval or consolidated audit documentation |
| [04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/CHECK.md](<04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/CHECK.md>) | Method, approval or consolidated audit documentation |
| [04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/RULES.md](<04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/RULES.md>) | Method, approval or consolidated audit documentation |
| [04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/final_approval.md](<04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/final_approval.md>) | Method, approval or consolidated audit documentation |
| [04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/manifest.json](<04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/manifest.json>) | Approval, definition or manifest/validation contract |
| [04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/validation.json](<04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/validation.json>) | Approval, definition or manifest/validation contract |
| [04_reviewed_claims/recorded_source/index.json](<04_reviewed_claims/recorded_source/index.json>) | Historical source hash index |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/beverage_01_ocr_evidence_audit.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/beverage_01_ocr_evidence_audit.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/beverage_02_validation_preparation.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/beverage_02_validation_preparation.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/beverage_03_close_review.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/beverage_03_close_review.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/beverage_03_human_review_reconciliation.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/beverage_03_human_review_reconciliation.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/beverage_05a_non_beverage_audit.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/beverage_05a_non_beverage_audit.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/close_beverage_04.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/close_beverage_04.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/close_check_06a.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/close_check_06a.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/implement_beverage_current_wave.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/implement_beverage_current_wave.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/lock_wave2_ocr_llm.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/lock_wave2_ocr_llm.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/prepare_emerging_benefits_prompt_v1.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/prepare_emerging_benefits_prompt_v1.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/prepare_run_06b_final_candidates.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/prepare_run_06b_final_candidates.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/reconcile_run_06b_step2.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/reconcile_run_06b_step2.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/reconcile_run_06b_step4.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/reconcile_run_06b_step4.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/reconcile_wave2_claims.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/reconcile_wave2_claims.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/review_run_06b_step3.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/review_run_06b_step3.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/run_04_preliminary_clustering.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/run_04_preliminary_clustering.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/run_04b_broad_m1.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/run_04b_broad_m1.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/run_05_candidate_universe.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/run_05_candidate_universe.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/run_06a_allocation_design.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/run_06a_allocation_design.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/segmentation/run_06b_prepare.py](<04_reviewed_claims/recorded_source/pipeline/segmentation/run_06b_prepare.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/emerging_benefits_stage.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/emerging_benefits_stage.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/emerging_benefits_v2.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/emerging_benefits_v2.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/emerging_benefits_v3.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/emerging_benefits_v3.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/prepare_run_06b_runner_readiness.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/prepare_run_06b_runner_readiness.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/recover_run_06b_pilot.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/recover_run_06b_pilot.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/run_06b_main_readiness.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/run_06b_main_readiness.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/run_06b_pilot_history.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/run_06b_pilot_history.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/run_06b_v6_confirmation.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/run_06b_v6_confirmation.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/run_06b_v6_liquid_recovery.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/run_06b_v6_liquid_recovery.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/run_06b_v6_mini.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/run_06b_v6_mini.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/test_emerging_benefits_v2.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/test_emerging_benefits_v2.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/test_emerging_benefits_v3.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/test_emerging_benefits_v3.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/pipeline/vision_ops/test_run_06b_execution_guard.py](<04_reviewed_claims/recorded_source/pipeline/vision_ops/test_run_06b_execution_guard.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/shared/beverage_eligibility.py](<04_reviewed_claims/recorded_source/shared/beverage_eligibility.py>) | Archived exact source; provenance only, not the active execution entry point |
| [04_reviewed_claims/recorded_source/shared/db.py](<04_reviewed_claims/recorded_source/shared/db.py>) | Archived exact source; provenance only, not the active execution entry point |
| [05_master_parquet/README.md](<05_master_parquet/README.md>) | Method, approval or consolidated audit documentation |
| [05_master_parquet/build.py](<05_master_parquet/build.py>) | Reproducible source or exact historical source snapshot |
| [05_master_parquet/output/manifest.json](<05_master_parquet/output/manifest.json>) | Approval, definition or manifest/validation contract |
| [README.md](<README.md>) | Method, approval or consolidated audit documentation |
| [historical_paths.json](<historical_paths.json>) | Approval, definition or manifest/validation contract |

## Executable dependencies and restoration contract

The master entry point delegates to these existing sources, published unchanged with this scope:

- `presentations/segmentation/production/workflow/build_master.py`
- `presentations/segmentation/production/workflow/artifact_paths.py`
- `presentations/segmentation/production/workflow/evidence_index.py`
- `pipeline/segmentation/run_01_select_eligible_products.py`

`pipeline/rules/barcode_identity.py` is already versioned. These modules need Python and PyArrow; exact analytical-package versions are recorded in its manifest. The original-source archive preserves earlier implementations; it is not an alternative active pipeline. Other future-wave production scripts are outside this publication scope.

Reproduction additionally requires the corrected Wave 2 work database and manifest under `data/06_brand_governance_outputs/wave2_identity_fix_v1/`, the country/region reference CSV, the original RUN 01 manifest, reviewed exclusion/eligibility rules and the local locked claims layer. The analytical verifier also requires its declared local keyed outputs and independent accepted references. GitHub contains the code and audit contract; a checkout without restored local inputs is not self-contained.

The reporting helpers consume `beverage_final_v1/benefit_app_overlay.csv`, `segmentation_beverage_eligible_keys.csv` and eligibility decisions. Keep those local tables at their current locations. This publication does not modify the Streamlit population or application.

Historical manifests/approvals retain recorded paths and hashes. Resolve historical segmentation paths through [historical_paths.json](historical_paths.json) and the production path helper, then check the recorded hash. The source index itself retains the older `first_run/04_reviewed_claims/recorded_source/` prefix; its archive now lives under `first_run/01_ingestion/04_reviewed_claims/recorded_source/`. Keep that recorded identity unchanged and resolve the archive location explicitly. Archived reports can contain historical relative links; the public links in this guide are the current navigation contract.

## Housekeeping validation and remaining work

Publication preserves all images, ledgers, original reports, locked outputs and archived source bytes. The two current navigation READMEs are the only ingestion files updated for consolidation; they are not locked manifest outputs. Source, claims and analytical-package hash verification is read-only and does not rerun provider calls, model fitting or numerical analyses.

The full isolated pipeline smoke test remains outstanding and must use restored inputs and a new output location. Never remove the accepted analytical freeze to force a rerun. After scoped pushes, update the repository README and segmentation navigation as one coherent documentation pass; those wider navigation edits are deferred from this commit. No data deletion or smoke-test execution is authorized by this publication step.
