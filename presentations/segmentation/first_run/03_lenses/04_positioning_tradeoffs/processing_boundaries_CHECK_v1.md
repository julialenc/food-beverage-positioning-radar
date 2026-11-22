# Processing and category boundaries — CHECK v1

Thursday 19 November scope, executed 2026-11-19. Corrected Wave 2: retrieved 17 October, cutoff 29 September 2026. **Complete for Julia's review; Friday consolidation has not started.**

| Question | Decision | Release implication |
| --- | --- | --- |
| Organic × NOVA 4, French muesli | RETAIN selected-evidence association | Organic-positive: 6/24 NOVA 4; non-detection: 25/48. Evidence is narrow and not independently replicated in UK/IE. |
| US/CA granola | DESCRIPTIVE ONLY | Selected exploratory evidence; no population positioning or processing prevalence. |
| Other resolved organic/NOVA cells | INSUFFICIENT EVIDENCE | Joint arm sizes, not full product counts, limit comparison. Broad/unresolved parents stay descriptive. |
| Juice-family commercial boundaries | RETAIN corrected analytical labels and unresolved flags | Shared name/tag classifier corrected 19 November; original labels retained alongside corrected labels. See juice_classification_CHECK_v1.md. No source recategorization. |
| Potato constructions | RETAIN commercial descriptors; DESCRIPTIVE ONLY nutritionally | Popped, puffed/stacked and unspecified construction are not interchangeable. No new nutritional segment. |
| Human review | RETAIN qualitative examples | All 12 submitted observations and the interpreted sidecar remain separate and unchanged. |

## Organic × recorded NOVA 4

Organic-positive means communication in the locked field; documented non-detection concerns only the assessed pack evidence, not proof that a product is non-organic. Compare these selected observations within region and commercial type. Recorded NOVA is a separate, crowdsourced attribute, partly dependent on ingredient information. This is not a healthfulness, causal or claim-compliance test. Unknown claims and missing NOVA stay outside the relevant comparison, without deletion from the master.

| Commercial type | Region | Full n | Organic + / documented non-detection / unknown | NOVA known / unavailable | NOVA 4: organic+ vs non-detection | Difference pp [95% CI] | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| syrup/concentrate | FR | 3439 | 18 / 56 / 3365 | 1804 / 1635 | 9/11 vs 34/35 | not estimated | insufficient evidence |
| tea/infusion preparation | FR | 4027 | 20 / 22 / 3985 | 1758 / 2269 | 4/10 vs 5/15 | not estimated | insufficient evidence |
| FLAKES | US-CA | 743 | 13 / 49 / 681 | 592 / 151 | 5/12 vs 19/36 | not estimated | insufficient evidence |
| GRANOLA | FR | 1552 | 26 / 101 / 1425 | 1131 / 421 | 6/19 vs 46/76 | not estimated | insufficient evidence |
| GRANOLA | US-CA | 2009 | 50 / 150 / 1809 | 1555 / 454 | 13/30 vs 67/94 | -27.9 [-45.9, -7.9] | descriptive only: exploratory US-CA comparison |
| MUESLI | FR | 1222 | 37 / 70 / 1115 | 738 / 484 | 6/24 vs 25/48 | -27.1 [-45.8, -2.9] | retain selected-evidence comparison |
| biscuit | FR | 15864 | 25 / 106 / 15733 | 10084 / 5780 | 15/19 vs 66/78 | not estimated | insufficient evidence |

Support floor, fixed before this comparison: at least 20 jointly known records in each arm and an adequately resolved commercial type. This is a pragmatic minimum, not a guarantee of representativeness or statistical power. Smaller arms retain counts only. Heterogeneous parent categories and unresolved types retain coverage without inferential promotion. US/Canada remains exploratory. No cross-format or cross-region pooled estimate is calculated.

Supported cells use organic-positive minus documented-non-detection risk differences, Newcombe/Wilson 95% intervals and two-sided Fisher exact tests. Benjamini–Hochberg q values cover supported FR/UK comparisons only. Intervals describe sampling uncertainty conditional on these selected observations; they cannot remove selection bias. A non-significant result is not proof of equivalence.

