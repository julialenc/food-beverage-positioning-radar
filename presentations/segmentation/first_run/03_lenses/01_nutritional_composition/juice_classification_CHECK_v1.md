# Bounded juice classification correction — CHECK v1

**Completed 19 November 2026. STOP before consolidation.** Corrected Wave 2, retrieved 17 October with 29 September cutoff. This corrects derived analytical commercial labels; master nutrition, governed categories and locked claim evidence are unchanged.

## What changed

The old rule treated the broad parent tag `boissons aux fruits` as a specific fruit-drink identity before checking juice evidence. One shared text-only classifier now supplies beverage labels and boundary interpretation in all three regions. Specific names/tags can resolve juice, nectar, fruit drink or smoothie. Generic parent tags alone do not. Conflicting evidence and incompatible intended-use wording stay `juice family unresolved`; a name is not automatically privileged over a specific contradictory tag. Confidence describes proposed text evidence, not human verification.

| Region | Commercial type | Original n | Corrected n | Change |
| --- | --- | --- | --- | --- |
| FR | juice | 3046 | 8558 | 5512 |
| FR | nectar | 2130 | 1930 | -200 |
| FR | fruit drink | 5757 | 102 | -5655 |
| FR | smoothie | 596 | 544 | -52 |
| FR | juice family unresolved | 57 | 452 | 395 |
| UK-IE | juice | 782 | 798 | 16 |
| UK-IE | nectar | 22 | 14 | -8 |
| UK-IE | fruit drink | 124 | 40 | -84 |
| UK-IE | smoothie | 174 | 171 | -3 |
| UK-IE | juice family unresolved | 13 | 92 | 79 |
| US-CA | juice | 4733 | 4505 | -228 |
| US-CA | nectar | 305 | 252 | -53 |
| US-CA | fruit drink | 709 | 805 | 96 |
| US-CA | smoothie | 725 | 586 | -139 |
| US-CA | juice family unresolved | 33 | 357 | 324 |

Total beverage assignments remain **117,596**; corrected juice assignments **13,861**. Exactly **6,680** assignments changed analytical label. All original labels are retained as `original_analytical_format`, alongside corrected label, rule version `juice_identity_v1_20261119`, confidence, name/tag evidence, reason and change flag in beverage_assignments_v1.parquet. No duplicate old dataset was retained.

| Region | Revised type on changed records | Confidence | n |
| --- | --- | --- | --- |
| FR | fruit drink | MEDIUM | 16 |
| FR | juice | HIGH | 4518 |
| FR | juice | MEDIUM | 1090 |
| FR | juice family unresolved | LOW | 395 |
| UK-IE | fruit drink | MEDIUM | 2 |
| UK-IE | juice | HIGH | 35 |
| UK-IE | juice | MEDIUM | 12 |
| UK-IE | juice family unresolved | LOW | 79 |
| US-CA | fruit drink | HIGH | 1 |
| US-CA | fruit drink | MEDIUM | 180 |
| US-CA | juice | HIGH | 20 |
| US-CA | juice | MEDIUM | 8 |
| US-CA | juice family unresolved | LOW | 324 |

The correction is bounded to existing governed juice-family liquid assignments. Both original juice and neighbouring nectar/fruit-drink/smoothie sides were reconsidered. Outside-family cases remain in the two-sided boundary audit; juice mentioned in soda/tea/water is not automatically a juice product. No comprehensive reclassification was performed.

## Nutritional findings refreshed

| Region | Population | n | Valid sugars | 0.5<sugars<5 n | Valid salt in band | Salt median | Band without vegetable evidence n | Valid salt there | Salt median there |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FR | Original selected juice | 3046 | 2827 | 533 | 501 | 0.3 | 234 | 206 | 0.01 |
| FR | Corrected juice | 8558 | 7550 | 840 | 784 | 0.02 | 530 | 478 | 0.008 |
| UK-IE | Original selected juice | 782 | 729 | 110 | 99 | 0.01 | 90 | 79 | 0.01 |
| UK-IE | Corrected juice | 798 | 746 | 95 | 84 | 0.01 | 75 | 64 | 0.01 |
| US-CA | Original selected juice | 4733 | 319 | 45 | 42 | 0.029 | 31 | 28 | 0.01 |
| US-CA | Corrected juice | 4505 | 318 | 35 | 32 | 0.051 | 21 | 18 | 0.01 |

