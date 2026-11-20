# Reviewed cereal population and assignment master - CHECK

**Completed preparatory evidence; documentation consolidated 20 November 2026.** Corrected Wave 2: retrieval 17 October 2026, cutoff 29 September. The current folder has this CHECK, the [reviewed classification input](lens1_cereal_classification.csv), the [unchanged master builder](lens1_cereal_master_v1.py), and a local derived Parquet. Later findings are in the [shared analytical design](../00_shared_baseline_and_feature_diagnostics/H1_H12_ANALYTICAL_PLAN.md) and [lens audit](../../../03_lenses/AUDIT_v1.md). Historical open-eligibility statements below do not reopen closed research.

The CSV contains 6,700 region-GTIN review records and is a required input, not a reproducible output of the builder. It is published exactly as retained. Keep GTIN as text, including leading zeros. Original columns E/F (`cereal?`, `type`) remain separate from authoritative G-I (`review_cereal`, `review_type`, `type_code`); confidence and review priority remain separate. NO stays outside breakfast-cereal EDA; UNKNOWN is unresolved; OTHER and UNRESOLVED do not become invented subtypes. LOW confidence is not independent verification. Names/tags support format identity, not inferred nutritional or pack-claim decisions.

The local `lens1_cereal_master_v1.parquet` retains all 17,180 assignments and 67 columns, including original/reviewed labels, working/raw nutrition, missing flags and H2 eligibility. It is a current frozen release/baseline input. Keep it until the later isolated rebuild/smoke-test contract is established. No classifications, nutrition or canonical categories changed here. The 4,230 strict energy/sugars measurement pairs are assignment-level observations; later disjoint product matching is a separate analysis.

## Current identities

| Artifact | SHA-256 |
|---|---|
| Corrected master | `ff6de2e3ef6752abbd5335a352a413940a8e6c12962bb6c85101f52ea86af912` |
| Reviewed classification CSV | `912c6fce23a194ccc0eea3ffc4b8fe298e1dd6e47827e4416be60a6e10c7bcce` |
| Unchanged cereal builder | `3d1ad6118aa069fba034df4b9653ae90a4ba37b942dc2ad8d9ea24feb89bab73` |
| Retained local cereal Parquet | `2f3859a401fada540b119424a91b2a924db6c084320f175cb0c8a58119027837` |

<a id="cereal-findings"></a>
## Preserved classification and measurement findings

### H2 · Ambiguous cereal review v1

The starting population was 17,180 product-scope-eligible cereal assignments. The original regional exports covered 6,700 held rows. The table below records their first-pass proposals. The [combined classification file](lens1_cereal_classification.csv) retains these alongside the authoritative proposed revisions. Each GTIN can have an assignment in more than one region.

| Region | Held assignments | Likely breakfast cereal | Likely outside breakfast cereal | Membership uncertain | Likely cereal with proposed type |
|---|---:|---:|---:|---:|---:|
| France | 2,363 | 2,182 | 17 | 164 | 922 |
| UK/Ireland | 554 | 530 | 4 | 20 | 310 |
| US/Canada | 3,783 | 3,700 | 50 | 33 | 1,477 |

Membership and format are separate judgements. A breakfast-cereal name or a specific breakfast-cereal tag can support YES even when the evidence cannot identify a subtype. A generic grains tag alone is insufficient. Product names and format tags, including common cereal names and commercial forms, supply the decisions. Explicit bar, drink and bakery forms can support NO. Cereal-flavoured bakery and bakery-flavoured cereal require attention to the product being sold. A blank membership means the evidence is inconclusive. A blank type means the format could not be resolved. Where a discernible form such as bran has ambiguous breakfast use, type can still be populated.

These are provisional text-based decisions. Specific conflicting format cues can leave type blank even for likely cereals. Prepared porridge, infant cereal and loose granola can all meet a broad cereal description but need different peer groups. The four displayed nutrient measurements are review context only. High calories or protein alone do not establish that an item is a bar. No bar reassignment, change to H2 eligibility or examination of sugars took place. Julia's category decisions for reporting remain in force. [Category scope](../../../../../../docs/01_PRODUCT_DATA_GOVERNANCE/01_CATEGORY_SCOPE_AND_CLEANUP.md)

### Lens 1 cereal master v1 · H2 coverage and validity

The combined master retains all 17,180 eligible cereal assignments. Of these, 10,480 retain an original format assignment and 6,700 carry the proposed review layer. Effective membership is YES for 16,833, NO for 97 and UNKNOWN for 250. The five previously identified US/Canada bar-form exceptions have a separate review flag. None falls in the two H2 peer groups. H1 eligibility remains open.

Percentages use each region–format candidate count as the denominator. Numerical validity requires the existing governed physical gate and finite values within 0–900 kcal and 0–100 g sugars per 100 g, inclusive. For v1, the stricter pair check additionally requires agreement with both preserved OFF values and both missing flags. Warning-only records stay eligible. These checks do not independently verify a package label or preparation basis.

