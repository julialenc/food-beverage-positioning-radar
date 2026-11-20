# Segmentation research audit - H1-H12 and format-first follow-ups

**Accepted Wave 2 evidence; publication consolidated 20 November 2026.** Retrieval: 17 October 2026. Reporting cutoff: 29 September 2026. This is the current public research entry point, consolidating 13 earlier narrative reports. Twelve frozen originals remain byte-identical local evidence. This is housekeeping, not another analytical RUN.

The objective is interpretable product positioning, not healthfulness, sales-weighted prevalence or market share. The accepted architecture is **commercial identity → nutritional formulation → communicated positioning**. Geography, nutrient density, processing and trade-offs are additional views. Not every format needs nutritional subsegments. Missing nutrients, measured zeros, positive claims, documented non-detection, uncertainty and unassessed evidence remain distinct.

**Public audit versus local reproduction.** Public source, accepted decisions, aggregate results and exact identities make the research auditable. Master/raw data, selected product-level evidence and required keyed matrices remain local. A GitHub clone alone is not a self-contained analytical dataset. Source identity, selection and denominators must accompany reproduced findings. The [permanent methodology](../../SEGMENTATION.md) and [first-run navigation](../README.md) define the public entry points and local-input restoration boundary; this report does not expand their scope.

After consolidation: **21 public artifacts and 31 retained local files**. Of 54 original files, 20 are public artifacts, 19 are local data/evidence files, 13 reports are consolidated here (12 local frozen originals retained), and two completed runners are retired as live files. The superseded coverage note is also removed as a live document. Exact retired source/text is recoverable from the existing [run manifest](00_shared_research/run_manifest_v1.json), without another archive folder.


<a id="current-layout"></a>
## Current layout - approved reorganization, 20 November 2026

```text
03_lenses/
  AUDIT_v1.md
  FORMULATION_DECISIONS_v1.csv
  00_shared_research/
    hypothesis_run_v1.py
    formulation_synthesis_v1.py
    validate_run_v1.py
    run_manifest_v1.json
  01_nutritional_composition/
  02_nutrient_density/
  03_claims_composition_and_ingredients/
  04_positioning_tradeoffs/
  05_unsupervised_control/
    control_comparison_v1.py
    control_comparison_v1.csv
```

This is the public layout; immutable local reports keep their original paths. The four shared files and control runner were moved, without compatibility shortcuts or duplicate entry points. Shared scripts explicitly locate the 03_lenses root; the hypothesis runner lists the five analytical lenses explicitly, so 00_shared_research cannot shift an output index. The register and all data outputs remain at their accepted locations.

The original 54-file table below is a historical disposition list; its links now point to current code locations. `relocation_v1` in the shared manifest records all five old/new paths, prior/current source hashes and recoverable previous source text. Archived reports and prior metadata retain their recorded root paths and resolve through that map. No hypotheses, methods, assertions, source observations, classifications, claims or numerical outputs changed.

Historical reorganization checkpoint (superseded by the current first-run navigation): the remaining nine files under 02_shared_preprocessing_and_eda were reviewed separately; no 02_ files are moved, deleted, published or rewritten in this reorganization. Stop before the 04_ review and defer the final clean-checkout smoke test/working-output removal until all folders are reviewed.

<a id="format-first-findings"></a>
## Commercial identity and nutritional formulation - closed

Profiles are descriptive conventions, not established natural clusters or estimates of market prevalence. Identify commercial types from names/tags independently of nutrition. HIGH/MEDIUM describes textual support, not verified package identity. Original/reviewed labels and governed source categories stay separate.

| Individual-product profile | Valid-measurement rule | FR | UK/IE | US/CA exploratory |
|---|---|---:|---:|---:|
| Granola | sugars ≤14 and protein ≥11 g/100 g in accepted cereal population | 251 | 94 | 121 |
| Dessert cream/pudding | protein ≥8 g; 10≤energy≤110 kcal/100 g | 27 | 15 | 1 |
| Potato crisps | fat ≤20 g/100 g in accepted comparable format | 100 | 90 | 53 |
| Soda | sugars ≤0.5 g/100 ml, comparable liquid | 713 | 255 | 96 |
| Energy drinks | sugars ≤0.5 g/100 ml, comparable liquid | 153 | 88 | 97 |

The [33-row decision register](FORMULATION_DECISIONS_v1.csv) preserves rules, required fields, populations, source identities and limitations. Its evidence paths identify exact local original reports; this audit consolidates their accepted interpretation publicly. Uninvestigated, unresolved, insufficient evidence, deferred and excluded scope are different outcomes.