All food identity decisions precede nutrition. Liquid figures above are per 100 ml on the inherited basis. Missing remains distinct from measured zero. The regenerated juice report contains the updated apple/orange/tomato composition summaries, nutrient distributions, ambiguity effects, very-low-sugar energy checks and the same bounded within-type cutoff sensitivities. Retain commercial composition refinements and no additional nutritional profile; thresholds and questionable zero-sugar/high-energy records do not establish a new formulation strategy.

**Material interpretation change:** the French low-sugar group's median salt falls from 0.30 to 0.02 g/100 ml after correcting the population. Tomato/vegetable composition remains informative, but the expanded low-sugar juice population is not generally a higher-salt group. Apple/orange/tomato remain useful commercial distinctions; a separate low-sugar nutritional segment is still unsupported.

The earlier French-versus-UK fruit-drink nutritional contrast is withdrawn because the old French population mixed in many juices. Original low-sugar/salt counts remain reproducible as original-population observations, but the refreshed denominators above and the regenerated juice report govern current interpretation. No inference about recipe substitution or added salt is made.

## Affected dependencies rebuilt

Rebuilt affected outputs: beverage_assignments_v1.parquet and beverage evidence tables; juice_assignments_v1.parquet and juice_formulations_v1.md; communication_coverage_v1.csv; communication_overlays_v1.csv (updated coverage hash only); existing FORMULATION_DECISIONS_v1.csv source references; organic_nova_v1.csv; category_boundaries_v1.csv and processing_boundary_evidence_v1.parquet; processing CHECK. Dynamic key-subset checks replace the obsolete 8,561-juice-row assertion. Existing coverage/synthesis notes and learning plan point to this correction. This refreshes existing outputs and references; it does not create Friday's consolidated release.

Communication coverage now has 13,602 proposition-specific cells; known/non-detection/unknown states still reconcile. The processing CHECK reports supported organic/NOVA cells on corrected commercial populations. The full master and the original broad-family H1–H12 results were not rerun or changed.

## Validation

PASS: shared classifier regression fixtures (parent tags, nested types, contradiction, missing identity, preparation wording and negative juice mentions); one verified shared master read and all 96 region/category/nutrient-valid counts; exact text-key preservation and uniqueness; corrected juice keys equal the corrected beverage juice subset; no changes outside correction scope and unchanged source metadata on every beverage row; unchanged retained profiles in all 15 region/profile cells; identical unaffected communication coverage and all Wednesday substantive overlay values/provenance; identical potato nutrition consequences; 33 existing register decisions retained; final processing input/script hashes agree with the refreshed dependencies; unchanged in-memory source measurements and original-run/protected evidence hashes (25 protected artifacts). No OCR, image assessment, provider calls, enrichment, imputation or clustering.

Master SHA-256: `ff6de2e3ef6752abbd5335a352a413940a8e6c12962bb6c85101f52ea86af912`. All 12 human submissions and their interpreted sidecar remain unchanged qualitative examples. The processing evidence Parquet contains an updated input-hash manifest. Existing source lineage and original GTIN strings, including leading zeros, remain intact.

## Reproduce and stop

Run `.venv/Scripts/python.exe -B presentations/segmentation/first_run/03_lenses/01_nutritional_composition/juice_classification_correction_v1.py` from the repository. It reuses one validated master read across existing builders and overwrites only affected analytical outputs/notes. Rule fixtures can also run directly through juice_classification_v1.py. **Ready for review; no consolidation, release packaging or publication has started.**