| Region | H2 format | Candidates | Both present and numerically valid | Missing flag disagreement | Pass stricter check | Both missing | Only energy missing | Only sugars missing |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| France | Granola/clusters | 1,552 | 1,446 (93.2%) | 11 | 1,435 (92.5%) | 105 | 0 | 1 |
| France | Flakes | 902 | 837 (92.8%) | 3 | 834 (92.5%) | 63 | 0 | 2 |
| UK/Ireland | Granola/clusters | 395 | 377 (95.4%) | 3 | 374 (94.7%) | 16 | 0 | 2 |
| UK/Ireland | Flakes | 228 | 215 (94.3%) | 1 | 214 (93.9%) | 13 | 0 | 0 |
| US/Canada | Granola/clusters | 2,009 | 948 (47.2%) | 3 | 945 (47.0%) | 1,056 | 1 | 4 |
| US/Canada | Flakes | 743 | 428 (57.6%) | 0 | 428 (57.6%) | 309 | 2 | 4 |
| **Total** | | **5,829** | **4,251 (72.9%)** | **21** | **4,230 (72.6%)** | **1,562** | **3** | **13** |

All 4,251 observed pairs agree with the preserved working-source values. For 21, the energy missing flag is set despite a recorded energy measurement. They remain available as numerically valid observations with an explicit disagreement status. There are 33 observed sugar zeros and two observed energy zeros across the candidate rows. One energy zero has sugars missing and the other has an observed sugar zero. US/Canada has the lowest joint coverage for each format. No similarity bands, sugar contrasts or treatment of outliers were defined.

### H2 energy and total sugars · strict pairs

Values below are median [Q1, Q3] per 100 g. All 4,230 assignments are included. Flakes show a wider middle spread of sugars in each region. The largest is US/Canada flakes at 10.0–32.4 g, alongside an energy IQR of 350–381 kcal. These are marginal distributions. The cereal master retains each product's energy–sugars pair. They do not establish a threshold for similar energy. US/Canada has substantially lower strict coverage, so comparisons describe the retained OFF assignments.

| Region | Format | Strict n | Energy, kcal | Total sugars, g | Zero energy / sugars | Any IQR outlier |
|---|---|---:|---|---|---:|---:|
| France | Granola/clusters | 1,435 | 442.5 [421, 459] | 18.0 [14, 22] | 0 / 1 | 72 |
| UK/Ireland | Granola/clusters | 374 | 441.3 [423, 465] | 16.0 [11, 19.4] | 0 / 0 | 30 |
| US/Canada | Granola/clusters | 945 | 435.5 [406.3, 466.7] | 20.0 [14.3, 23.3] | 1 / 13 | 110 |
| France | Flakes | 834 | 378.0 [373, 387] | 14.0 [7, 22] | 0 / 9 | 77 |
| UK/Ireland | Flakes | 214 | 378.0 [366.2, 387] | 14.0 [8, 22] | 0 / 0 | 12 |
| US/Canada | Flakes | 428 | 364.5 [350, 381.0] | 22.7 [10, 32.4] | 0 / 7 | 21 |

The exploratory outlier rule flags a value strictly below Q1 − 1.5×IQR or above Q3 + 1.5×IQR within its own region and format. Energy crossed a fence on 290 assignments and sugars on 42, with 10 crossing both. Of 30 observed sugar zeros, one US/Canada granola also recorded zero energy. The zero and outlier flags overlap on 17 assignments, yielding 335 distinct flagged assignments. All were retained in the original calculation. The paired observations are available in the Lens 1 cereal master (`lens1_cereal_master_v1.parquet`, local/historical evidence).

<a id="execution-log"></a>
## Historical execution and provenance

Earlier builder/output digests below identify previous builds. The current identities above govern this publication. The source command writes the derived Parquet and is an approved-rebuild recipe, not a read-only integrity check.

### 15 November 2026 · H2 ambiguous cereal review v1

The three review CSVs cover the held regional cereal assignments from the preceding names-and-tags screen. The input is the corrected Wave 2 master Parquet (`../../../01_ingestion/05_master_parquet/output/master_products.parquet`, local/historical evidence), retrieved on 17 October 2026 with the 29 September cutoff. Its SHA-256 is `ff6de2e3ef6752abbd5335a352a413940a8e6c12962bb6c85101f52ea86af912`.

The retired first-pass script reproduced the hold rule and exported the three provisional lists. Their filenames and digests below document the historical handoff. The combined classification CSV preserves the original proposals alongside the revisions.

| File | SHA-256 |
|---|---|
| h2_ambiguous_cereal_review_v1.py | `480d0246da597bfd4864f6af25ee873816ce1e2470743439b027c149c4fea411` |
| h2_ambiguous_cereal_review_fr_v1.csv | `239cc9cf2c1d369f310f6e7bf373084668de205966f1be114de34a6cf6c9ffc6` |
| h2_ambiguous_cereal_review_uk_ie_v1.csv | `b905f5993dea69abd03e73963f3d5a54f7da005ad8504b444e2a00bf220f55f5` |
| h2_ambiguous_cereal_review_us_ca_v1.csv | `5f5c8faf96716e64adbc4b8fc1f804c63ffefd259a81b4ea359f49565054503b` |

