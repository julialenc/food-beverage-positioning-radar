# Wave 2 segmentation — first-run navigation

**Accepted analytical package frozen on 19 November 2026. Folder publications, the resource-qualified isolated smoke test and approved first-run housekeeping are complete as of 20 November.** Retrieval: 17 October 2026. Reporting cutoff: 29 September 2026. No Wave 3 data belongs to this release.

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

The local working documents `../learning_plan.md` and `../SEGMENTATION_HYPOTHESES_NEXT_PHASE.md` preserve scheduling and the original research hypotheses. They are not permanent public entry points. The local `logs.md` retains maintenance approvals, executed actions and the merged original housekeeping proposal. The obsolete inventory and generator are retired; dated references to them are historical. This ledger does not replace the published scientific decisions or frozen manifests.

Only the required shared master modules from `../production/workflow/` are public. The local `../production/README.md` and numbered future-wave operators are a separate operational route; this publication does not advertise them as a complete GitHub runnable pipeline.

## Reproduction and freeze boundary

A checkout alone cannot reproduce the data. Restore the corrected Wave 2 source/reference inputs, locked claims and accepted keyed research/output layers at the paths and hashes declared by the [ingestion contract](01_ingestion/README.md#executable-dependencies-and-restoration-contract) and [package manifest](04_analytical_package/output/manifest_v1.json). The reporting database and the standalone segmentation master are different artifacts.

The three canonical package code dependencies are [shared rules](04_analytical_package/analytical_rules_v1.py), [builder](04_analytical_package/build_analytical_package_v1.py) and [verifier](04_analytical_package/verify_analytical_package_v1.py). Accepted v1 protects 17 files and pins 34 external references. The receipt is additional to its own hash inventory. The builder refuses overwrite; after freeze the verifier checks hashes and returns stored equivalence results. That integrity check is not a fresh numerical-equivalence run or a full clean-checkout smoke test.

Historical inputs and source indexes retain their original identities. Resolve recorded paths through the [ingestion path map](01_ingestion/historical_paths.json) and documented archive mapping before checking hashes. Never delete or rewrite locked evidence to make a check pass. A future rebuild uses an approved new destination/version.

<a id="smoke-test"></a>
## Isolated rerun smoke test · PASS, 20 November 2026

Tested published commit: `df6d57eb45c6e25f5af5b0e01f64833b053d7826`. Code was exported from Git and local inputs were restored separately by SHA-256. All 24 executed project source files matched published Git identities, accounting for ordinary Windows text checkout line endings. This closure publication updates documentation only; pipeline code is unchanged from the tested commit.

| Stage | Verified result |
|---|---|
| Frozen integrity | 17 canonical files plus 34 pinned references pass; the additional receipt remains unchanged. |
| Corrected master | 374,840 products / 382,527 regional assignments; regenerated Parquet is byte-identical, including four existing category relinks. |
| Inventory and cereals | 213 fields; 17,180 cereal assignments; cereal Parquet byte-identical. |
| Shared baseline/features | All three baseline CSVs byte-identical; 376,845 eligible rows, 292,302 named peers and four approved ratio definitions pass. |
| H1–H12/control | Saved-result validator passes; H8 descriptive, H10 US/Canada granola, selected k=5 unchanged. No hypothesis statistics or models were refitted. |
| Fresh package equivalence | 393 exact cohort key sets, 96 nutrient-validity cells, 15 profile cells, 13,602 coverage cells, 377 organic/NOVA cells, 12 human observations and 32,336 boundary annotations pass. |
| Output comparison | Four Parquets match values, schemas and metadata; two CSVs are byte-identical; findings JSON differs only in accepted versus test-candidate status. |
| Original evidence | All 74 declared original input/package hashes, eight locked-output digests and 35 archived source digests remain unchanged. |

The package was regenerated in a new sibling test destination using three unchanged published canonical code files and the freshly regenerated master. The accepted receipt stayed in place. Full independent numerical/key verification ran; this was not only the frozen hash-check fast path. Workers blocked networking, provider SDK imports and subprocess dispatch. No actual provider/network attempts, source changes or evidence deletions occurred. Existing-output refusal was respected when resuming an already completed test checkpoint.

### Required alias register

Restore `data/06_brand_governance_outputs/wave2_identity_fix_v1/barcode_aliases.csv` **as well as** the corrected `release_work.db` and `manifest.json`. The alias file must match `manifest.json` → `identity_correction.aliases_sha256`:

`53de69e28d8c4d4cb4a7fda1f1ff3335086064654045fea3d9c5bd4e4323e254`

The first isolated master attempt refused category linkage while this register was missing. Restoring the existing approved register resolved the dependency; no mapping, padding policy or reviewed decision changed. GitHub contains the executable identity code; the register is an intentionally local governed input.

### Tested low-memory settings

The default Arrow mimalloc attempt exhausted memory on the approximately 5.85-GiB-RAM test machine. A bounded retry passed with these settings applied before loading the package data:

```python
import pyarrow as pa
pa.set_memory_pool(pa.system_memory_pool())
pa.set_cpu_count(1)
pa.set_io_thread_count(1)
```

The same published code, preprocessing rules and numerical comparisons were used. The PASS is qualified by this runtime configuration; default parallel execution is not certified under the same memory pressure. These settings do not disable the overwrite guard or authorize changing the accepted release. A new rerun uses a fresh approved destination and restored inputs; the installed analytical environment was reused, not reinstalled from scratch.

### Retained test evidence and limits

The compact test CHECK, harness, results, code provenance, restoration/hash manifests and stage/failure logs remain local under `outputs/first_run_smoke_v1/` at the repository root. Detailed `results.json` SHA-256: `bfecf0d5f3e52e24d303607c86fc88a3aa535f59a9afb237a407e1fbd9ecb50f`.

The larger exported checkout, regenerated datasets and two temporary work directories were removed in the approved ten-path cleanup on 20 November. Their original source/evidence files remain at canonical paths. The completed smoke workspace is retained as compact evidence and cannot be resumed; another test starts in a fresh isolated directory with exported code and restored inputs. The public results above remain independent of the removed copies.

This smoke test covers the accepted rerun from governed data and saved decisions. Historical provider work, control fitting, future-wave operators, fresh dependency installation, remote-backup recovery and live Streamlit/Lovable deployment were not tested.

## Housekeeping closure · 20 November 2026

Public code, reviewed decisions, navigation and the local restoration contract are established and the accepted rerun is tested. Julia approved the exact ten-path cleanup. The old proposal was merged byte-for-byte into the local `logs.md` before removing its standalone file, obsolete census/generator and seven smoke-copy paths. Exactly 356 files were removed across the ten targets, recovering 4,406,018,941 logical bytes (about 4.10 GiB). No additional targets were removed.

All 24 compact smoke records were retained; the local CHECK received only an appended cleanup note. Post-removal checks passed for all 74 original input/package hashes, frozen 17 canonical files and 34 pinned dependencies, eight locked-output hashes, 35 archived sources, and the presence/Git identity/syntax of 24 runtime source files. Master dependency imports, path resolution and frozen overwrite refusal pass. Historical inventory/proposal references now resolve to the merged local action record. No new numerical analysis, provider call, model fit or canonical data/evidence modification occurred. **Housekeeping is closed for the accepted first-run scope.** Further removal requires a new exact approval.

Lovable layout/integration remains separate from analytical housekeeping. Repository-wide reporting edits and future-wave operations remain outside this scoped closure.

