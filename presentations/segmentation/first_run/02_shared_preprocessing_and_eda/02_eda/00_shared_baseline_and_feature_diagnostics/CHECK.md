# Shared baseline EDA and feature diagnostics — CHECK

**Completed research evidence; publication consolidated 20 November 2026.** Wave 2 was retrieved 17 October 2026 with a 29 September cutoff. The sections below preserve the baseline EDA and pre-run diagnostic findings, not a new analytical RUN or current request for model approval. Subsequent format-first findings and corrected juice interpretations govern the final analytical release. Baseline subtype labels are retained as historical inputs, not replacements for later commercial refinements.

This folder publishes exactly five evidence/code files. Source/master data, locked claims, reviewed cereal inputs and the three working CSVs stay local; a GitHub clone alone is not a complete runnable analytical dataset. Scripts use the project environment and preserved local inputs. No new provider calls, modelling or source changes were performed for this publication.

Claim wording safeguard: the historical `sugar_free_claim` field includes saved no-added-sugar wording and other accepted evidence. Display it as **sugar-related communication**, not prevalence of literal sugar-free claims. Historical feasibility counts below do not change that distinction.

| GitHub file | Role |
|---|---|
| [CHECK.md](CHECK.md) | Consolidated baseline, diagnostics, learning, execution history and reproduction |
| [H1_H12_ANALYTICAL_PLAN.md](H1_H12_ANALYTICAL_PLAN.md) | Approved pre-run design; link-only publication revision |
| [h2_four_category_baseline_v1.py](h2_four_category_baseline_v1.py) | Reproducible initial classifications and nutritional baseline |
| [shared_feature_diagnostics_v1.py](shared_feature_diagnostics_v1.py) | Shared feature diagnostics and retained reader dependency |
| [nutrient_availability.csv](nutrient_availability.csv) | Small aggregate validation evidence; exact bytes preserved |

Local-only: `FEATURE_DECISIONS.csv` (771 rows, used by the research validator), `nutrient_distributions.csv` (1,784 rows, used by diagnostics), and `subtype_assignments.csv` (376,845 keyed assignments, used by the canonical release and retained research). Original barcodes remain text.

<a id="baseline-eda"></a>
## Baseline EDA · historical four-category findings

**376,845 eligible barcode–region–category assignments** from the corrected Wave 2 master, retrieved 17 October 2026 with a 29 September cutoff. Each of the eight nutrients uses its own available, valid observations. The earlier cereal scatterplots used 4,230 jointly valid energy–sugars pairs. This baseline covers the whole governed population. Source manifest: `first_run/01_ingestion/05_master_parquet/output/manifest.json` (local frozen input)

## Population and subtype decisions

| Category | Assignments | OTHER | Subtype unresolved | Membership unknown | Outside-category evidence |
|---|---:|---:|---:|---:|---:|
| Cereals | 17,180 | 691 | 3,520 | 250 | 97 |
| Snacks | 151,461 | 878 | 13,947 | 2,405 | 518 |
| Dairy | 90,608 | 93 | 3,446 | 1,643 | 4 |
| Beverages | 117,596 | 425 | 22,898 | 2,674 | 0 |

The remaining assignments have named analytical subtypes. Cereal membership, seven type codes, reviewed confidence and the five existing bar-review flags come from the Lens 1 master. For snacks, dairy and beverages, product-form wording and specific OFF tags support provisional assignments. Agreement supports high confidence. Strong single-source evidence supports medium confidence. Conflicting or broad evidence generally leaves the subtype unresolved. Missing subtype evidence and possible category contamination have separate codes. The 518 snack OUT rows include corroborated baking preparations; the four dairy OUT rows have corroborating evidence of outside formats. All remain in the tables under their canonical category. The beverage population already incorporates the locked eligibility decisions. `subtype_assignments.csv` (local keyed input)

## Coverage and selection effects

| Source energy available | France | UK/Ireland | US/Canada |
|---|---:|---:|---:|
| Cereals | 93.1% | 95.9% | 43.3% |
| Snacks | 91.1% | 92.2% | 9.9% |
| Dairy | 86.4% | 94.9% | 31.7% |
| Beverages | 65.3% | 74.0% | 6.8% |

**Coverage changes which formats a comparison represents.** In US/Canada, protein is present on 97.6% of 5,674 yogurt/cultured-fresh assignments and 10.4% of 13,396 cheese assignments. A pooled dairy protein distribution therefore gives much more weight to yogurt than the starting population does. Sugars coverage is 14.9% for snack bars and 4.8% for sugar confectionery. The underlying US/Canada OFF coverage limitation was previously documented.

