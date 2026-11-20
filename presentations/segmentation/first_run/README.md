# Wave 2 segmentation — first-run navigation

**Accepted analytical package frozen on 19 November 2026. Folder publications completed on 20 November; the final isolated pipeline smoke test and broader working-file cleanup remain pending.** Retrieval: 17 October 2026. Reporting cutoff: 29 September 2026. No Wave 3 data belongs to this release.

[Permanent methodology](../SEGMENTATION.md) · [Accepted research findings](03_lenses/AUDIT_v1.md) · [Decision register](03_lenses/FORMULATION_DECISIONS_v1.csv) · [Release contract](04_analytical_package/ARTIFACT_INDEX.md)

Commercial Classification & Nutritional Formulation — CLOSED | 16 November 2026. Research is complete for the investigated product families. Five descriptive formulation profiles, commercial refinements, decisions against further subdivision and unresolved populations are retained. The hierarchy is **commercial identity → nutritional formulation → communicated positioning**; geography, density, processing and trade-offs are additional views. Descriptive thresholds are research conventions, not established natural clusters or market-prevalence estimates.

## Read in this order

| Stage | Public entry point | What remains local |
|---|---|---|
| 01 · Ingestion | [Audit, approved rules and restoration contract](01_ingestion/README.md); [master contract](01_ingestion/05_master_parquet/README.md); [master manifest](01_ingestion/05_master_parquet/output/manifest.json) | Corrected source database/master Parquet, locked claim Parquets, images, ledgers, detailed selection and original evidence. Historical sampling figures are not current analytical denominators. |
| 02 · Shared preprocessing | [Preparation CHECK](02_shared_preprocessing_and_eda/01_preprocessing/CHECK.md) and [field-use script](02_shared_preprocessing_and_eda/01_preprocessing/field_use_inventory_v1.py) | Reproducible inventory export; no new cleaning authorized. |
| 02 · Shared EDA | [Baseline/diagnostic CHECK](02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/CHECK.md) and [analytical plan](02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/H1_H12_ANALYTICAL_PLAN.md) | Detailed feature decisions, nutrient distributions and product subtype assignments. Reuse shared diagnostics across lenses. |
| 02 · Reviewed cereal input | [Cereal CHECK](02_shared_preprocessing_and_eda/02_eda/01_nutritional_composition/CHECK.md) and [classification decisions](02_shared_preprocessing_and_eda/02_eda/01_nutritional_composition/lens1_cereal_classification.csv) | Derived cereal master Parquet. Original/reviewed decisions, text GTINs and uncertainty remain distinct. |
| 03 · Research | [Consolidated audit](03_lenses/AUDIT_v1.md), [decision register](03_lenses/FORMULATION_DECISIONS_v1.csv), [shared research code](03_lenses/00_shared_research/) and [run manifest](03_lenses/00_shared_research/run_manifest_v1.json) | Original frozen reports, keyed research outputs and human evidence. The public audit consolidates their accepted conclusions. |
| 04 · Accepted release | [Artifact index](04_analytical_package/ARTIFACT_INDEX.md), [data dictionary](04_analytical_package/DATA_DICTIONARY.md), [CHECK](04_analytical_package/CHECK.md), [manifest](04_analytical_package/output/manifest_v1.json) and [freeze receipt](04_analytical_package/RELEASE_FREEZE_v1.json) | Four keyed Parquets, communication coverage CSV, findings JSON and original package logs/learnings. The JSON also contains keyed source evidence, so it is not an aggregate-only public export. |

## Five lenses, one analytical foundation

| Lens | Public code location | Scope |
|---|---|---|
| 1 · Nutritional composition | [01_nutritional_composition](03_lenses/01_nutritional_composition/) | H1–H2 and format-first cereal, snack and beverage follow-ups. |
| 2 · Nutrient density | [02_nutrient_density](03_lenses/02_nutrient_density/) | H3–H4 and dairy-dessert formulations. |
| 3 · Communication and ingredients | [03_claims_composition_and_ingredients](03_lenses/03_claims_composition_and_ingredients/) | H5–H8, communication coverage and overlays, ingredient checks and separate human interpretation. |
| 4 · Positioning trade-offs | [04_positioning_tradeoffs](03_lenses/04_positioning_tradeoffs/) | H9–H11 and bounded processing/category boundaries. |
| 5 · Unsupervised control | [05_unsupervised_control](03_lenses/05_unsupervised_control/) | One completed k=5 exploratory reference, not five universal commercial segments. |

H12 compares geographies across supported commercial populations. The shared research folder is a common implementation, not a sixth lens. Format-specific code reuses the same corrected master, classifications and feature definitions. Use the public audit for accepted interpretation; dated housekeeping checkpoints inside earlier reports describe their historical scope.

## Public code and local evidence

GitHub carries the reproducible source/decision chain and compact audit evidence. Product-level working exports, source databases, images and locked model observations are intentionally local. Reviewed classification/eligibility tables are explicit publication exceptions because they are necessary decision inputs. No review confidence label is independent package verification.

The local working documents `../learning_plan.md` and `../SEGMENTATION_HYPOTHESES_NEXT_PHASE.md` preserve scheduling and the original research hypotheses. They are not permanent public entry points. The local `logs.md`, `HOUSEKEEPING_PROPOSAL_v1.md`, `housekeeping_inventory_v1.csv` and inventory helper record maintenance history; they do not replace the published scientific decisions or frozen manifests.

Only the required shared master modules from `../production/workflow/` are public. The local `../production/README.md` and numbered future-wave operators are a separate operational route; this publication does not advertise them as a complete GitHub runnable pipeline.

## Reproduction and freeze boundary

A checkout alone cannot reproduce the data. Restore the corrected Wave 2 source/reference inputs, locked claims and accepted keyed research/output layers at the paths and hashes declared by the [ingestion contract](01_ingestion/README.md#executable-dependencies-and-restoration-contract) and [package manifest](04_analytical_package/output/manifest_v1.json). The reporting database and the standalone segmentation master are different artifacts.

The three canonical package code dependencies are [shared rules](04_analytical_package/analytical_rules_v1.py), [builder](04_analytical_package/build_analytical_package_v1.py) and [verifier](04_analytical_package/verify_analytical_package_v1.py). Accepted v1 protects 17 files and pins 34 external references. The receipt is additional to its own hash inventory. The builder refuses overwrite; after freeze the verifier checks hashes and returns stored equivalence results. That integrity check is not a fresh numerical-equivalence run or a full clean-checkout smoke test.

Historical inputs and source indexes retain their original identities. Resolve recorded paths through the [ingestion path map](01_ingestion/historical_paths.json) and documented archive mapping before checking hashes. Never delete or rewrite locked evidence to make a check pass. A future rebuild uses an approved new destination/version.

## Next checkpoint

The navigation publication changes documentation only. The next separately authorized step is the isolated full-pipeline smoke test with restored inputs and new output destinations. It must establish executable dependency closure and equivalence without altering the accepted release. No additional source ingestion, provider calls, models, data deletion or automatic future-wave processing is implied. Lovable layout/integration remains separate from the accepted analytical package.