- **Cereals:** retain the granola profile; flakes show variation without a defensible additional profile. Plain/frosted/bran or finer identities can explain some differences. Matched-energy findings describe nutrition, not actual ingredient substitutions. Carbohydrates minus sugars is not established starch; regional labelling bases differ.
- **Dairy desserts:** format is identifiable for 2,725/4,261 assignments; 1,355 unspecified, 110 conflicting and 71 comparability concerns remain broader observations. Protein pudding is recognizable but has no established natural cluster boundary. FR/UK shares are not market differences; pudding versus conventional cream wording changes the observed mix. Retain per-weight and per-calorie views.
- **Biscuits/wafers:** no further segmentation justified. Biscuits vary continuously in fat/salt/protein at similar sugars; wafer support is insufficient. Construction/coating and pooled-control format mix explain part of the contrast.
- **Savoury snacks:** the lower-fat crisp tail recurs in FR/UK (median fat about 13 versus 29–32 g/100 g; energy about 428–429 versus 512–529 kcal). Keep observed baked/fried construction. Tortilla boundaries are unstable: describe variation. Puffs are better distinguished by observable base/construction; no forced universal nutritional split. Other savoury forms remain uninvestigated within format.
- **Beverages:** preserve the RTD/preparation split and comparable measurement basis. Retain soda/energy very-low-sugars profiles and identifiable plant bases. Alcohol is excluded from nutritional segmentation; preparations remain deferred where basis is unverified. Source/reporting records remain.
- **Juice:** commercial composition explains more than another sugar profile. The bounded parent/child correction gives FR 8,558 / UK-IE 798 / US-CA 4,505 juices. French low-sugar-group salt changes from 0.30 to 0.02 g/100 ml because the population changes. Excluding exactly 1,090 newly assigned French MEDIUM-confidence juices retains 7,468, salt 0.03; apple/orange medians stay essentially unchanged and no tomato records are removed. Retain juice/nectar/fruit-drink/smoothie boundaries, composition and concentrate descriptors; zero sugars with substantial energy is discordant source data, not proof of a novel recipe.

<a id="communication-evidence"></a>
## Communicated positioning - accepted with evidence limits

Coverage is not prevalence. Show full population, matched eligible assessments, usable-market evidence, exact-proposition known positives/non-detections, uncertain/other unknown, unmatched and market-limited states separately. Assessed packs were deliberately selected.

- **UK/Irish soda:** 28/43 known profile assessments versus 1/43 outside it are positive: a selected-evidence contrast of 62.8 percentage points. Display **sugar-related communication**. The locked `sugar_free_claim` includes no-added-sugar wording and saved model assessments, not exclusively literal sugar-free wording. Cloudy Lemonade has 3.3 g sugars/100 ml and saved no-added-sugar wording. Preserve exact field, wording and provenance.
- **Granola:** protein/fibre/organic overlays are descriptive. Fibre is known for just 25/251 French and 25/94 UK/Irish qualifiers. These are small selected groups, not positioning-prevalence estimates.
- **Unresolved overlays:** protein status is known for 0/27 French and 1/15 UK cream/pudding qualifiers; reduced-fat status for 0/100 French and 3/90 UK crisp qualifiers; sugar-related status for two French and nine UK energy qualifiers. French profile soda has seven known sugar-related assessments. Retain nutritional profiles while withholding unsupported communication comparisons.
- **Selective H5-H11 reuse:** supported nutrient-claim contrasts remain format-specific. H6-H7 are narrow, H8 descriptive, H9-H10 limited. H11 cannot establish missed marketing opportunities or regulated claim qualification. US/Canada remains exploratory.

The retired coverage note's useful denominators are consolidated above; its proposed-Wednesday scope and literal sugar-free wording are superseded. Exact original text is archived. The 13,602-cell coverage CSV stays local as an independent reference; the package copy has a separate consumer role and is not deleted as a duplicate.

<a id="processing-and-boundaries"></a>
## Processing and commercial boundaries

Recorded NOVA and assessed organic communication are distinct attributes. French muesli supplies one conditional association: NOVA 4 is recorded for 6/24 organic-positive products versus 25/48 documented non-detections. This is selected evidence, not healthfulness, causality, claim compliance or prevalence. US/Canada granola remains exploratory; other cells are descriptive/insufficient. Preserve full, organic-known/unknown and NOVA-known/missing/invalid denominators separately.

Both sides of two boundaries were examined independently of nutrition: juice ↔ nectar/fruit drinks/smoothies; potato crisps ↔ popped/extruded potato snacks. Distinguish overlap, ambiguous wording, insufficient evidence and apparent misclassification. Nutrients describe consequences, not identity. This is not comprehensive category reassignment. Genuine overlapping commercial propositions remain valid.

Three historical ambiguous-composition comparability flags cover 54 FR, two UK/IE and seven US/CA assignments. The canonical rules conservatively mark these types non-comparable. All have zero joint organic/NOVA observations and no effect; no substantive finding, membership or denominator changes. Original evidence stays intact.

<a id="human-evidence"></a>
## Human evidence and post-v1 gaps

Twelve selected image records supplied two qualifiers and one comparison per primary region for cream/pudding and lower-fat crisps. Preserve Julia's submission, exact-key/image manifest and interpreted sidecar separately. Five shortened keys were reconciled against the exact manifest; leading zeros were not guessed. Eleven future recorded dates remain flagged, not silently corrected.

The sidecar has five positives, four unknown, two reported non-detections and one uncertain observation. These are qualitative examples, not another representative sample or new prevalence denominator. Human observations do not overwrite locked OCR/LLM. Names/nutrition supply no claim decisions. Public source documents exact-proposition interpretation and metadata limits; product-level submissions stay local.

