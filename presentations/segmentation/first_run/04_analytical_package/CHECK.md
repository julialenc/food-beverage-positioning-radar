# Friday analytical consolidation — CHECK v1

**PASS — accepted frozen v1.** Friday 20 November scope, executed 19 November 2026. No deletions, historical reruns, model fitting, provider calls, GitHub push, Streamlit changes or Lovable integration. Master and locked evidence are unchanged.

## What changed

One shared rule implementation and one build command now produce canonical keyed assignments, sparse communication, separate human observations, boundary annotations, population/evidence summaries and accepted findings. Routine execution reads frozen master and approved decisions; it does not import research runners or repeat preprocessing/EDA/models. The separate verifier uses retained decision evidence for independent equivalence. [Artifact index](ARTIFACT_INDEX.md) · [Data dictionary](DATA_DICTIONARY.md) · [Manifest](output/manifest_v1.json).

## Populations and profiles

382,527 master assignments are retained; 376,845 are product-scope eligible and 5,682 remain explicitly outside scope. All keys preserve barcode strings and region/category assignments. 12,161 locked pack-assessment rows remain a sparse separate layer, including ineligible source observations. Unmatched records retain unknown communication. All 12 human observations remain qualitative and separate.

| Profile | FR | UK/IE | US/CA |
|---|---:|---:|---:|
| granola | 251 | 94 | 121 |
| dessert cream/pudding | 27 | 15 | 1 |
| potato crisps | 100 | 90 | 53 |
| soda | 713 | 255 | 96 |
| energy drink | 153 | 88 | 97 |

These five profiles reproduce the accepted 15 regional cells and exact product memberships. They are descriptive research rules, not natural clusters or market-prevalence estimates. Other formats retain commercial distinctions, continuous variation, uncertainty, deferrals or uninvestigated status. The k=5 control remains a completed reference, not final food segmentation.

## Evidence and interpretation carried forward

The corrected juice assignments remain FR 8,558 / UK-IE 798 / US-CA 4,505 with original and reviewed labels, textual confidence and reasons. The final 1,090-record French sensitivity remains closed and stable; no record is deleted. HIGH/MEDIUM does not mean independently verified identity. The discarded French fruit-drink regional contrast stays withdrawn.

UK/Irish soda retains the selected 28/43 versus 1/43 comparison under **sugar-related communication**, with saved wording and the Cloudy Lemonade exception. Granola overlays remain descriptive; sparse cream/pudding, crisp and energy-drink communication remains unresolved. H8 stays descriptive and H10 stays US/Canada granola only. H11 is not a marketing-opportunity estimate.

French muesli organic × recorded NOVA 4 stays conditional on selected jointly known observations (6/24 versus 25/48). No healthfulness, causality, claim-compliance or market-prevalence inference. NOVA and pack communication are overlays, not nutritional clustering requirements. Preparations retain unverified basis; alcohol stays outside nutritional segmentation while source records remain.

## Equivalence and integrity

| Check | Result |
|---|---:|
| master_rows | 382527 |
| eligible_assignments | 376845 |
| outside_scope_retained | 5682 |
| nutrient_validity_cells | 96 |
| corrected_juice_keys_and_nutrition | 13861 |
| dairy_classifier_assignments | 4261 |
| biscuit_classifier_assignments | 30695 |
| exact_cohort_key_sets | 393 |
| communication_coverage_cells | 13602 |
| approved_regional_profile_cells | 15 |
| locked_assessments_preserved | 12161 |
| separate_human_observations | 12 |
| unchanged_boundary_annotations | 32336 |
| documented_comparability_metadata_exceptions | 3 |
| organic_nova_population_cells | 377 |
| claim_unknown_and_zero_denominator_guards | PASS |
| input_output_hashes_and_document_links | PASS |

Verification compares every raw nutrition/source field, exact saved juice nutrition, all derived profile populations and overlapping coverage cohort key sets, all 13,602 proposition-specific coverage cells, all 377 organic/NOVA population counts, accepted classifier outputs, all matched claim source fields, 12 human rows, 32,336 boundary annotations and frozen input hashes. The accepted statistical results are reused without refitting; their supporting populations are verified. Missing and recorded-zero guards pass.

**Documented metadata exception:** the historical organic/NOVA table marks three ambiguous-composition groups as comparable (54 FR, 2 UK/IE and 7 US/CA assignments). Canonical rules correctly mark ambiguous composition non-comparable under the approved uncertainty framework. Each group has zero joint organic/NOVA observations and no reported effect; no membership, denominator or substantive finding changes. The original table and evidence are preserved. This is not a new nutritional classification or comparison.

## Reproduce, review and stop

From the repository: `.venv/Scripts/python.exe -B presentations/segmentation/first_run/04_analytical_package/build_analytical_package_v1.py`, then `.venv/Scripts/python.exe -B presentations/segmentation/first_run/04_analytical_package/verify_analytical_package_v1.py`.

Julia accepted the consolidated analytical contract and authorized the freeze after the presentation-status and release-contract clarifications. The seven output artifacts retain all analytical values; only the findings JSON release-status metadata is promoted. The internal catch-all must be resolved through the documented presentation decision priority. [Freeze receipt](RELEASE_FREEZE_v1.json) protects canonical code, outputs, manifest and release documentation. Builder overwrite is refused; verification is read-only. Housekeeping requires a separate exact proposal and Julia's approval before any deletion, rename or move. The package remains local and unconnected to Lovable. **STOP before housekeeping mutations.**