A separate read-back checked all ten headers and all 6,700 rows. Each source value was checked against the eligible regional master row, including missing nutrient cells, observed zeros and leading-zero GTINs. Brand uses the first populated value in `off_brands_raw`, `brands`, then `normalized_brand`, ignoring unknown placeholders. Picture URL uses the saved HTTP(S) image pointer. Missing pointers and the known `/invalid/` path are blank. Image content and live URL availability were not checked.

### Lens 1 cereal master v1 · build and validation

Built lens1_cereal_master_v1.parquet (`lens1_cereal_master_v1.parquet`, local/historical evidence) using [lens1_cereal_master_v1.py](lens1_cereal_master_v1.py), the corrected Wave 2 master, the original format rules and [lens1_cereal_classification.csv](lens1_cereal_classification.csv). Reproduce from the repository root with the command below. A successful replay replaces only the matching derived Parquet after read-back and scope checks.

```powershell
.\.venv\Scripts\python.exe -B presentations/segmentation/first_run/02_shared_preprocessing_and_eda/02_eda/01_nutritional_composition/lens1_cereal_master_v1.py
```

| Artifact | SHA-256 |
|---|---|
| Decision CSV | `912c6fce23a194ccc0eea3ffc4b8fe298e1dd6e47827e4416be60a6e10c7bcce` |
| Lens 1 builder | `372d2f232ff21404e4dabb2fc550a6410d0e9a2747b0d52ee50c3372f737259c` |
| Lens 1 Parquet | `b116cb77217df53c25bcf41a1537e06aad7b4d3e27843f2ae4d310c4ad28a94e` |

The assignment key is string barcode, region and canonical category. The Parquet records both input hashes and the current builder hash, and the Wave 2 release metadata. Original screen status and format, original Codex proposals on held rows, review decisions and effective membership/type are separate columns. Review-only fields are null for original-only assignments. H2 coverage flags are null outside the candidate population. The eight working nutrient measurements and their raw and missing fields carry forward without selecting an H1 feature set.

Validation reconciled unique keys, the complete original and reviewed populations, all projected source fields, the six candidate cell counts and per-row pair status against an independent read-back. The Parquet retained all 6,700 reviewed keys and their original proposals, confidence and priority. [Six-cell check](#cereal-findings)

### Classification housekeeping and H2 distributions

Renamed the decision CSV to `lens1_cereal_classification.csv` and checked its digest against the original. With Julia's approval, removed the three provisional regional exports and their script. The master builder now reads the checked combined file directly, preserves columns E–K separately and contains the original name/tag screening rules needed for the remaining 10,480 assignments. Repository reference checks identified the builder and this log as the dependent files.

After removal, rebuilt the master and compared every one of its 67 columns across all 17,180 rows against the previous Parquet. All values match. Only build provenance metadata changed. The updated builder SHA-256 is `3d1ad6118aa069fba034df4b9653ae90a4ba37b942dc2ad8d9ea24feb89bab73`. The rebuilt Parquet digest is `2f3859a401fada540b119424a91b2a924db6c084320f175cb0c8a58119027837`. The earlier digests above identify the original build.

Retired the cereal-only H2 distribution script, HTML plots, summary CSV and flagged-assignment CSV at Julia’s request after the four-category baseline was completed. Before retirement, the six panels had been checked against all 4,230 strict pairs and the 335 flagged assignments had been reconciled. The [strict-pair summary](#cereal-findings) retains those results, and the Lens 1 cereal master (`lens1_cereal_master_v1.parquet`, local/historical evidence) retains the paired measurements and eligibility fields.

### 16 November 2026 · housekeeping

Moved shared EDA into 00_shared_baseline_and_feature_diagnostics; kept five cereal files. BASELINE_CHECK.md preserves the four-category CHECK separately from the feature-design CHECK. Updated callers and manifest. Earlier open-eligibility statements are historical.

## Cleanup CHECK - 20 November 2026

- Reconstructed the existing cereal master in memory using the unchanged script and reviewed CSV; all 17,180 rows, 67 columns and schema metadata match the saved Parquet exactly. Neither the Parquet nor source evidence was rewritten.
- Classification CSV and both scripts retain exact bytes. Git attributes prevent line-ending conversion from changing CSV, script or embedded-builder identities. Read CSV identifiers as text; no spreadsheet rewrite or numeric GTIN conversion was performed.
- Merged learnings and log into this CHECK, preserving the review history, source identities, strict/observed coverage distinction and distribution/outlier cautions. Removed the two redundant Markdown files; links now resolve to this document.
- The complete corrected master, frozen 17-file analytical release and 34 pinned inputs/references remain unchanged. No new analysis, features, cleansing, OCR/LLM or model fitting. Stop before the 04_ review.

| Merged pre-cleanup document | SHA-256 |
|---|---|
| `learnings.md` | `07f170afb1f7e58d0cc0739a2d019b55c4507443b1a13ae6afd69053fd6db887` |
| `logs.md` | `0c8fba0d6a4764c20141956ea60c99f806c25e4475b633138e043dce62f7eecf` |