The 24-arm post-v1 register is deferred. Priorities include cream/pudding protein, lower-fat crisp communication, sparse energy comparisons and selected granola propositions. Any future batch needs comparison products as well as qualifiers, exact known/unknown/unassessed denominators and image/taxonomy prerequisites. No new image assessment, OCR/LLM, provider execution or sample expansion is authorized here. Completed preparation code is archived rather than retained as a live network/selection entry point.

<a id="h1-h12-evidence"></a>
## H1-H12 and one control - historical test evidence

The original result section below retains its meaning as the exploratory test stage. Format-first conclusions above govern the final interpretation. k=5 is the completed preferred control among tested k=3–5, not five natural food segments or proof that format-first grouping is uniquely optimal. Small silhouette gains and product mix limit pooled-group interpretation. H11 describes selected-evidence non-coincidence, not marketing opportunity.


**Selected k = 5 for the single exploratory control.** It produced the most stable assignments of the three candidates and distinguished two formulations that have almost identical median sugars but different protein, fat and salt. The hypothesis-led results also show why an individual nutrient can be a poor proxy for overall formulation. Among 2,095 energy-matched cereal pairs, 1,012 (48.3%) differed by at least 5 g sugars per 100 g.

This run uses the 17 October 2026 retrieval and the 29 September cutoff. Of 376,845 governed assignments, 292,302 have confirmed analytical membership, a named format and comparable food or liquid basis. Each question then requires only its own measurements and evidence. Claims refer to the deliberately assessed packs. UK/IE and France are the primary nutritional comparisons. US/Canada estimates describe the selected measurable products. [Approved design and k amendment](../02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/H1_H12_ANALYTICAL_PLAN.md) · Feature retention by population (`../02_shared_preprocessing_and_eda/02_eda/FEATURE_DECISIONS.csv`, local/historical evidence)

## Results by hypothesis

|Question|Decision and evidence|
|-|-|
|**H1 · Recurring formulations within a format**|**Supported for high protein with low sugars.** Nine named formats exceeded independence by at least 5 percentage points in both FR and UK/IE after false-discovery adjustment. Granola exceeded expectation by 7.4 and 5.5 points respectively; cereal/protein snack bars by 7.6 and 7.5. High fat with high salt did not replicate at the same threshold. These are combinations relative to format peers.|
|**H2 · Sugars at similar energy**|**Supported in both flakes and granola.** With a 10 kcal/100 g tolerance, the share of matched pairs differing by ≥5 g sugars was 52.3% FR and 51.0% UK/IE in flakes; 44.1% and 50.5% in granola. Across all six region–format cells, 4,190 of 4,230 eligible assignments were paired once. All six cleared the 25% effect floor and the lower interval bound of 15%. The conclusion held at 5 and 20 kcal and with reversed pairing.|
|**H3 · Concentration versus per-calorie ranking**|**Replicated in five format–nutrient combinations.** For dairy desserts, 42.1% FR and 41.2% UK/IE moved at least 25 percentile points in the protein ranking. These shares changed by less than one point across the energy floors. For plant drinks, 26.6% and 26.1% moved that far in fibre ranking. This compares the same products under the two denominators.|
|**H4 · Concentration and energy trade-off**|**Replicated in six format–nutrient combinations.** Of upper-quartile protein dairy desserts, 34.9% of 944 FR products and 24.6% of 65 UK/IE products were also upper-quartile in energy and at or below median protein per kcal. The US/CA upper group had just 12 products. Both directions of the trade-off and quartile ties are recorded in the density results.|
|**H5 · Nutrient claims versus measured composition**|**Supported in 7 of 14 adequately sized comparisons.** Fibre-positioned flakes had median fibre 3.95 g/100 g higher in FR and 6.20 higher in UK/IE than peers with documented non-detection. UK/IE sugar-free soft drinks had 3.90 g/100 ml less total sugars. Selected US/CA granola showed 8.30 g/100 g higher protein; restricting positives to direct wording gave 8.08. UK/IE yogurt showed a 1.90 g protein difference, below the approved 2 g threshold. Reduced-sugar had no adequately sized cell.|
|**H6 · Similar composition, different communication**|**Supported in one of three cells with ≥30 matched pairs.** In FR juices/smoothies/nectars, 15 of 34 nutritionally close pairs differed in assessed organic communication (44.1%, bootstrap interval 26.5–61.8%). The corresponding rates were 9/79 for organic in FR cheese and 10/52 for protein in UK/IE cheese. The result is proposition- and format-specific.|
|**H7 · Ingredients versus communicated protein**|**A narrow ingredient association in two exploratory US/CA cells.** Explicit pea/soy protein wording was 35.3 points more frequent for protein-positioned granola and 43.3 points more frequent for protein-positioned cereal/protein snack bars than in the documented non-detection arms. English-tag-only estimates were 32.1 and 44.1 points. The third supported cell, UK/IE yogurt, had no phrase hits in either arm. Validation and language limitations are below.|
|**H8 · Functional beverages**|**Descriptive only.** Among 1,866 named liquids with both nutrition measurements in the eligible evidence population, 87 had positive energy positioning, 18 positive hydration and 7 positive electrolytes. For energy versus either front proposition, only 45 had both statuses known. Each table contains 39 energy-only, 1 other-proposition-only, 5 documented neither and 0 jointly positive. This small intersection cannot establish exclusivity. The energy registry separately contains 101 RTD assignments and 5 preparations. No H8 test was performed.|
|**H9 · Less-visible trade-offs**|**One of 13 comparisons cleared the prespecified criteria.** In UK/IE cheese, 20/30 reduced-fat positives versus 27/160 documented non-detections exceeded the peer sugar Q3 of 1.9 g/100 g. Difference 49.8 points (31.1–66.5). That relatively low absolute sugar threshold matters when interpreting the word “high.” The observation describes a within-cheese trade-off.|
|**H10 · Difference between territories**|**Exploratory, US/Canada granola only.** Above the peer sugar Q3 of 23.33 g/100 g were 8/42 organic-only versus 1/38 protein-only assessments. Difference 16.4 points (4.2–29.0). Four additional products had both propositions and 112 had documented non-detection for both. This is one small cell, with one above-threshold observation in the protein-only arm.|
|**H11 · Potential undercommunication**|**Documented non-detection was frequent among high-density products with known claim status.** All 15 eligible protein cells and 12 fibre cells cleared the lower-bound criterion. Across those cells, 479/628 high-protein-density assessments and 360/480 high-fibre-density assessments had documented non-detection on the assessed evidence. Unmatched and uncertain records are outside both denominators. Removing historical and QA-noted US dairy evidence leaves no informative US dairy comparison.|
|**H12 · Geography**|**Some format-specific differences; no general 10-point shift across shared formats.** Across 28 common cells the equal-weight UK/IE minus FR differences were +2.2 points for high protein/low sugars and +1.8 for high fat/high salt. Reweighting to French cell sizes gave +0.7 and +0.6. Within puffed cereals, the high-protein/low-sugars difference was +17.9 points and remained +17.1 after excluding shared barcodes. The selected US/CA subset likewise had small aggregate differences (+2.1 and +3.9 across 27 cells). No common cell supported the prespecified regional protein-claim comparison with ≥20 observations in both assessed arms in each region.|

