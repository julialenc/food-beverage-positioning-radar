# Shared preprocessing and field-use inventory - CHECK

**Data preparation CLOSED; documentation consolidated 20 November 2026.** The corrected Wave 2 master is authoritative: retrieved 17 October 2026, reporting cutoff 29 September. The findings and dated execution record below preserve the original preparation stage. Earlier statements about future H2, feature selection or folder contents are historical; the completed [analytical design](../02_eda/00_shared_baseline_and_feature_diagnostics/H1_H12_ANALYTICAL_PLAN.md) and [lens research audit](../../03_lenses/AUDIT_v1.md) govern subsequent analysis.

This folder retains only this CHECK and [field_use_inventory_v1.py](field_use_inventory_v1.py). The reproducible inventory JSON is removed; if regenerated it is ignored by Git. Its source schema, 19 purpose-group definitions and reproduction recipe remain available. Source/master data and locked OCR/LLM stay unchanged. This cleanup does not authorize a general preparation rerun.

Availability includes observed numeric zero and does not establish measurement validity. Exact-proposition comparisons require their own positive/documented-non-detection/unknown states and eligible evidence denominator; the inventory's simple non-null/boolean summaries are historical availability context. Deliberately selected OCR/LLM evidence is not positioning prevalence. Nutrition and communicated propositions remain separate.

<a id="field-findings"></a>
## Preserved preparation findings

### Field-use inventory v1

This is the fresh preprocessing baseline for the corrected Wave 2 master, retrieved on 17 October 2026 with the 29 September reporting cutoff. The master has 374,840 governed products, 382,527 regional/category assignments and 213 fields. Product-scope eligibility includes 376,845 assignments. Master manifest (`../../01_ingestion/05_master_parquet/output/manifest.json`, local/historical evidence)

