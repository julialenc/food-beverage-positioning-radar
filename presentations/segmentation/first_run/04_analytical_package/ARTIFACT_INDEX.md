# Analytical package v1 — artifact index

Accepted frozen v1 package; no source deletion, commit/push or website publication. [CHECK](CHECK.md) · [Data dictionary](DATA_DICTIONARY.md) · [Project methodology](../../SEGMENTATION.md)

## Rerun and acceptance

Run from the repository: `.venv/Scripts/python.exe -B presentations/segmentation/first_run/04_analytical_package/build_analytical_package_v1.py`, then the sibling `verify_analytical_package_v1.py`. Routine build imports only analytical_rules_v1.py and ordinary Python libraries. The verifier independently compares against retained accepted evidence; it does not execute original research main functions. Sources and classifications stay frozen. Accepted v1 is frozen: the builder refuses overwrite; the verifier checks integrity read-only. A new build needs an approved new version/destination.

## Protected canonical code dependencies

All three files are protected canonical dependencies and are included in the release manifest/freeze hashes. None is a housekeeping deletion or relocation candidate.

| File | Role |
|---|---|
| [build_analytical_package_v1.py](build_analytical_package_v1.py) | Canonical builder and input/output contract; frozen-v1 overwrite guard |
| [analytical_rules_v1.py](analytical_rules_v1.py) | Shared validity, commercial interpretation, profile and claim-state definitions |
| [verify_analytical_package_v1.py](verify_analytical_package_v1.py) | Independent equivalence verifier; read-only frozen-release integrity check |

## Canonical outputs

| Artifact | Rows | Role |
|---|---:|---|
| [analytical_assignments_v1.parquet](output/analytical_assignments_v1.parquet) | 382527 | Product-level commercial/nutrition/profile foundation; full master grain |
| [approved_findings_v1.json](output/approved_findings_v1.json) | structured | Accepted decisions/statistical context and limitations |
| [assessed_communication_v1.parquet](output/assessed_communication_v1.parquet) | 12161 | Sparse locked communication; join by exact key, preserve unknown |
| [boundary_annotations_v1.parquet](output/boundary_annotations_v1.parquet) | 32336 | Independent boundary descriptors/uncertainty; no source recategorization |
| [communication_coverage_v1.csv](output/communication_coverage_v1.csv) | 13602 | Reproduced exact-proposition evidence populations |
| [human_observations_v1.parquet](output/human_observations_v1.parquet) | 12 | Separate qualitative human evidence; no locked-field override |
| [population_summary_v1.csv](output/population_summary_v1.csv) | 411 | Population and field-specific coverage/profile denominators |

[Build/validation manifest](output/manifest_v1.json) supplies exact input, code and output identities/hashes. No output is a market-prevalence estimate.

## Runtime inputs and evidence

All paths below are repository-relative. Runtime data inputs are necessary frozen decisions/evidence, not independent pipelines. Research reports retain the rationale, rejected splits and limitations. Do not delete or move them merely because the canonical rerun no longer imports their scripts.