## Control selection

The 114,146 distinct food GTINs in the FR/UK reference had valid protein, fat, total sugars and salt. Every candidate used the same reference percentile transformation, seed 42, 20 initializations, 12 identical product-bootstrap samples and the same 4,000-product silhouette evaluation sample. Stability is the median adjusted Rand index between the original and each bootstrap fit, evaluated on the complete reference population. The four nutrient medians below are in g/100 g.

|k|Median stability|Silhouette|Smallest group|Adjusted mutual information with format|
|-:|-:|-:|-:|-:|
|3|0.987|0.335|30.8%|0.364|
|4 · initial reference|0.917|0.327|18.0%|0.408|
|**5 · selected**|**0.992**|**0.337**|**17.2%**|**0.411**|

|k=5 group|Reference GTINs|Protein|Fat|Sugars|Salt|
|-|-:|-:|-:|-:|-:|
|1|26,964|22.0|28.0|0.5|1.50|
|2|21,403|5.8|24.0|19.0|0.93|
|3|20,341|8.2|14.0|18.9|0.40|
|4|25,751|3.5|3.3|20.4|0.11|
|5|19,687|6.9|34.0|39.0|0.15|

**Why stop at five?** k=3 already gave stable broad profiles. k=5 improved silhouette by only 0.002 over k=3, but groups 2 and 3 reveal a commercially interpretable distinction at nearly equal sugars: a 10 g fat difference, a 0.53 g salt difference and a 2.4 g protein difference. Both groups contain over 20,000 products. k=4 was less stable under the same resamples. All size and separation floors were met, and there was no specific unresolved formulation contrast that justified expanding the search. The result is the preferred control among the tested configurations. Format still contributes strongly: cheese makes up 88% of group 1 and chocolate confectionery 64% of group 5. Use these as exploratory formulation profiles.

The same reference transformation and centroids assigned 13,911 complete US/CA solid-food GTINs. Of these, 12,036 were unseen in training and 1,875 were shared. Projection counts describe the selected subset. The selected assignment is the `k5` column of the keyed control assignments (`05_unsupervised_control/control_assignments_v1.parquet`, local/historical evidence); the [candidate comparison and group profiles](05_unsupervised_control/control_comparison_v1.csv) retain all three candidates, original-unit quartiles, format and regional composition, and proposition-specific known denominators.

## Evidence, uncertainty and audit