| Type | Region | p | q (primary family only) |
| --- | --- | --- | --- |
| GRANOLA | US-CA | 0.00812 | — |
| MUESLI | FR | 0.04292 | 0.04292 |

All commercial types, including insufficient-evidence and parent-context rows, are retained in `organic_nova_v1.csv`. Its mutually exclusive organic states distinguish positive, documented non-detection, separate human-negative, uncertain, other assessed unknown, unassessed and market-limited records. NOVA 1–4 is recorded/available; missing and invalid codes are separate. Full populations form one disjoint 376,845-assignment partition. Nutrient completeness is not required. Exact organic state, basis, cohort and saved evidence JSON are retained in the keyed table; no human-review observations are merged into the locked comparison.

## Category boundaries: two-sided text evidence

The full governed beverage and snack populations were screened in both directions. Current labels, source name/tags, independent cues, derived identity and uncertainty stay separate. Parent tags are not proof of a specific child identity. Nutrition never enters classification. These are text-supported candidates, not final package adjudications; implicit or unrecognized-language descriptions can be missed. Counts are assignments, not market prevalence.

### Juice Family

| Region | Full category screened | Boundary candidates | Name support | Specific tag support | Corroborated | Overlap cues | Unresolved identity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FR | 66659 | 13997 | 10871 | 12351 | 9086 | 702 | 2857 |
| UK-IE | 6362 | 1258 | 892 | 1122 | 750 | 80 | 233 |
| US-CA | 44575 | 7828 | 7385 | 2049 | 1571 | 338 | 1673 |

| Original analytical side | FR n | UK/IE n | US/CA n |
| --- | --- | --- | --- |
| juice | 3046 | 782 | 4733 |
| nectar | 2130 | 22 | 305 |
| fruit drink | 5757 | 124 | 709 |
| smoothie | 596 | 174 | 725 |
| other current labels | 2468 | 156 | 1356 |

| Evidence outcome | FR n | UK/IE n | US/CA n |
| --- | --- | --- | --- |
| adjacent commercial identity with juice-family wording | 36 | 4 | 22 |
| apparent analytical-label mismatch | 6 | 2 | 7 |
| conflicting name and specific tags | 181 | 41 | 63 |
| insufficient specific identity evidence | 148 | 40 | 51 |
| juice name conflicts with more-specific child tags | 56 | 2 | 4 |
| multiple identities in product name | 37 | 2 | 197 |
| non-comparable intended use or preparation wording | 4 | 0 | 2 |
| overlapping commercial identity; preserve unresolved | 18 | 4 | 36 |
| overlapping or conflicting specific evidence | 8 | 3 | 4 |
| scope or preparation-basis concern | 2369 | 137 | 1294 |
| supported corrected identity | 11134 | 1023 | 6148 |

### Potato Constructions

| Region | Full category screened | Boundary candidates | Name support | Specific tag support | Corroborated | Overlap cues | Unresolved identity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FR | 75282 | 3495 | 246 | 3420 | 208 | 475 | 26 |
| UK-IE | 10500 | 1041 | 166 | 982 | 148 | 101 | 32 |
| US-CA | 65679 | 4717 | 3813 | 1792 | 1081 | 112 | 157 |

| Original analytical side | FR n | UK/IE n | US/CA n |
| --- | --- | --- | --- |
| potato crisps | 2932 | 825 | 4273 |
| puffed/extruded | 409 | 128 | 300 |
| other current labels | 154 | 88 | 144 |

| Evidence outcome | FR n | UK/IE n | US/CA n |
| --- | --- | --- | --- |
| conflicting name/tag base evidence | 12 | 10 | 49 |
| conflicting or mixed construction evidence | 0 | 0 | 1 |
| independent other-base evidence | 10 | 15 | 92 |
| insufficient potato-base evidence | 8 | 19 | 97 |
| potato base known; snack construction unresolved | 3 | 0 | 0 |
| scope concern | 3 | 3 | 10 |
| supported construction with overlapping crisp descriptor | 469 | 100 | 110 |
| supported potato construction | 20 | 3 | 19 |
| supported potato-crisp identity | 2970 | 891 | 4339 |

## Nutrition describes consequences, not identity