| ID | Role | Path |
|---|---|---|
| MASTER | runtime accepted input | [presentations/segmentation/first_run/01_ingestion/05_master_parquet/output/master_products.parquet](../01_ingestion/05_master_parquet/output/master_products.parquet) |
| MASTER_MANIFEST | runtime accepted input | [presentations/segmentation/first_run/01_ingestion/05_master_parquet/output/manifest.json](../01_ingestion/05_master_parquet/output/manifest.json) |
| LOCKED_CLAIMS | runtime accepted input | [presentations/segmentation/first_run/01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/claims_join.parquet](../01_ingestion/04_reviewed_claims/03_final_lock/wave2_ocr_llm_lock_v1/claims_join.parquet) |
| BASELINE_CLASSIFICATIONS | runtime accepted input | [presentations/segmentation/first_run/02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/subtype_assignments.csv](../02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/subtype_assignments.csv) |
| CEREAL_DECISIONS | runtime accepted input | [presentations/segmentation/first_run/02_shared_preprocessing_and_eda/02_eda/01_nutritional_composition/lens1_cereal_master_v1.parquet](../02_shared_preprocessing_and_eda/02_eda/01_nutritional_composition/lens1_cereal_master_v1.parquet) |
| SAVOURY_DECISIONS | runtime accepted input | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/savoury_snack_assignments_v1.parquet](../03_lenses/01_nutritional_composition/savoury_snack_assignments_v1.parquet) |
| BEVERAGE_DECISIONS | runtime accepted input | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/beverage_assignments_v1.parquet](../03_lenses/01_nutritional_composition/beverage_assignments_v1.parquet) |
| JUICE_DECISIONS | runtime accepted input | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/juice_assignments_v1.parquet](../03_lenses/01_nutritional_composition/juice_assignments_v1.parquet) |
| HUMAN_SOURCE | runtime accepted input | [presentations/segmentation/first_run/03_lenses/03_claims_composition_and_ingredients/human_claim_decisions_v1.csv](../03_lenses/03_claims_composition_and_ingredients/human_claim_decisions_v1.csv) |
| HUMAN_DECISIONS | runtime accepted input | [presentations/segmentation/first_run/03_lenses/03_claims_composition_and_ingredients/human_claim_adjudications_v1.csv](../03_lenses/03_claims_composition_and_ingredients/human_claim_adjudications_v1.csv) |
| BOUNDARY_EVIDENCE | runtime accepted input | [presentations/segmentation/first_run/03_lenses/04_positioning_tradeoffs/processing_boundary_evidence_v1.parquet](../03_lenses/04_positioning_tradeoffs/processing_boundary_evidence_v1.parquet) |
| FORMULATION_DECISIONS | runtime accepted input | [presentations/segmentation/first_run/03_lenses/FORMULATION_DECISIONS_v1.csv](../03_lenses/FORMULATION_DECISIONS_v1.csv) |
| COMMUNICATION_RESULTS | runtime accepted input | [presentations/segmentation/first_run/03_lenses/03_claims_composition_and_ingredients/communication_overlays_v1.csv](../03_lenses/03_claims_composition_and_ingredients/communication_overlays_v1.csv) |
| PROCESSING_RESULTS | runtime accepted input | [presentations/segmentation/first_run/03_lenses/04_positioning_tradeoffs/organic_nova_v1.csv](../03_lenses/04_positioning_tradeoffs/organic_nova_v1.csv) |
| BOUNDARY_RESULTS | runtime accepted input | [presentations/segmentation/first_run/03_lenses/04_positioning_tradeoffs/category_boundaries_v1.csv](../03_lenses/04_positioning_tradeoffs/category_boundaries_v1.csv) |
| FINAL_JUICE_SENSITIVITY | runtime accepted input | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/juice_confidence_sensitivity_v1.csv](../03_lenses/01_nutritional_composition/juice_confidence_sensitivity_v1.csv) |
| POST_V1_BACKLOG | runtime accepted input | [presentations/segmentation/first_run/03_lenses/03_claims_composition_and_ingredients/post_v1_evidence_gaps_v1.csv](../03_lenses/03_claims_composition_and_ingredients/post_v1_evidence_gaps_v1.csv) |
| FORMULATION_SYNTHESIS | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/FORMULATION_SYNTHESIS_v1.md](../03_lenses/FORMULATION_SYNTHESIS_v1.md) |
| HYPOTHESIS_CHECK | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/CHECK.md](../03_lenses/CHECK.md) |
| CEREAL_REPORT | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/cereal_formulations_v1.md](../03_lenses/01_nutritional_composition/cereal_formulations_v1.md) |
| DAIRY_REPORT | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/02_nutrient_density/dairy_dessert_formulations_v1.md](../03_lenses/02_nutrient_density/dairy_dessert_formulations_v1.md) |
| BISCUIT_REPORT | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/biscuits_and_wafers_CHECK_v1.md](../03_lenses/01_nutritional_composition/biscuits_and_wafers_CHECK_v1.md) |
| SAVOURY_REPORT | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/savoury_snacks_CHECK_v1.md](../03_lenses/01_nutritional_composition/savoury_snacks_CHECK_v1.md) |
| BEVERAGE_REPORT | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/beverages_CHECK_v1.md](../03_lenses/01_nutritional_composition/beverages_CHECK_v1.md) |
| JUICE_REPORT | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/juice_formulations_v1.md](../03_lenses/01_nutritional_composition/juice_formulations_v1.md) |
| COMMUNICATION_CHECK | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/03_claims_composition_and_ingredients/communication_overlays_CHECK_v1.md](../03_lenses/03_claims_composition_and_ingredients/communication_overlays_CHECK_v1.md) |
| PROCESSING_CHECK | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/04_positioning_tradeoffs/processing_boundaries_CHECK_v1.md](../03_lenses/04_positioning_tradeoffs/processing_boundaries_CHECK_v1.md) |
| JUICE_CORRECTION_CHECK | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/juice_classification_CHECK_v1.md](../03_lenses/01_nutritional_composition/juice_classification_CHECK_v1.md) |
| HUMAN_REVIEW_CHECK | research decision evidence/reference | [presentations/segmentation/first_run/03_lenses/03_claims_composition_and_ingredients/human_review_preparation_CHECK_v1.md](../03_lenses/03_claims_composition_and_ingredients/human_review_preparation_CHECK_v1.md) |
| ACCEPTED_NUTRIENT_COUNTS | independent validation only | [presentations/segmentation/first_run/02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/nutrient_availability.csv](../02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/nutrient_availability.csv) |
| ACCEPTED_COMMUNICATION_COUNTS | independent validation only | [presentations/segmentation/first_run/03_lenses/03_claims_composition_and_ingredients/communication_coverage_v1.csv](../03_lenses/03_claims_composition_and_ingredients/communication_coverage_v1.csv) |
| RESEARCH_DAIRY_CLASSIFIER | independent validation only | [presentations/segmentation/first_run/03_lenses/02_nutrient_density/dairy_dessert_formulations_v1.py](../03_lenses/02_nutrient_density/dairy_dessert_formulations_v1.py) |
| RESEARCH_BISCUIT_CLASSIFIER | independent validation only | [presentations/segmentation/first_run/03_lenses/01_nutritional_composition/biscuits_and_wafers_v1.py](../03_lenses/01_nutritional_composition/biscuits_and_wafers_v1.py) |
| RESEARCH_COVERAGE_COHORTS | independent validation only | [presentations/segmentation/first_run/03_lenses/03_claims_composition_and_ingredients/communication_coverage_v1.py](../03_lenses/03_claims_composition_and_ingredients/communication_coverage_v1.py) |