* **Ingredient validation.** Codex reviewed 72 saved ingredient texts across FR, EN and BOTH tags, stratifying by detector hit, plausible near miss and other non-hit. All 24 detected texts contained explicit pea/soy protein; none of the 42 assessable non-hits did. Six non-hits carried an EN/BOTH tag but had other-language text, including a Dutch pea-protein term. On the 66 assessable texts, sampled precision and recall were both 24/24, meeting the point-estimate gates. This small agent-labelled sample has no independent human adjudication; it cannot establish general multilingual recall. The sensitivity results identify the language and known mismatches. A no-hit means the specified phrase was undetected. Keyed validation labels and ingredient texts (`03_claims_composition_and_ingredients/ingredient_validation_v1.csv`, local/historical evidence)
* **Uncertainty.** Intervals are 95% percentile bootstrap intervals using 399 replicates. Within a region–category–subtype cell each product appears once. H2 and H6 resample matched-pair outcomes. H3/H4 and H9–H11 recompute reference quantiles where relevant. H12 shares Poisson bootstrap weights across repeated GTINs and recalculates French cut points. Sensitivities cover matching direction/tolerance, energy floors, low-confidence assignments, shared barcodes, claim provenance and affected dairy evidence. Blank effects or intervals denote an insufficient arm, a tied/uninformative boundary, or a point-estimate sensitivity. They do not represent zero.
* **Multiple comparisons and units.** The result files report Benjamini–Hochberg q-values within each tested primary hypothesis. H1 uses the exact fixed-margin permutation distribution. H5 uses the pooled-median test; H7/H9/H10 use Fisher's exact test. H2/H6/H11 also report conditional binomial tests against their prespecified proportion floors. H3/H4 are descriptive replication checks, and H8 is a descriptive cross-tab. All rate effects in the CSVs are fractions. Multiply by 100 for percentage points. H5 effects and H2 median gaps are grams per applicable 100 g or 100 ml.
* **Historical reproduction.** The original root commands are retained in the frozen local result report. Current shared runners live under `00_shared_research/`; the control runner lives under `05_unsupervised_control/`. The [manifest](00_shared_research/run_manifest_v1.json) records current source identities and exact previous locations/sources. Research RUNs still require the preserved local inputs and separate authorization.

**Detailed results:** H1, H2 and cross-lens H12 (`01_nutritional_composition/hypothesis_results_v1.csv`, local/historical evidence) · H3–H4 (`02_nutrient_density/hypothesis_results_v1.csv`, local/historical evidence) · H5–H8 (`03_claims_composition_and_ingredients/hypothesis_results_v1.csv`, local/historical evidence) · H9–H11 (`04_positioning_tradeoffs/hypothesis_results_v1.csv`, local/historical evidence).



<a id="reproduction"></a>
## Reproduction and safe verification

Use the previously published [shared baseline/diagnostic CHECK](../02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/CHECK.md) and preserved local inputs. All GTIN joins use text barcode + region + category. Unknown claim evidence never becomes negative.

The hypothesis runner uses shared definitions and fixed ingredient-validation evidence; the control supplies one bounded k comparison. Follow-ups reuse those results and independent name/tag rules. Coverage, overlays and processing consume accepted keyed identities. The separate canonical consumer implementation is local `first_run/04_analytical_package/`; it reads frozen decisions and refuses accepted-v1 overwrite. Original research main functions write evidence: do not invoke them just to verify integrity.

Read-only commands from repository root:

```powershell
.\.venv\Scripts\python.exe -B presentations/segmentation/first_run/03_lenses/00_shared_research/validate_run_v1.py --check-only
.\.venv\Scripts\python.exe -B presentations/segmentation/first_run/04_analytical_package/verify_analytical_package_v1.py
```

The second verifier is a local prerequisite outside this folder's publication. The first checks saved results/source identities without rewriting its manifest. Later approved manifest refreshes preserve source archives and documentation revisions. No model, EDA, provider call or enrichment is required by housekeeping.

<a id="file-by-file-review"></a>
## File-by-file disposition - all 54 original files

GitHub means public source or concise governed/aggregate evidence. Local means required input, selected/product-level evidence or working output. Merge consolidates public narrative here; 12 frozen originals stay local, and the superseded coverage note is archived/removed as a live file. Remove retires a completed entry point while retaining exact source inside the manifest.


### Files directly under 03_lenses

| Original file | Purpose | Decision | Dependency / treatment |
|---|---|---|---|
| `CHECK.md` | Completed H1-H12 findings, uncertainty and bounded k selection. | MERGE | Frozen evidence: consolidate public narrative, preserve exact local original. Direct frozen dependency: evidence_references:HYPOTHESIS_CHECK. |
| [control_comparison_v1.py](05_unsupervised_control/control_comparison_v1.py) | Fits and evaluates the single bounded k=3-5 control. | GITHUB | Source for stability, transformation and format-dominance evidence; no new fit authorized. |
| [FORMULATION_DECISIONS_v1.csv](FORMULATION_DECISIONS_v1.csv) | 33 accepted commercial/formulation decisions with rules and lineage. | GITHUB | Small governed decision register, not a disposable exploratory export. Direct frozen dependency: inputs:FORMULATION_DECISIONS. |
| `FORMULATION_SYNTHESIS_v1.md` | Closed formulation chapter, hierarchy and accepted limitations. | MERGE | Frozen decision evidence: consolidate public narrative, preserve exact local original. Direct frozen dependency: evidence_references:FORMULATION_SYNTHESIS. |
| [formulation_synthesis_v1.py](00_shared_research/formulation_synthesis_v1.py) | Reconciles accepted profiles, populations and register lineage. | GITHUB | Necessary reproducible decision-register construction. |
| [hypothesis_run_v1.py](00_shared_research/hypothesis_run_v1.py) | Runs H1-H12 and approved sensitivities on the shared foundation. | GITHUB | Primary effect/uncertainty source; H8 descriptive, H10 US/Canada granola only. |
| [run_manifest_v1.json](00_shared_research/run_manifest_v1.json) | Research identities, environment and housekeeping source archive. | GITHUB | Public provenance and reconstructible retired sources; product datasets stay local. |
| [validate_run_v1.py](00_shared_research/validate_run_v1.py) | Checks saved results, population contracts and hashes. | GITHUB | Independent checks; preserves history and supports read-only --check-only. |