The inventory assigns every field to one of 19 purpose groups. The [versioned source](field_use_inventory_v1.py) preserves field definitions, lens uses and dispositions. The full typed JSON can be regenerated from the hash-checked master using [the reproduction instructions](#reproduction); the standalone output is no longer retained.

| Purpose | Fields | Lens use | Disposition |
|---|---:|---|---|
| Assignment identity and geography | 4 | 1–5: define units, regional/category comparisons and traceability; H12 across lenses. | Keep in every analytical extract. Preserve barcode strings and country lists. |
| Product scope and reviewed decisions | 4 | 1–5: establish product scope before lens-specific eligibility. | Use existing decisions and retain their reasons. |
| Peer-format evidence | 3 | 1: H2 cereal peers; 2–4: comparable formats where relevant; 5: interpret format effects. | Inspect cereal tags and names when defining H2. Format assignments remain open. |
| Working nutrient measurements | 8 | 1: composition; 2: energy, protein and fibre; 3: claim contrasts; 4: trade-offs; 5: candidate inputs. | Inventory availability. Select measurements separately for each question. |
| Preserved nutrient values and missing flags | 16 | 1–5: trace selected measurements and interpret missingness. | Consult within the chosen hypothesis when assessing validity. |
| Nutrition warnings and reasons | 6 | 1–5: interpret flagged records when selected measurements are used. | Retain for QA. Decide any treatment in the relevant analysis. |
| Source country and region descriptors | 3 | 1–5: consult when an assignment needs explanation. | Defer normalization. Use governed region and assignment_countries for grouping. |
| Ingredient evidence | 4 | 3: conditional H7; 4: only for a specified ingredient trade-off. | Defer parsing and language-specific cleaning until H7 feasibility review. |
| Processing classification | 1 | 4: H9/H10 if the specified trade-off involves processing. | Defer coverage and interpretation until that comparison is chosen. |
| Brand and company layers | 14 | 3: optional profiling of brand-related communication under H6. | Defer. Preserve existing governed layers. |
| Other source descriptors | 5 | No current hypothesis requires these fields. An OFF label tag has a different source from reviewed pack evidence. | Defer. Package quantity alone does not establish serving size or preparation basis. |
| Reporting controls | 2 | No analytical lens requires reporting display controls as inputs. | Retain for reporting lineage. |
| Source timestamps and image pointer | 4 | 1–5: provenance if a record needs investigation. | Defer reprocessing. Use the release manifest for wave identity. |
| Claim sample, eligibility and cohort | 6 | 3: claim denominator; 4: denominator for comparisons using pack propositions. | Apply both eligibility gates and claim-specific assessment. Keep historical reuses identifiable. |
| Claim evidence, assessment context and QA | 13 | 3–4: trace pack assessments. Consult dairy QA notes when a nutrition or population question touches those cases. | Retain evidence and QA context. Defer OCR text processing and detailed exceptions. |
| Core pack propositions and evidence states | 102 | 3: H5–H7; 4: H9–H11 when communication is part of the hypothesis. | Select propositions individually with their state and basis. Preserve unknowns. Use the locked energy-positioning indicator for H8. |
| Communicated nutrient amounts and fortification | 5 | 3: H5 where a pack amount or fortification wording matters; 4: conditional context. | Defer until needed. Keep amount basis and provenance with the claim. |
| Beverage energy positioning | 5 | 3: H8 energy positioning and format; 4: conditional on a beverage trade-off. | Use the locked derived indicator. Recorded kcal measures composition. |
| Beverage hydration and electrolyte positioning | 8 | 3: H8 benefits have separate assessments; 4: conditional on a beverage trade-off. | Retain independent v6 usability and front/content uncertainty. |

### Availability in the corrected population

The denominator is product-scope-eligible barcode/region/category assignments. Nutrient coverage counts non-null working values, including numeric zero. Availability alone does not establish measurement validity.

| Region | Eligible assignments | Energy | Sugars | Protein | Fibre |
|---|---:|---:|---:|---:|---:|
| FR | 208,902 | 81.6% | 81.0% | 81.1% | 43.1% |
| UK-IE | 23,759 | 88.2% | 86.7% | 87.1% | 62.0% |
| US-CA | 144,184 | 14.7% | 14.4% | 14.7% | 12.7% |

### Interpretation and deferred decisions

The master links 12,161 locked regional/category evidence rows, comprising 12,126 new processed observations and 35 historical dairy reuses. Joint product and claims eligibility retains 12,159 assignments. OCR/LLM coverage was deliberately selected. Claim comparisons require their own assessed populations and per-claim positive, documented-negative and unknown states. An unmatched or uncertain claim remains unknown.

Measured nutrition and communicated pack propositions remain separate. Communicated protein amounts retain their serving or weight basis. Energy positioning and the independent beverage hydration/electrolyte assessments retain their locked definitions.

Only fields needed by a chosen hypothesis proceed to analytical cleaning. The H2 cereal peer group, similarity thresholds, feature selection, feature engineering, missing-value treatment, scaling, methodology and success criteria remain to be defined under the existing learning plan (`../../../learning_plan.md`, local/historical evidence). Lens 5 retains its agreed hypothesis-free control role.

### Preparation closeout

Of 144,184 eligible US/Canada assignments, 122,886 lack all eight working nutrient measurements. The October source check found blank source nutrient fields for all 122,885 of these assignments that matched the saved source. The remaining nutrition gap after barcode correction is predominantly an upstream Open Food Facts coverage limitation. Nutritional comparisons can therefore represent a much narrower US/Canada assortment. Quantify joint coverage within each hypothesis’s peer group.

Of those 122,886 assignments, 108,327 carry ingredient text and 37,143 carry a primary image URL. These groups overlap. Across all regions, the 486 minimal-information assignments stay in the master without individual review. Retain nutrition-empty assignments for questions whose evidence requirements they meet. A missing nutrient stays missing, including when another evidence source is available.

The barcode incident and correction evidence are documented in [OBS-028](../../../../../docs/03_PROJECT_REFERENCE/05_OBSERVATIONS.md) and the correction CHECK (`../../../../../data/06_brand_governance_outputs/wave2_identity_fix_v1/CHECK.md`, local/historical evidence).

<a id="execution-log"></a>
## Historical execution record

The following describes the original four-file stage. Its dates, identities, limitations and decisions are preserved; current folder contents and reproduction are specified above and below.

### 14 November 2026 — fresh field-use inventory v1

Julia authorized a full reset of this preprocessing folder after the barcode correction. The former nutrient-coverage script/CSV, placeholder and earlier notes were removed. The field-use inventory script and output were recreated using the corrected master. New learnings and this log establish the current baseline.

The folder contains four files.

- `field_use_inventory_v1.py`
- `field_use_inventory_v1.json`
- `learnings.md`
- `logs.md`

The existing v1 naming convention and field-use logic are retained. Source provenance now includes the master path and manifest digest, with explicit retrieval/cutoff and row-count checks. The hypotheses, learning plan, governance rules and master data were verified unchanged by SHA-256.

Dependency review found that the barcode correction command's `refresh` phase still called the removed US/Canada investigation. That phase now refreshes only the current field-use inventory. The first-run guide continues to link to these learnings and this log.

#### Reproduction

Run from the repository root with the project Python.

```powershell
.\.venv\Scripts\python.exe -B presentations/segmentation/first_run/02_shared_preprocessing_and_eda/01_preprocessing/field_use_inventory_v1.py --replace
```

#### Source and output identities

| Artifact | SHA-256 |
|---|---|
| Corrected master | `ff6de2e3ef6752abbd5335a352a413940a8e6c12962bb6c85101f52ea86af912` |
| Master manifest | `70882bc27d70d7a58c047f4b917e083d57f449733d00bf797a6fcd83f1ed3b1b` |
| Inventory script | `caa0530e69dbcb818ecca5b3bf726a8a98c9f0288e1da975c3929d4f467a811d` |
| Inventory output | `9405a372c514b72af53f38a3f5c130cb696dc0133b13c392004fb07106b05152` |

#### Validation

The master digest agrees with its manifest. Retrieval, reporting cutoff and master row count match Wave 2. All 213 fields appear exactly once across 19 purpose groups. Region/category counts reconcile to the overall counts. Evidence cohorts reconcile, and claim uncertainty is retained. Replaying the inventory reproduces the output exactly. Remaining references to the removed nutrient investigation were checked.

### 14 November 2026 — data preparation closed

Julia accepted the documented source-coverage limitations and retained the complete corrected master. The next phase is hypothesis-driven EDA, starting with the cereal peer group for H2. Any further checks on energy or sugars belong to that population’s data-quality assessment. This handover records a documentation decision only. [Preparation findings](#field-findings) · Learning plan (`../../../learning_plan.md`, local/historical evidence)

<a id="reproduction"></a>
## Reproduction and dependency contract

For a deliberately requested inventory replay, from repository root:

```powershell
.\.venv\Scripts\python.exe -B presentations/segmentation/first_run/02_shared_preprocessing_and_eda/01_preprocessing/field_use_inventory_v1.py --output "$env:TEMP\fbr_field_use_inventory_v1.json" --replace
```

The unchanged script verifies the master digest, Wave 2 identity, retrieval/cutoff and row count. It reads source schema and coverage only. No retained executable consumes the old saved JSON. The historical barcode-maintenance refresh invokes this same producer and may recreate the ignored default JSON; that remains a transient output and does not require a retained export. No pipeline/production caller was changed here.

## Cleanup CHECK - 20 November 2026

- The entire saved JSON was reproduced exactly in memory before removal: 213 fields and 19 purpose groups. No output/source file was overwritten by the replay.
- Merged the original learnings and log into this CHECK, resolving current links and retaining their dated evidence. Removed the two old documents and saved JSON; the script is byte-unchanged.
- Frozen analytical-package files and dependencies remain unchanged; no new cleansing, EDA, features, models, enrichment or OCR/LLM were performed.

| Pre-cleanup artifact | SHA-256 |
|---|---|
| `learnings.md` | `2d62d514cc8ab257fde5319f5e621e1cb8e68b8fa5a5d57415d4c7241c5f4aee` |
| `logs.md` | `6cfe5fa8da7f60522eafacd12f6277b4878a7d1b82ee8cf305f86fbcf1ba5d6b` |
| `field_use_inventory_v1.json` | `9405a372c514b72af53f38a3f5c130cb696dc0133b13c392004fb07106b05152` |
| unchanged `field_use_inventory_v1.py` | `caa0530e69dbcb818ecca5b3bf726a8a98c9f0288e1da975c3929d4f467a811d` |