## Retention boundary

No files are removed or retired here. Old exploration scripts, baseline checks and the pooled control remain research provenance and independent equivalence references. They are not imported by the routine canonical build. A future housekeeping proposal must identify exact replacements and protect hashed snapshots, approved manual decisions and locked source evidence. Production, Streamlit, ingestion, OCR/LLM and the Lovable repository remain untouched.

## approved_findings_v1.json — Lovable contract

| Top-level key | Structure and interpretation |
|---|---|
| version, status, unit, hierarchy, limitations | Release metadata, exact assignment grain, three-level architecture and global interpretation limits |
| formulation | source_id plus decisions array (33 accepted register rows). Use branch/decision/scope_note with product metadata to distinguish studied variation, insufficient evidence and uninvestigated formats; see DATA_DICTIONARY.md presentation priority table |
| communication | Source ID; sugar-related display label; supported_uk_soda result and focused_exception; descriptive granola; unresolved_profile_comparisons; reused_H5; qualified other_hypotheses. Each result retains its own denominators, units and evidence role |
| processing | Conditional french_muesli, exploratory us_granola, remaining-evidence limits and the documented ambiguous-composition metadata exception |
| boundaries | Source ID, keyed output, bounded families, treatment, corrected juice counts and outside-family cautions; no automatic source recategorization |
| juice_sensitivity | Source ID, closed decision, exact exclusion predicate, removed/retained counts and saved summary rows |
| human_review | Separate keyed output, n=12, qualitative role and overrides_locked_claims=false |
| density, control, deferred | Complementary density view, completed k=5 reference and explicit alcohol/preparation/evidence deferrals |

Resolve source_id/evidence_gaps_source_id through manifest inputs/evidence_references/validation_references. Relative evidence paths inside copied research rows remain relative to their original source artifact, not output/. Profile IDs are defined in DATA_DICTIONARY.md. Do not sum overlapping coverage cohorts or infer claim absence from a missing sparse-table join. Interpret the internal catch-all profile status only through the documented presentation decision priority; unknown/uninvestigated is not a negative research conclusion.

[Release freeze receipt](RELEASE_FREEZE_v1.json) protects canonical code, data, manifest and release documentation. Historical source and evidence paths remain protected by the accepted manifest.