### 01_nutritional_composition

| Original file | Purpose | Decision | Dependency / treatment |
|---|---|---|---|
| `beverage_assignments_v1.parquet` | Keyed RTD/preparation identities, original/corrected juice labels and profiles. | LOCAL | Frozen input; narrower juice layer has a different role. Direct frozen dependency: inputs:BEVERAGE_DECISIONS. |
| `beverages_CHECK_v1.md` | Comparable beverage-format evidence and decisions. | MERGE | Frozen evidence: conclusions consolidated publicly, original retained locally. Direct frozen dependency: evidence_references:BEVERAGE_REPORT. |
| [beverages_v1.py](01_nutritional_composition/beverages_v1.py) | Derives beverage formats from reporting split and corrected juice rules. | GITHUB | Processing-Parquet embedded input hash; retain exact source bytes. |
| `biscuits_and_wafers_CHECK_v1.md` | Evidence against additional biscuit/wafer formulation segmentation. | MERGE | Frozen evidence: preserve negative/insufficient outcomes publicly. Direct frozen dependency: evidence_references:BISCUIT_REPORT. |
| [biscuits_and_wafers_v1.py](01_nutritional_composition/biscuits_and_wafers_v1.py) | Classifies biscuits/wafers and tests nutrients at similar sugars. | GITHUB | Frozen classifier and processing-metadata dependency. Direct frozen dependency: validation_references:RESEARCH_BISCUIT_CLASSIFIER. |
| `cereal_formulations_v1.md` | Matched pairs, granola profile and no further flakes profile. | MERGE | Frozen evidence: preserve rules, coverage and continuous-gradient conclusion publicly. Direct frozen dependency: evidence_references:CEREAL_REPORT. |
| [cereal_formulations_v1.py](01_nutritional_composition/cereal_formulations_v1.py) | Reproduces cereal pairs, screens and sensitivity evidence. | GITHUB | H2 follow-up source; reads reviewed cereal master and saved H2 results. |
| `hypothesis_results_v1.csv` | Detailed H1/H2/H12 statistics and sensitivities. | LOCAL | Read by cereal validation and original run checks. |
| `juice_assignments_v1.parquet` | Refined keyed juice composition and valid measurements. | LOCAL | Frozen input; refinements extend its beverage parent. Direct frozen dependency: inputs:JUICE_DECISIONS. |
| `juice_classification_CHECK_v1.md` | Parent-tag correction, recalculated impacts and final sensitivity closure. | MERGE | Frozen evidence: correction and superseded interpretation explained publicly. Direct frozen dependency: evidence_references:JUICE_CORRECTION_CHECK. |
| `juice_classification_correction_v1.py` | Completed one-time orchestration of the juice correction. | REMOVE | No retained importer; reusable rules/builders remain. Exact source archived; old command superseded. |
| [juice_classification_v1.py](01_nutritional_composition/juice_classification_v1.py) | Independent name/tag juice-family rules and regression fixtures. | GITHUB | Active commercial classifier and embedded processing input hash. |
| `juice_confidence_sensitivity_v1.csv` | 54 saved rows for the final French confidence sensitivity. | LOCAL | Frozen input; publish conclusion and exact exclusion predicate. Direct frozen dependency: inputs:FINAL_JUICE_SENSITIVITY. |
| [juice_confidence_sensitivity_v1.py](01_nutritional_composition/juice_confidence_sensitivity_v1.py) | Reproduces closed French sensitivity and verifies input hashes. | GITHUB | Source for accepted robustness evidence without changing identities. |
| `juice_formulations_v1.md` | Juice composition evidence and no additional nutritional profile. | MERGE | Frozen evidence: commercial distinctions and discordant nutrition retained publicly. Direct frozen dependency: evidence_references:JUICE_REPORT. |
| [juice_formulations_v1.py](01_nutritional_composition/juice_formulations_v1.py) | Derives fruit/vegetable descriptors and compares like products. | GITHUB | Active rule source and embedded processing input hash. |
| `savoury_snack_assignments_v1.parquet` | Keyed snack format, construction/base and lower-fat crisp decisions. | LOCAL | Frozen input for coverage, formulation and processing views. Direct frozen dependency: inputs:SAVOURY_DECISIONS. |
| `savoury_snacks_CHECK_v1.md` | Crisp profile, continuous tortilla variation and puff-base distinctions. | MERGE | Frozen evidence: all three distinct decisions retained publicly. Direct frozen dependency: evidence_references:SAVOURY_REPORT. |
| [savoury_snacks_v1.py](01_nutritional_composition/savoury_snacks_v1.py) | Identifies commercial snack forms and tests within-format formulations. | GITHUB | Embedded processing input hash; identities independent of nutrition. |

### 02_nutrient_density