Fibre has 123,139 source observations across all categories (32.7%), versus 211,298 for protein (56.1%). France cereal fibre coverage is 76.5%; France dairy fibre coverage is 37.2%. Requiring fibre in every comparison would change the retained assortment even in regions with relatively complete energy and protein data. [Consolidated availability](nutrient_availability.csv)

## Distribution contrasts and questionable tails

French medians illustrate why the commercial format matters. Each number uses the valid observations for the named nutrient.

| Comparison | Findings |
|---|---|
| Cereal · per 100 g | Granola has median energy of 442 kcal and fat of 16 g. Flakes have 378 kcal and 1.5 g fat. Median sugars are 18 and 14 g respectively. |
| Snacks · per 100 g | Chips/crisps/puffs have median sugars of 1.7 g and salt of 1.29 g. Sugar confectionery has 60.6 g sugars and 0.08 g salt. Chocolate confectionery has 20 g median saturated fat. |
| Dairy · per 100 g | Cheese has 22 g median protein and 0.5 g sugars. Yogurt/cultured fresh dairy has 3.9 g protein and 10.3 g sugars. Butter has 82 g median fat. |
| Beverages · liquid basis per 100 ml | Median sugars are 0 g for water, 7.6 g for soft drinks, 8.4 g for energy/sports drinks and 10 g for juices/smoothies/nectars. |

**Two tails deserve targeted checking before feature decisions.** French cheese has 2,574 sugar outliers among 25,775 valid values (10.0%); its median is 0.5 g, P95 is 4 g and maximum is 95 g/100 g. French liquid juices/smoothies/nectars have median salt of 0.005 g, P95 of 0.2 g and a maximum of 50 g/100 ml. A product can pass numerical checks while its subtype, nutrition basis or recorded amount still warrants inspection.

Zero-heavy distributions behave differently. Both fibre quartiles are zero for French cheese: every positive observation crosses the upper fence (1,773 of 9,414). This describes the shape of the data. It is insufficient evidence for removing a product. Across subtype–basis–metric cells, 314 have only 1–29 valid observations and one has none. `nutrient_distributions.csv` (local working output)

## Reading the tables

- **Availability.** `eligible_n` counts all governed assignments in the cell. Each metric has source-available, working-available and valid counts and percentages, plus a separate observed-zero count. Missing values contribute to the denominator only. The product keys in the assignment CSV are text; import `barcode` as Text in Excel.
- **Validity.** Within the approved physical gate, require a finite working value, agreement with the preserved OFF value, a clear missing flag and the governed bounds (0–900 kcal, 0–50 g salt, 0–100 g for the other nutrients). Warning-only observations remain. Present values with missing flags account for the gap between availability and validity: 1,521 energy, 833 carbohydrate, 128 sugars and 103 saturated-fat measurements. These counts refer to measurements and can overlap on a product.
- **Basis.** The master supplies standardized per-100 fields without a verified pack-level g/ml declaration. Identifiable foods and liquids use the documented food and liquid conventions. Distributions split even category totals by basis. Of 117,596 beverages, 67,543 fall in the liquid comparison group, 17,640 in preparation groups, 5,757 have conflicting form evidence and 26,656 have unresolved basis. Preparation, uncertain cream and oat rows remain descriptive as reported. Their statistics should not be used as ready-to-consume equivalents. No dilution or unit conversion was applied.
- **Outliers.** Each distribution row uses linear percentiles and counts valid values strictly outside Q1 − 1.5×IQR or Q3 + 1.5×IQR. Percentages use `valid_n`. Zeros and outliers remain in all statistics. `small_n` marks fewer than 30 valid observations. `ALL` means the category total; adding it to subtype rows would count assignments twice.

## Historical decisions for the next stage

Choose the first **within-format** comparison to pursue. Energy, sugars and fat merit closer examination in cereals; sugars and salt distinguish sweet and savoury snack formats; protein merits a dairy comparison within comparable products. For liquids, energy and sugars can be examined together within identified beverage formats. Before making fibre mandatory, quantify joint retention for the selected peers. Before using saturated fat with total fat, or sugars with carbohydrates, examine how much independent information the two measurements contribute. The salt and fibre tails above warrant a focused check wherever they could influence a result. Feature selection remains open.