| Boundary | Region | Population choice | n | Energy median (valid n) | Sugars median (valid n) | Fat median (valid n) | Salt median (valid n) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| juice family | FR | current juice (corrected assignment) | 8558 | 45.00 (7599) | 9.80 (7550) | 0.10 (7564) | 0.01 (7093) |
| juice family | FR | current fruit drink (corrected assignment) | 102 | 41.67 (99) | 9.58 (99) | 0.00 (99) | 0.01 (94) |
| juice family | FR | independently supported juice (all origins) | 8562 | 45.00 (7603) | 9.80 (7554) | 0.10 (7568) | 0.01 (7097) |
| juice family | FR | independent fruit drink | 103 | 41.67 (100) | 9.44 (100) | 0.00 (100) | 0.02 (95) |
| juice family | UK-IE | current juice (corrected assignment) | 798 | 44.00 (745) | 9.40 (746) | 0.10 (744) | 0.01 (648) |
| juice family | UK-IE | current fruit drink (corrected assignment) | 40 | 22.50 (38) | 4.65 (38) | 0.00 (38) | 0.01 (36) |
| juice family | UK-IE | independently supported juice (all origins) | 800 | 44.00 (747) | 9.40 (747) | 0.10 (746) | 0.01 (650) |
| juice family | UK-IE | independent fruit drink | 40 | 22.50 (38) | 4.65 (38) | 0.00 (38) | 0.01 (36) |
| potato constructions | FR | current potato crisps | 2932 | 527.00 (2787) | 0.90 (2797) | 32.00 (2807) | 1.22 (2796) |
| potato constructions | FR | explicit popped potato construction | 17 | 413.00 (17) | 4.40 (17) | 10.50 (17) | 1.40 (17) |
| potato constructions | FR | explicit puffed/extruded/stacked potato; no popped wording | 472 | 508.00 (447) | 3.30 (447) | 29.00 (444) | 1.40 (447) |
| potato constructions | UK-IE | current potato crisps | 825 | 509.00 (765) | 1.80 (768) | 28.80 (773) | 1.20 (754) |
| potato constructions | UK-IE | explicit popped potato construction | 14 | 429.41 (14) | 2.20 (13) | 13.00 (14) | 1.10 (14) |
| potato constructions | UK-IE | explicit puffed/extruded/stacked potato; no popped wording | 89 | 517.25 (82) | 2.50 (83) | 30.00 (83) | 1.49 (84) |

**Juice correction, 19 November.** The shared classifier now prevents broad parent tags from overriding specific commercial identity. Original fruit-drink assignments now supported as juice: FR: 5,606, including 4,518 name/tag-corroborated; UK-IE: 47, including 35 name/tag-corroborated; US-CA: 28, including 20 name/tag-corroborated. Original labels remain in the keyed audit and beverage file. Conflicting names/specific tags, insufficient evidence and incompatible intended-use wording remain unresolved. This is an analytical correction; governed source categories and observations are unchanged. Nested tags can describe compatible parent/child identities; juice wording in tea, coconut water or soda may indicate ingredients or overlapping propositions. Outside-family boundary flags do not automatically reclassify those products.

The beverage/juice layers, nutrition summaries, claim coverage and recorded-NOVA denominators have been rebuilt from the corrected assignments. The bounded correction CHECK in 01_nutritional_composition gives before/after counts, retained findings, unresolved populations and validation. Comprehensive category cleanup stays deferred. No new juice nutritional profile is proposed; Friday consolidation has not started.

**Potato finding.** A crisp descriptor can legitimately coexist with popped or extruded construction. Explicitly popped products have much lower median fat, but other puffed/stacked constructions need not. These descriptors explain some overlap, not the entire retained lower-fat profile. Among the existing lower-fat potato-crisp qualifiers: FR: 10/100 with explicit popped/puffed/extruded construction and 9/100 with baked wording; UK-IE: 1/90 with explicit popped/puffed/extruded construction and 14/90 with baked wording. Construction wording is incomplete; absence of a cue is not proof of frying, slicing or recipe. Mixed base wording is separately flagged. Keep the accepted descriptive profile and the independent construction descriptor; do not assume extrusion means lower fat.