| Original file | Purpose | Decision | Dependency / treatment |
|---|---|---|---|
| `dairy_dessert_formulations_v1.md` | Within-dessert formats, protein density and pudding profile. | MERGE | Frozen evidence: retain denominator, format and unresolved-population caveats. Direct frozen dependency: evidence_references:DAIRY_REPORT. |
| [dairy_dessert_formulations_v1.py](02_nutrient_density/dairy_dessert_formulations_v1.py) | Independent dessert classifier and concentration/density follow-up. | GITHUB | Frozen classifier imported by coverage/processing; retain exact source. Direct frozen dependency: validation_references:RESEARCH_DAIRY_CLASSIFIER. |
| `hypothesis_results_v1.csv` | Detailed H3/H4 density ranks, floors and sensitivities. | LOCAL | Dairy validation and original run checks consume it. |

### 03_claims_composition_and_ingredients

| Original file | Purpose | Decision | Dependency / treatment |
|---|---|---|---|
| `communication_coverage_CHECK_v1.md` | Tuesday coverage findings and the then-proposed Wednesday scope. | MERGE | Unpinned superseded note: consolidate denominators, archive text, remove live copy. |
| `communication_coverage_v1.csv` | 13,602 proposition-specific population/evidence denominator cells. | LOCAL | Frozen independent validation reference; package copy has a different contract role. Direct frozen dependency: validation_references:ACCEPTED_COMMUNICATION_COUNTS. |
| [communication_coverage_v1.py](03_claims_composition_and_ingredients/communication_coverage_v1.py) | Builds comparable cohorts with exact-proposition known/unknown states. | GITHUB | Frozen cohort verifier and embedded processing dependency. Direct frozen dependency: validation_references:RESEARCH_COVERAGE_COHORTS. |
| `communication_overlays_CHECK_v1.md` | Supported soda contrast, descriptive overlays and unresolved profiles. | MERGE | Frozen evidence: combine public communication findings/provenance here. Direct frozen dependency: evidence_references:COMMUNICATION_CHECK. |
| `communication_overlays_v1.csv` | Saved supported/descriptive contrasts and source provenance. | LOCAL | Frozen input; reuse statistical output without refitting. Direct frozen dependency: inputs:COMMUNICATION_RESULTS. |
| [communication_overlays_v1.py](03_claims_composition_and_ingredients/communication_overlays_v1.py) | Constructs overlays and selectively reuses H5-H11 evidence. | GITHUB | Embedded processing hash; interval and supported-comparison logic. |
| `human_claim_adjudications_v1.csv` | 12 interpreted human observations with restored keys/uncertainty. | LOCAL | Frozen separate input; qualitative examples, no locked-field overwrite. Direct frozen dependency: inputs:HUMAN_DECISIONS. |
| `human_claim_decisions_v1.csv` | Julia's original 12 observations and recorded wording. | LOCAL | Irreplaceable reviewed source, not a regenerable export. Direct frozen dependency: inputs:HUMAN_SOURCE. |
| `human_claim_review_v1.csv` | Exact review keys, images, selection arms and saved evidence. | LOCAL | Interpreter and embedded processing hash require it; preserves exact leading-zero keys. |
| `human_review_preparation_CHECK_v1.md` | Review rationale, qualitative interpretation and deferred-evidence limits. | MERGE | Frozen evidence: publish method/limits, keep product-level examples local. Direct frozen dependency: evidence_references:HUMAN_REVIEW_CHECK. |
| `hypothesis_results_v1.csv` | Detailed H5-H8 effects, matched pairs and ingredient/functional intersections. | LOCAL | Read by overlays and run validation. |
| `ingredient_validation_v1.csv` | 72 ingredient texts, strata and reviewed cue labels. | LOCAL | Reviewed H7 evidence; retain unassessable-language states and labels. |
| [ingredient_validation_v1.py](03_claims_composition_and_ingredients/ingredient_validation_v1.py) | Reconstructs fixed stratified ingredient sample and labels. | GITHUB | Auditable H7 validation source and limited agent-labelled design. |
| `post_v1_evidence_gaps_v1.csv` | 24 prioritized gap arms and image/taxonomy prerequisites. | LOCAL | Frozen backlog input; execution remains deferred. Direct frozen dependency: inputs:POST_V1_BACKLOG. |
| `prepare_human_review_v1.py` | Completed review selection and image-availability preparation. | REMOVE | No retained importer; exact source archived, original review manifest/submission retained. |
| [use_human_review_v1.py](03_claims_composition_and_ingredients/use_human_review_v1.py) | Interprets the human submission without changing locked claims. | GITHUB | Reproduces sidecar interpretation, exact-key and date limitations. |

### 04_positioning_tradeoffs

| Original file | Purpose | Decision | Dependency / treatment |
|---|---|---|---|
| `category_boundaries_v1.csv` | Saved two-sided boundary populations and nutritional consequences. | LOCAL | Frozen input; not canonical category reassignment. Direct frozen dependency: inputs:BOUNDARY_RESULTS. |
| `hypothesis_results_v1.csv` | Detailed H9-H11 coexistence, territory and non-detection results. | LOCAL | Read by run validation; public conclusions retain narrow scope. |
| `organic_nova_v1.csv` | 377 joint-evidence cells for organic status and recorded NOVA. | LOCAL | Frozen input; preserves known/unknown/NOVA-missing denominators. Direct frozen dependency: inputs:PROCESSING_RESULTS. |
| `processing_boundaries_CHECK_v1.md` | Accepted organic/NOVA and bidirectional boundary findings. | MERGE | Frozen evidence: consolidate conclusions and metadata exception publicly. Direct frozen dependency: evidence_references:PROCESSING_CHECK. |
| [processing_boundaries_v1.py](04_positioning_tradeoffs/processing_boundaries_v1.py) | Builds organic/NOVA comparisons and two independent boundary audits. | GITHUB | Own SHA and 21 input hashes embedded in evidence Parquet; retain exact bytes. |
| `processing_boundary_evidence_v1.parquet` | Keyed processing/boundary observations with embedded lineage. | LOCAL | Frozen input; feeds separate canonical boundary annotations. Direct frozen dependency: inputs:BOUNDARY_EVIDENCE. |

