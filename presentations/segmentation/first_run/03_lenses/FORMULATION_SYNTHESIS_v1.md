# Commercial Classification & Nutritional Formulation — CLOSED | 16 November 2026

Commercial classification and nutritional formulation research is complete for the investigated product families.

Five descriptive formulation profiles, accepted commercial refinements, decisions not to subdivide, limitations and unresolved populations are consolidated in a reproducible decision register.

The analytical hierarchy is established: **commercial identity → nutritional formulation → communicated positioning**. Not every commercial format requires further nutritional segmentation, and descriptive thresholds are not assumed to represent natural cluster boundaries.

The next phase integrates assessed on-pack communication, selected processing questions (including NOVA), nutritional trade-offs and cross-category boundary analysis.

The corrected Wave 2 master and locked OCR/LLM evidence remain unchanged.

**Interpretation at closure.** These are descriptive formulation profiles, not necessarily natural clusters. Their thresholds are research conventions, and the results are not estimates of market prevalence. The accepted hierarchy is the foundation for the next phase, with geography, nutrient density, processing and trade-offs as additional analytical views.

## The analytical architecture

1. **Commercial identity establishes peers.** Physical format, composition-based subtype, base material and construction can all supply relevant descriptors. Names and OFF tags support these fields, with corroboration where available. Unresolved identity stays in its broader category. Nutrient measurements can flag a record for checking; they cannot supply its commercial label.
2. **Formulation describes differences within those peers.** A retained profile has an individual-product rule and explicit measurement eligibility. Some branches show a continuous spectrum, some benefit from finer commercial descriptors, and some have insufficient evidence for further division. Research cutoffs remain conventional.
3. **Communicated positioning adds separately assessed evidence.** Exact-proposition positives, documented non-detection and unknown states have their own denominators. Geography cuts across the three levels. Nutrient density, trade-offs and processing supply analytical views.

The hierarchy's depth depends on the evidence in each branch. The completed k=5 control is retained as context for format influence. Its mixed product populations and small silhouette improvement over k=3 limit claims about natural commercial segments. [Original consolidated run](CHECK.md)

## Five retained descriptive profiles

| Commercial branch | Rule on valid measurements | Decision and limitation |
|---|---|---|
| Granola | Sugars ≤14 g and protein ≥11 g per 100 g | Recognizable end of a recurring gradient. French-format quartiles supply the convention. Fibre is descriptive and optional. |
| Dessert cream/pudding | Protein ≥8 g and energy 10–110 kcal per 100 g | Recognizable formulation, possibly already an established protein-pudding commercial proposition. Naming mix prevents a market interpretation of regional coverage. |
| Potato crisps | Fat ≤20 g per 100 g | Lower fat and energy recur with broadly similar protein/fibre. Preserve baked, popped or other construction evidence when observable. |
| Soda | Sugars ≤0.5 g per 100 ml convention | Recurrent near-zero-sugar end. Energy is usually lower at group level, with discordant individual records retained visibly. |
| Energy drinks | Same sugar rule within commercially identified energy drinks | Formulation and assessed energy-positioning claims are separate. The exact sugar boundary is conventional. |

The [decision register](FORMULATION_DECISIONS_v1.csv) has one row per region for each profile, including starting population, eligible population, qualifying count, missing-required count, rule, basis and source-report digest. It also records the remaining branch decisions. Counts are barcode–region–category assignments; the same GTIN can occur in several regions. Do not sum these rows to estimate market size.

**Beverage denominators need care.** Profile assignment requires valid sugars. The original energy comparison required valid sugars and energy jointly. The sugar-only profile retains 713 French sodas versus 710 in the joint comparison, 153 French energy drinks versus 151 jointly, and 96 US/Canadian sodas versus 95 jointly. These are population differences under the accepted rule. Missing energy does not become zero.

## Commercial refinements and decisions to stop