Food figures are per 100 g and liquid figures use the inherited per-100-ml comparable-basis flag. Preparations, unresolved bases and scope concerns remain in the text-boundary audit but not numerical comparison. Validity masks are reused unchanged; nulls and zeros remain distinct. Different nutrient medians can use different available subsets. These sensitivities change analytical boundaries only; no source reclassification or accepted profile rule is changed.

## Selected text examples

Examples illustrate evidence outcomes, not verified package identities or a representative sample. No images were opened or assessed.

| Boundary | Exact key | Name | Current | Independent interpretation | Reason |
| --- | --- | --- | --- | --- | --- |
| juice family | `0012000172601` · FR · beverages | Vanilla honey flavored coffee smoothie with almondmilk, vanilla honey | plant drink: mixed/unresolved | UNRESOLVED | adjacent commercial identity with juice-family wording |
| juice family | `3560070815852` · FR · beverages | Boisson aux fruits Saveur Orange à l'eau de source | water: unspecified flavour | fruit drink | apparent analytical-label mismatch |
| juice family | `0001000506814` · FR · beverages | Jus d'abricot biologique | nectar | UNRESOLVED | conflicting name and specific tags |
| potato constructions | `00368841` · UK-IE · snacks | Cheese and onion flavoured chickpea chips | conflicting | UNRESOLVED | conflicting name/tag base evidence |
| potato constructions | `0082666806011` · FR · snacks | Himalayan salt popped pea chips, himalayan salt | puffed/extruded | UNRESOLVED | insufficient potato-base evidence |
| potato constructions | `0003800013928` · FR · snacks | Pringles screaming dill pickles | puffed/extruded | potato popped/extruded construction | supported construction with overlapping crisp descriptor |

## Human evidence and source integrity

Julia's 12 submitted observations and the separate interpreted sidecar are unchanged. They remain qualitative diagnostic examples; no expansion, new image assessment or update of locked negatives is made. Previously flagged date/key limitations remain. Neither human file enters organic/NOVA estimates.

Validation passed: master SHA-256, all 96 baseline category/region/nutrient validity counts, one-to-one commercial joins, disjoint organic-state and NOVA denominators, boundary-origin/status reconciliation, exact text-key Parquet round-trip (38,922 keyed evidence rows), unique keys per evidence purpose, all 12 human review IDs and before/after hashes for every protected dependency. The Parquet schema metadata contains the full input-hash manifest and script hash.

## Reproduce and handover

Run `.venv/Scripts/python.exe -B presentations/segmentation/first_run/03_lenses/04_positioning_tradeoffs/processing_boundaries_v1.py` from the repository. It writes only this CHECK, `organic_nova_v1.csv`, `category_boundaries_v1.csv` and `processing_boundary_evidence_v1.parquet`. The supporting CSV contains screen denominators, original-side/status cross-tabs, original-to-independent identities and nutrition consequences. Source wording is in the keyed table; source organic evidence is carried with its original field/state/basis and exact key.

Master SHA-256: `ff6de2e3ef6752abbd5335a352a413940a8e6c12962bb6c85101f52ea86af912`. Human submission SHA-256: `df98236abe148b916fe44175625d6880ffb3b8756fd3d5d01fa3ac233eee97eb`. Interpreted sidecar SHA-256: `debc7a3296a112dceb7dac49e0dee2fd2afd4addd1819ee5b7ab0c034295b9cf`.

**STOP for Julia's review. No Friday consolidation, provider calls, new segmentation, master/reporting changes or source deletions.**

<!-- juice-confidence-sensitivity-v1 -->
## Approval and consolidation handoff · 19 November 2026

**Approved by Julia.** Retain French muesli organic × recorded NOVA 4 only as an association among selected observations with known organic-communication status and recorded NOVA: 6/24 versus 25/48. Documented non-detection is limited to assessed evidence. Do not infer healthfulness, causality, organic compliance, population prevalence or cross-region replication.

The corrected juice layer is accepted after the final 1,090-record confidence sensitivity; its headline interpretation is stable. HIGH/MEDIUM denotes textual evidence strength, not independently verified package identity. [Final sensitivity and acceptance](../01_nutritional_composition/juice_classification_CHECK_v1.md). Sparse, unresolved and deferred populations retain their stated decisions. Consolidation is the next phase and has not started.
<!-- /juice-confidence-sensitivity-v1 -->