<!-- juice-confidence-sensitivity-v1 -->
## Final MEDIUM-confidence sensitivity and acceptance · 19 November 2026

Julia approved the Thursday processing/boundary findings and the corrected juice interpretation subject to this final bounded sensitivity. The condition has been met. Corrected juice classifications are the authoritative analytical interpretation; all records remain in their existing keyed layers. **Ready for the consolidation phase; consolidation has not started.**

Exact exclusion predicate: `region == FR`, corrected `analytical_format == juice`, `original_analytical_format != juice`, and `juice_classification_confidence == MEDIUM`. This identifies exactly 1,090 of 8,558 French assignments; 7,468 remain in the comparison. The retained arm is not a HIGH-only or independently verified sample. Original-juice MEDIUM records remain. No classifications or evidence states are changed.

| Sensitivity arm | Juice n | Valid sugars n | 0.5<sugars<5 n | Valid salt in band | Median salt | Salt Q1–Q3 | Median salt without vegetable-type labels |
| --- | --- | --- | --- | --- | --- | --- | --- |
| corrected full | 8558 | 7550 | 840 | 784 | 0.02 | 0–0.314 | 0.008 |
| exclude newly assigned MEDIUM | 7468 | 6548 | 767 | 716 | 0.03 | 0–0.38 | 0.01 |
| removed MEDIUM only | 1090 | 1002 | 73 | 68 | 0 | 0–0.01 | 0 |

| Comparable named type | Full: sugars / energy / salt medians (each valid n) | Exclude newly MEDIUM: same measurements |
| --- | --- | --- |
| fruit: apple | 10.28 (n=1605) / 45 (n=1631) / 0.005 (n=1515) | 10.24 (n=1470) / 45 (n=1494) / 0.008 (n=1386) |
| fruit: orange | 9 (n=1428) / 43 (n=1438) / 0 (n=1334) | 9 (n=1235) / 43 (n=1243) / 0 (n=1142) |
| vegetable: tomato | 3 (n=281) / 19 (n=284) / 0.4 (n=277) | 3 (n=281) / 19 (n=284) / 0.4 (n=277) |

**Headline interpretation remains stable.** The low-sugar group's median salt changes from 0.02 to 0.03 g/100 ml, compared with 0.30 in the superseded selected population. The distribution still has a higher-salt upper tail; tomato/vegetable distinctions remain informative. Apple sugars change from 10.28 to 10.24 g/100 ml, orange stays at 9, and the named-type energy medians remain 45/43/19 kcal. No tomato records are excluded, so unchanged tomato measurements are expected, not independent validation of identity. This check supports retaining the commercial refinements and existing decision against an additional juice nutritional profile. It does not prove the absence of clusters or verify product identity.

Measurements reuse saved valid values on the inherited per-100-ml basis. Missing and numeric zero remain separate. The no-vegetable-type-label view exactly reuses the existing `not juice_subformat.startswith('vegetable')` definition; it is not proof of absence of vegetable ingredients and does not remove mixed fruit/vegetable labels. No new identity inference, outlier deletion or cleansing is performed. French conclusions remain conditional on the observed OFF population.

[Reproducible script](juice_confidence_sensitivity_v1.py) · [Matching summary table](juice_confidence_sensitivity_v1.csv). The 54 rows cover three arms, six populations and sugars/energy/salt; input and script hashes accompany each row. The exact excluded keys are reconstructible from the unchanged beverage/juice layers and the predicate above; no duplicate product export is required.

Validation: exact 1,090/7,468 partition; composite key and leading-zero-sensitive string preservation; corrected-juice subset equality; complete missing/available reconciliation; summary CSV round-trip; processing dependency/script hash verification; before/after hashes of 10 protected source/evidence artifacts. Master, locked claims, classifications, register and all 12 human observations are unchanged.

**Decision: stop this sensitivity. No further classification, OCR/LLM, model or manual-review iteration is required for this question.**
<!-- /juice-confidence-sensitivity-v1 -->