| Investigated branch | Accepted outcome |
|---|---|
| Flakes | Retain format and sugar variation. Known corn, bran, frosted and other wording can explain part of the contrast. A nutritional subdivision is unsupported. |
| Mousse and flan | Retain form and per-weight/per-calorie views. Richer fat/energy combinations change protein ranking within form. |
| Other identified dairy desserts | Retain observable forms. Regional sample limitations constrain further subdivision. |
| Biscuits | Differences survive similar-sugar comparison, but independent nutrient co-occurrence and boundary evidence are insufficient for a named profile. |
| Wafers | Keep the commercial form. Weak replicated support for an additional split. |
| Tortilla/corn chips | Report continuous fat variation. A French high-saturated-fat tail remains exploratory. |
| Puffed/extruded snacks | Prioritize base and construction, including potato, pulse and popped/stacked cues. More specific nutritional subdivision remains unsupported. |
| Plant drinks | Preserve identifiable soy, almond and other bases. Subtype identification and captured regional populations remain incomplete. |
| Juices | Fruit/vegetable distinctions, named types and blends explain much of the apparent nutritional structure. Concentrate wording is independent. No extra nutritional profile. |
| Other studied RTD formats | Retain commercial distinctions and descriptive evidence. Sparse regional arms or ambiguity limit additional profiles. |
| Preparations | Separate population. Numerical segmentation is deferred where as-sold/prepared basis is unverified. |
| Alcohol | Excluded from nutritional segmentation. Source and reporting records remain governed independently. |

This closure covers the follow-ups performed in flakes/granola, dairy desserts, biscuits/wafers, the three primary savoury formats, and the beverage forms assessed. It does not establish profiles for every cereal, cheese, yogurt, savoury nut, pretzel or other baseline subtype. The register marks these broader branches uninvestigated where appropriate.

## Unresolved populations and limitations

Unknown commercial identity remains visible. In dairy desserts, 1,536 of 4,261 assignments were unspecified, conflicting or raised comparability concerns. The identified 64% have unknown representativeness. Snack and beverage keyed layers retain unresolved and scope-caution outcomes. Juice refinement now uses 13,861 corrected juice assignments after the bounded 19 November parent/child tag correction. Original labels and unresolved boundary flags remain in the beverage layer; this is not a comprehensive recall audit of juices elsewhere.

US/Canada nutrition coverage creates selected exploratory populations. Source-valid measurements have passed the existing gate, which cannot independently certify the pack basis or every plausible value. Juice examples with zero sugar and substantial energy are nutritionally discordant and supply no evidence for unusual low-sugar formulations. The master and locked OCR/LLM layer remain the source evidence. [Master manifest](../01_ingestion/05_master_parquet/output/manifest.json)

## Canonical evidence and dependency index

| Retain as one chain | Files and dependency |
|---|---|
| Cereal evidence | [Classification, master builder and cereal Parquet](../02_shared_preprocessing_and_eda/02_eda/01_nutritional_composition/); the baseline consumes this Parquet. Retain its logs and learnings. |
| Shared foundation | [Shared baseline and feature diagnostics](../02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics/); retain both scripts, three baseline CSVs, two diagnostic CSVs, approved plan, two CHECKs and logs/learnings. All follow-up builders import the shared reader. |
| Hypothesis-led run | hypothesis_run_v1.py, its four lens result CSVs, run_manifest_v1.json and validate_run_v1.py. Cereal and dairy builders validate against original H2/H3 results. |
| Unsupervised reference | control_comparison_v1.py, [candidate results](05_unsupervised_control/control_comparison_v1.csv) and [assignments](05_unsupervised_control/control_assignments_v1.parquet). The biscuit builder reads the assignments. |
| Cereals | [Report](01_nutritional_composition/cereal_formulations_v1.md) and cereal_formulations_v1.py. The granola rule is reconciled here from the original keyed cereal cohort. |
| Dairy | [Report](02_nutrient_density/dairy_dessert_formulations_v1.md) and dairy_dessert_formulations_v1.py. Synthesis imports its commercial classifier. |
| Biscuits/wafers | [CHECK](01_nutritional_composition/biscuits_and_wafers_CHECK_v1.md) and biscuits_and_wafers_v1.py. The negative result is part of the accepted decision record. |
| Savoury snacks | [CHECK](01_nutritional_composition/savoury_snacks_CHECK_v1.md), savoury_snacks_v1.py and savoury_snack_assignments_v1.parquet. |
| Beverages | [CHECK](01_nutritional_composition/beverages_CHECK_v1.md), beverages_v1.py and beverage_assignments_v1.parquet. The juice builder reads this keyed population. |
| Juice | [Report](01_nutritional_composition/juice_formulations_v1.md), juice_formulations_v1.py and juice_assignments_v1.parquet. |
| Claims/ingredients | Keep ingredient_validation_v1.py and its keyed CSV with Lens 3 results for the next chapter. The consolidated runner reads that validation sample. |
| This closure | formulation_synthesis_v1.py, FORMULATION_DECISIONS_v1.csv and this synthesis. The register points to the existing evidence. |