### 05_unsupervised_control

| Original file | Purpose | Decision | Dependency / treatment |
|---|---|---|---|
| `control_assignments_v1.parquet` | 128,057 keyed control assignments for reference/shared/unseen products. | LOCAL | Biscuit/control validation input; selected exploratory populations only. |
| [control_comparison_v1.csv](05_unsupervised_control/control_comparison_v1.csv) | 982 aggregate k evaluations, nutrient profiles, format/claim summaries. | GITHUB | One numeric control audit for all k candidates, without product keys or raw pack evidence. |


<a id="dependency-resolutions"></a>
## Dependency resolutions for every removal or merge

1. **Twelve frozen reports:** preserve exact local bytes and paths. Public narrative is consolidated here, but accepted package hashes and all decision-register evidence references still resolve to original files. Historical STOP/planning/retention wording is superseded by this current entry point.
2. **Coverage CHECK:** its useful conclusions are consolidated in Communication evidence. Its only script-based writer was the retired juice orchestrator; no retained importer reads this Markdown. Current planning links are redirected here. Exact text/hash are archived.
3. **Juice orchestrator:** no retained importer/dynamic loader. Shared juice rules and beverage/juice/coverage/overlay/synthesis/processing/sensitivity sources remain. Exact source preserves historical migration/equivalence checks without a live bulk-overwrite entry point. Accepted release consumption/verification requires no migration rerun.
4. **Human preparation:** no retained importer. Retain original review manifest, submission and public interpreter. Archived source preserves selection and historical HTTP method. Retiring it removes no reviewed data and authorizes no new network execution.
5. **Validator:** preserve existing history when writing a later authorized manifest; --check-only verifies without writes. Statistical assertions are unchanged. Previous source and both identities are recorded in the manifest.
6. **Embedded lineage:** processing Parquet has 21 input hashes plus its own processing-script identity; keep those inputs/sources exact. Juice sensitivity records source/script identities. Saved hypothesis CSVs, control assignments, ingredient labels and human manifest stay because retained consumers actually read them. A file extension or apparent duplication alone is not a removal reason.

Historical frozen reports may name retired files or earlier EDA paths. They are provenance, not current execution instructions. Resolve retired names through this audit and the source archive rather than silently rewriting frozen evidence. Current publication contains no active links to removed files.

### Exact recovery without another archive folder

`00_shared_research/run_manifest_v1.json.housekeeping_v1.source_archive` maps retired paths to exact original UTF-8 text, SHA-256, reason and replacement. Verify SHA-256 of text.encode('utf-8') before restoring into a separately approved scratch location; original line endings are preserved. `source_changes` retains the previous validator; `documentation_revisions` retains the original approved plan. Do not restore/execute legacy batches as integrity checks.

## Consolidation CHECK - 20 November 2026

- Reviewed all five subfolders and eight top-level files: 54 originals, no unclassified entries.
- Consolidated 13 report narratives; 12 direct frozen originals remain unchanged locally. Two runners and one unpinned coverage note retired as live files, with exact source/text archived.
- Public: 17 scripts, one compact control aggregate, the 33-row register, manifest/source archive and this audit = 21. Local: 14 working/review CSVs, five keyed Parquets and 12 frozen reports = 31.
- Validation covers 17 frozen canonical files, 34 pinned dependencies, original run identities, 21 embedded processing input hashes plus its script, archive recovery, saved H1-H12/control checks and retained imports. No models, EDA, provider/image requests or OCR/LLM are executed.
- Frozen digest remains `48212697d2d245e3cc543032d63699b7e83fb43ad5db8dce7cbb8714991f0557`. Master/source observations, locked claims, current classifications, accepted numerical results and human evidence remain unchanged.
- Publication is this reviewed folder plus scoped Git ignore/byte-preservation controls. Ingestion, production, Streamlit, Lovable and unrelated working changes remain outside it.

## Reorganization CHECK - 20 November 2026

- Five real file moves: four shared files into 00_shared_research and the control runner into 05_unsupervised_control; no shortcuts, old live copies or new experimental folders.
- Explicit five-lens output routing; stable feature inputs, result locations, register location and control output path.
- Current links, manifest-reader paths and active source hash identities updated. Prior manifest/scripts exactly recoverable through relocation_v1; historical source archives unchanged.
- Validate saved H1-H12/control results read-only; import all retained scripts; verify path contracts, all historical/current assertions, archived sources, embedded processing hashes and frozen release integrity. No model fitting, EDA or provider calls.
- Frozen 17-file release and 34 pinned inputs/references retain their accepted hashes. The nine reviewed 02_ files remain unchanged and outside this publication scope.