**Validation.** The three outputs reconcile to 376,845 unique governed keys, including 149,950 assignments with a leading-zero barcode. All 17,180 cereal assignments reconcile to the frozen Lens 1 decisions. The 171 availability rows cover 12 category totals and every observed subtype in all three regions. The 1,784 distribution rows split by basis and metric. The reproduction command is in the [reproduction section](#reproduction); the executable rules are in the [versioned builder](h2_four_category_baseline_v1.py).

<a id="feature-diagnostics"></a>
## Feature diagnostics and approved design · historical findings

**The four-nutrient formulation comparison can proceed after approval. The functional-beverage and cross-territory questions need narrower outputs.** These conclusions concern feasibility. No hypothesis test or clustering model has been run. [H1–H12 decision matrix and control](H1_H12_ANALYTICAL_PLAN.md)

### Populations that determine what we can test

| Evidence population | Starting denominator | Retained | Consequence |
|---|---:|---:|---|
| Governed assignments, all four categories | 376,845 | 292,302 named comparable peers | Format-specific inference uses confirmed membership and a comparable basis. Master includes the other assignments. |
| Protein, fat, sugars and salt in named peers | 292,302 | 160,548 (54.9%) | Practical shared measurements for H1 and H6. Each separate nutrient question keeps its own denominator. |
| FR/UK solid-food control, unique GTINs | 132,541 | 114,146 (86.1%) core four | Adding fibre reduces this to 61,518. Requiring all eight retains 61,014. |
| US/Canada named solid foods for projection | 79,330 | 13,911 (17.5%) with core four | 12,036 distinct GTINs are unseen in the complete reference. US results describe these selected observations. |
| Locked claim-evidence layer | 376,845 | 12,159 (3.2%) matched and eligible | FR 4,799, UK/IE 3,594, US/CA 3,766. Within those 12,159, only 6,586 have known protein-claim status. Assessability varies by proposition. |
| H2 reviewed granola and flakes, valid energy and sugars | 4,230 | 4,111 (97.2%) have ≥5 neighbours within 10 kcal/100 g | Energy-only matching is feasible in all six region–format cells. This counts candidate products, before disjoint pairs or sugar gaps are calculated. |

**Regional interpretation.** Within named US/Canada peers, the four-nutrient requirement retains 5,312/56,034 snacks (9.5%) and 1,662/25,638 beverages (6.5%). Using the same four nutrients, 27 of 31 subtype–basis combinations have ≥30 observations in each of the three regions; 20 have ≥100. Shared cell sizes permit conditional comparisons. They do not restore the missing US assortment. H12 should use common-format FR/UK reference comparisons and show the US/Canada coverage beside every exploratory estimate. Retention detail: `FEATURE_DECISIONS.csv` (local working output)

### Features to carry forward

- **Protein, fat, total sugars and salt** describe four positioning dimensions at workable coverage. In the distinct FR/UK food reference, none has a four-feature VIF above 1.44. Including all eight gives VIFs of 118 for energy, 99 for fat and 67 for total carbohydrates. Reserve energy for matching and denominator questions. Keep fibre, saturated fat and total carbohydrate available for the comparisons that need them.
- **Parent nutrients and their components carry different information.** In the reference, fat versus saturated fat gives Pearson 0.871 and Spearman 0.845 on 117,263 products. The corresponding rank correlation is 0.969 in solid dairy and 0.758 in snacks. Total carbohydrates versus sugars gives 0.736 and 0.762 on 117,269 reference products. Use saturated fat directly for a saturated-fat question and sugars directly for a sugar question. Adding every correlated field to a distance would weight some dimensions twice. [Correlation evidence and regeneration](#correlation-evidence)
- **Density changes the available population and can amplify small denominators.** Protein density is defined on 164,278 named peers with positive energy; fibre density on 94,346. Requiring ≥10 kcal retains 162,067 and 93,237 respectively. Observed zero energy prevents another 2,278 protein and 1,349 fibre ratios even though the numerator is available. Fibre density has a median of 0.48, P99 of 5.70 and maximum of 965.25 g/100 kcal. Use ranks on identical products, split liquids from foods, and show sensitivity to the energy floor. Review extremes before interpreting individual advantages.
- **Component shares are secondary.** There are 7 sugars/carbohydrate and 2 saturated-fat/total-fat ratios above one in comparable peers. A positive denominator below 1 g occurs in 11,564 and 16,454 ratios respectively. Preserve the values and flag incoherent or fragile ratios. Use original grams for primary comparisons, within-format ranks for density, and reference-percentile scaling only for the proposed control. Formulas, zeros and tail diagnostics: `FEATURE_DECISIONS.csv` (local working output)

### Readiness by hypothesis

| Status | Scope supported by this wave |
|---|---|
| **H1–H4 ready for prespecified comparisons** | H1 tests recurring within-format nutrient combinations. H2 starts with equal-energy cereals. H3/H4 share paired concentration and density measurements; fibre and low-energy liquids have separate sensitivities. |
| **H5, H6 and H9 ready in supported peer cells** | For H5 there are 4 protein, 7 fibre, 2 reduced-fat, 1 sugar-free and 0 reduced-sugar cells with ≥20 observations in each assessed arm. H6 requires enough nutritionally close pairs after matching; heritage has no cell at the starting two-arm floor. For H9 the protein/salt, fibre/sugars and reduced-fat/sugars contrasts have 4, 7 and 2 candidate cells. |
| **H7 narrowed to one auditable ingredient cue** | 5,861 named peers in the locked layer have qualifying ingredient text; 185 mention an explicit pea/soy protein phrase. Among protein-claim positives, 98/299 have a hit; among documented non-detections, 40/2,885. These are pooled feasibility counts. Three peer cells meet the protein two-arm floor. Validate the bilingual cue before interpreting a claim relationship; none meets that floor for plant-based or no-artificial. |
| **H8 descriptive only** | In comparable liquids with usable nutrition, 45 have energy positioning and hydration jointly assessed (4 FR, 21 UK/IE, 20 US/CA); the electrolyte intersection has the same counts. Each intersection has one positive for the respective hydration/electrolyte proposition. The larger marginal populations use different evidence. Describe the 101 RTD and 5 preparations in the approved energy registry separately. |
| **H10 exploratory in one cell** | Only US/Canada granola has ≥20 organic-only and ≥20 protein-only observations with both territories assessed and sugars valid. Neither plant-based pairing has a supported cell. A general ranking of territories across markets would exceed the evidence. |
| **H11 ready in selected assessed cells** | Strictly above the peer density Q3, 15 protein cells and 12 fibre cells have ≥30 known same-proposition assessments. Use the documented non-detection denominator. Among high-density records within the selected layer, a further 803 protein and 688 fibre assessments remain unknown. |
| **H12 conditional; one control ready for approval** | H12 reuses H1 and H5 within shared formats and shows observed-assortment and selected-evidence results separately. The single control uses FR/UK solid foods, four features with initial k=4 and the approved k=3–5 comparison. Judge stability, separation and format dominance before assigning any business meaning. |

### One decision from Julia before execution

Julia approved all three decisions on 15 November 2026. For the single control, k=4 is the initial reference. Compare k=3, 4 and 5 under identical preprocessing and evaluation. Expand the range only if justified by the results. Select and document k using stability, interpretability and analytical usefulness. The local run CHECK at `first_run/03_lenses/CHECK.md` records the outcome.

1. Use the core four for H1 and the single food-only control; keep fibre, saturated fat and carbohydrate targeted. Use a 10 kcal H2 match and ≥10 kcal primary density floor with the documented sensitivities.
2. Use the matrix's proposed practical effect thresholds, uncertainty rules and sample floors. Prioritize FR and UK/IE replication where feasible; publish US/CA comparisons only with their observed coverage.
3. Keep H7 to a validated ingredient cue, H8 descriptive and H10 exploratory in the single supported comparison. No additional extraction is required.

**Audit.** The shared diagnostic pass checked the corrected master SHA-256, reconciled all 376,845 assignment keys one-to-one and reproduced all 96 region–category–nutrient valid counts from the baseline. An independent check reproduced core-four reference retention and the Pearson/Spearman coefficients and paired counts for fat/saturated fat and carbohydrates/sugars. All six correlation matrices have complete upper triangles; claim-state denominators reconcile. The five lens folders reference the same versioned implementation. [Shared implementation](shared_feature_diagnostics_v1.py) · [Baseline EDA](#baseline-eda)

<a id="correlation-evidence"></a>
## Correlation evidence and regeneration

The decision-relevant coefficients, paired counts and multicollinearity conclusions are preserved in the feature section above and the approved plan. The 468-row `FEATURE_CORRELATIONS.csv` was a reproducible diagnostic export, with no downstream executable reader. It is no longer retained. The unchanged diagnostic script regenerates both that export and the local feature-decision table when a diagnostic rerun is deliberately requested; both outputs are ignored by Git. This cleanup did not rerun correlations or feature analysis.

The availability table remains an independent accepted reference rather than being recomputed during validation. `FEATURE_DECISIONS.csv` and `nutrient_distributions.csv` remain present because current retained consumers use them. Their local-only status is not a recommendation for permanent retention.

<a id="reproduction"></a>
## Reproduction · existing implementation, local inputs required

From the repository root, with the preserved local master and reviewed cereal master available:

```powershell
.\.venv\Scripts\python.exe -B presentations/segmentation/first_run/02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/h2_four_category_baseline_v1.py
.\.venv\Scripts\python.exe -B presentations/segmentation/first_run/02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/shared_feature_diagnostics_v1.py
```

The baseline script checks master and reviewed-cereal digests, then writes the three baseline CSVs. The diagnostic script checks the master digest, reconciles classification keys and baseline valid counts, and computes the two diagnostic exports. Both commands overwrite generated outputs: use only for an approved rebuild, not as an integrity check on the frozen release. Neither was executed during this cleanup.

Preserved source identities:

- Corrected master: `ff6de2e3ef6752abbd5335a352a413940a8e6c12962bb6c85101f52ea86af912`.
- Reviewed cereal master: `2f3859a401fada540b119424a91b2a924db6c084320f175cb0c8a58119027837`.
- Locked claims: `cd79f402e21b574710194e0cd741aee5d12e00677cd3ef37651d537747d23cda`.

The original H1–H12 run manifest records environment versions (Python 3.12.4; NumPy 2.4.6; pandas 3.0.3; SciPy 1.18.0; scikit-learn 1.9.0; PyArrow 24.0.0). These are saved execution provenance, not newly selected dependencies. The original script bodies remain byte-unchanged.

## Learnings and execution log

- Four-category baseline: use metric-specific valid denominators across the full governed population; the earlier six-cell cereal H2 exercise required paired energy and sugars. Missing values never become zero. Commercial format, regional coverage and measurement basis determine comparability.
- 15 November 2026: Julia approved the consolidated H1–H12 design and bounded k=3–5 control comparison, with H8 descriptive and H10 limited to US/Canada granola.
- 16 November 2026: shared EDA moved into this folder; five cereal-specific files stayed in the cereal folder. The earlier open-feature/approval wording above is historical.
- 20 November 2026: Julia approved five GitHub files and three local working CSVs. Merged `BASELINE_CHECK.md`, `learnings.md` and `logs.md` here, corrected the obsolete baseline command, and removed the correlation export. Updated documentation links; the local research manifest records the plan revision without changing analytical results. Narrow Git ignore/byte-preservation controls support this folder only.

### Pre-cleanup artifact identities

These hashes identify the merged/retired originals; their decision content is consolidated above. The removed correlation export is reproducible from the unchanged script and retained local inputs.

| Original file | SHA-256 |
|---|---|
| `BASELINE_CHECK.md` | `f55499fb79a260d3a8511d77187134dc39c9a520db6cfc4d8f2dc941a39bfe79` |
| `CHECK.md` | `941fb484294b20073d701d071d76e3b412bc7e3046e7b1905dfa5bce4217d7ee` |
| `learnings.md` | `b3307289739350187bc844bcb3ba982a64c4a1c66b38e2261da899a5b711a2b1` |
| `logs.md` | `df12802c611ea49fcefd4a294c5ec30a93319077e3d5cee4c8d34239ad52a945` |
| `FEATURE_CORRELATIONS.csv` | `06be74558341430d55fedd7c90bd629212d74292f7b6603a9b171f15c1cae20a` |
| `H1_H12_ANALYTICAL_PLAN.md` | `179ee58b3ffe18f2036694ae0453a32929fa0c73fcaed1334ae312d072d29730` |

### Cleanup validation

The five public artifacts, three ignored local CSVs and temporary correlation-output ignore rule define this folder's publication scope. Validation checks syntax/imports without executing research main functions; reconciles all eight nutrient counts in the aggregate reference; verifies relative public links and merged anchors; checks historical manifest identities and the frozen release's 17 canonical files plus 34 pinned inputs/references. No nutritional values, claims, classifications, methods, hypothesis results or models changed. Commit/push is limited to this scope; other working-tree changes remain unpublished.