The source and original run-manifest digests, script syntax, shared inputs, saved classification keys and accepted profile counts are checked by the [versioned reconciliation](formulation_synthesis_v1.py). Reproduce with the repository virtual-environment Python from any directory. This pass reconstructs eligibility and accepted rules; it does not refit the completed models or repeat EDA.

## Retention and removal proposal · awaiting Julia's review

**Closure verification passed.** The register contains 33 decisions, including 15 regional rows reproducing the five retained product-profile rules. The reconciliation verified original run-manifest hashes, shared inputs, saved classification keys and labels, corrected-source validity and script syntax. Links in this synthesis and the study entry point passed. Six placeholder files are listed below for review.

**Retain all substantive scripts and final outputs in the chains above.** Pairwise findings, rejected splits and missingness qualifications explain final decisions even where they did not produce a segment. The keyed juice file adds refinements beyond its beverage parent; the two files serve different roles. The original hypothesis results and control outputs remain inputs to existing follow-up validation and comparisons.

| Proposed removal | Dependency finding and required action before removal |
|---|---|
| .gitkeep in nonempty analytical lens folders and nonempty EDA folders | Placeholder files supply no evidence or executable input. Their folders already contain substantive files. Review the exact candidates below. |
| Empty 01_nutritional_composition/01_scope_and_hypotheses directory and its .gitkeep | First-run README previously linked here. The entry point now links to the actual cereal evidence and chapter synthesis. Remove only after approval. |
| Cache directories | None were present under 03_lenses at closure. No cache deletion is proposed. |
| Substantive files | None currently proposed. Further consolidation would need an identified replacement preserving dependencies and decision evidence. |

No deletion or retirement is performed by this closure. The proposed empty-directory removal concerns the unused stage placeholder only. Production and ingestion artifacts are outside this cleanup proposal.


Exact placeholder candidates inspected on 16 November 2026:

- 02_shared_preprocessing_and_eda/02_eda/.gitkeep
- 03_lenses/01_nutritional_composition/01_scope_and_hypotheses/.gitkeep
- 03_lenses/02_nutrient_density/.gitkeep
- 03_lenses/03_claims_composition_and_ingredients/.gitkeep
- 03_lenses/04_positioning_tradeoffs/.gitkeep
- 03_lenses/05_unsupervised_control/.gitkeep

## Recommendation for consolidation in the next phase

Distinguish the executable rerun path from the retained decision evidence and the earlier exploratory history. A candidate minimal rerun path would read the corrected master and accepted commercial decision layers, apply shared eligibility and the five approved rules, and write keyed assignments, coverage and the register. Keep the synthesis and final decision reports as the audit entry points. Earlier hypothesis tests, pair-matching explorations and the pooled control explain how the decisions were reached and can remain historical evidence.

Current imports still bind those roles together. The synthesis imports the dairy follow-up solely for its format classifier. The shared master reader also validates counts against the baseline availability CSV and supplies diagnostics used during research. Cereal and dairy reports check against the earlier hypothesis result CSVs. Biscuit research reads the pooled control assignments. These dependencies currently justify retaining those files; they need not all become runtime dependencies of the next phase.

When the next phase is consolidated, extract only the reusable commercial classifiers, nutrient validity and approved profile definitions into a shared implementation. Check equivalence against the accepted keyed decisions and counts, then redirect callers. At that point review which historical scripts or intermediate reports are fully superseded, which preserve substantive decisions, and which are still needed to reproduce a research finding. Keep one authoritative copy of each evidence layer. Present an exact retirement list with its replacements before deletion.

## Next chapter and bounded open questions

- Integrate assessed communication with meaningful commercial and formulation groups, using proposition-specific known denominators. H11 describes density/communication non-coincidence on assessed evidence.
- Complete the previously deferred targeted organic × recorded NOVA 4 comparison where joint evidence permits. Keep processing as an overlay with its own coverage and ingredient-related dependence.
- Investigate selected category boundaries across both sides, including juice/nectar/fruit drinks/smoothies/culinary products, pudding/dessert cream, biscuits/wafers/crackers/pastries, crisps/extruded potato snacks, and energy/sports drinks. Commercial overlap can be legitimate.
- Use the decision register to choose a bounded follow-up when evidence can address a material gap. Preparations and uninvestigated families retain their documented status.
