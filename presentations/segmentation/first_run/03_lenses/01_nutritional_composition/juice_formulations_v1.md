# Juice formulations · Wave 2

**Formulation investigation closed by Julia on 16 November. Bounded classification correction: 19 November 2026.** The shared name/tag rule now gives specific commercial evidence precedence over broad parent tags. Conflicting names/specific tags, generic-only identity and incompatible intended-use wording remain unresolved in the beverage layer. [Correction CHECK](juice_classification_CHECK_v1.md).

**Conclusion retained: commercial refinements, no additional nutritional profile proposed.** Apple, orange, tomato, fruit/vegetable mixtures and named blends are composition-based commercial types. Concentrate wording remains an independent processing descriptor. No clustering, new recipe inference or new claims assessment was performed.

The corrected population is the exact juice subset of beverage_assignments_v1.parquet: FR: 8,558, UK-IE: 798, US-CA: 4,505; total 13,861 assignments. Original and corrected analytical labels, confidence, reasons and text keys are retained. The earlier 8,561-assignment file represented the old selected population, not complete juice coverage.

**French low-sugar/salt explanation, refreshed.** Among 7,550 valid sugar observations, 840 have 0.5<sugars<5 g/100 ml. Salt is observed on 784; median 0.02 g/100 ml. Excluding vegetable-type evidence leaves 530, with 478 valid salt values and median 0.01 g/100 ml. These updated denominators replace the earlier selected-population summary. Nutrition describes consequences of commercial composition; it does not assign identity or prove salt addition.

| Named commercial type | France: sugars and salt per 100 ml | UK/IE: sugars and salt per 100 ml |
| --- | --- | --- |
| fruit: apple | 10.28 g (n=1605); salt 0.01 g (n=1515) | 10.30 g (n=205); salt 0.00 g (n=169) |
| fruit: orange | 9.00 g (n=1428); salt 0.00 g (n=1334) | 8.92 g (n=214); salt 0.01 g (n=194) |
| vegetable: tomato | 3.00 g (n=281); salt 0.40 g (n=277) | 3.10 g (n=20); salt 0.54 g (n=20) |

The same bounded within-type summaries and French P20/P25/P30 sensitivity are refreshed below. Apple/orange variation and questionable zero-sugar/nonzero-energy records do not establish a recognizable new low-sugar formulation profile. Recorded zero stays distinct from missing. US/Canada remains selected exploratory evidence; liquid basis and validity conventions are inherited, not independently pack-verified.

**Unresolved boundaries stay visible.** A juice name alongside specific nectar tags is not silently treated as confirmed juice. Broader beverage records can refer to juice as an ingredient or an overlapping proposition. This correction does not comprehensively recategorize beverages outside the existing governed juice-family population. Category-boundary questions and intended-use flags remain independent of nutrition.

The keyed file and evidence tables below are rebuilt reproducibly from the unchanged corrected Wave 2 master. Source observations and locked OCR/LLM evidence are unchanged. No new providers, image assessment, enrichment, clustering or consolidation were run.

<!-- evidence -->

<details><summary>Population and effect of ambiguity exclusions</summary>

| Region | Population | N | Valid sugars | Joint sugar/energy | ≤0.5 N | 0.5–<5 N |
| --- | --- | --- | --- | --- | --- | --- |
| FR | current juice | 8558 | 7550 | 7536 | 139 | 840 |
| FR | strict commercial evidence | 6698 | 5825 | 5816 | 77 | 664 |
| UK-IE | current juice | 798 | 746 | 743 | 24 | 95 |
| UK-IE | strict commercial evidence | 654 | 615 | 613 | 13 | 74 |
| US-CA | current juice | 4505 | 318 | 318 | 15 | 35 |
| US-CA | strict commercial evidence | 3108 | 245 | 245 | 7 | 18 |

</details>

<details><summary>Independent commercial classifications</summary>

| Subformat | FR | UK-IE | US-CA |
| --- | --- | --- | --- |
| ambiguous composition | 54 | 2 | 7 |
| boundary concern | 16 | 17 | 7 |
| composition unresolved | 1573 | 104 | 1154 |
| fruit blend | 746 | 62 | 347 |
| fruit: apple | 1928 | 220 | 700 |
| fruit: apricot | 6 | 0 | 0 |
| fruit: berry | 77 | 8 | 52 |
| fruit: cherry | 11 | 4 | 51 |
| fruit: cranberry | 72 | 11 | 78 |
| fruit: grape | 402 | 19 | 214 |
| fruit: grapefruit | 200 | 9 | 99 |
| fruit: lemon | 328 | 21 | 107 |
| fruit: lime | 17 | 5 | 84 |
| fruit: mango | 59 | 3 | 29 |
| fruit: orange | 1652 | 221 | 906 |
| fruit: peach | 26 | 2 | 8 |
| fruit: pear | 173 | 4 | 14 |
| fruit: pineapple | 307 | 22 | 79 |
| fruit: pomegranate | 136 | 4 | 51 |
| fruit: prune | 41 | 5 | 53 |
| mixed fruit/vegetable | 98 | 11 | 74 |
| other botanical juice | 117 | 13 | 30 |
| vegetable blend | 7 | 1 | 13 |
| vegetable unspecified | 23 | 0 | 147 |
| vegetable: beetroot | 37 | 6 | 23 |
| vegetable: carrot | 139 | 4 | 24 |
| vegetable: celery | 1 | 0 | 6 |
| vegetable: cucumber | 0 | 0 | 3 |
| vegetable: kale | 2 | 0 | 3 |
| vegetable: spinach | 0 | 0 | 1 |
| vegetable: tomato | 310 | 20 | 141 |

</details>

<details><summary>Explaining the 0.5–5 group</summary>

| Region | Subformat | Sugar group N | Valid salt | Median salt | Median energy |
| --- | --- | --- | --- | --- | --- |
| FR | ambiguous composition | 31 | 30 | 0.00 | 29.00 |
| FR | boundary concern | 5 | 5 | 0.03 | 44.50 |
| FR | composition unresolved | 103 | 95 | 0.01 | 20.00 |
| FR | fruit blend | 15 | 15 | 0.01 | 20.00 |
| FR | fruit: apple | 11 | 10 | 0.01 | 34.00 |
| FR | fruit: berry | 8 | 7 | 0.00 | 19.50 |
| FR | fruit: cranberry | 23 | 20 | 0.01 | 21.00 |
| FR | fruit: grape | 1 | 1 | 0.01 | 10.00 |
| FR | fruit: grapefruit | 5 | 5 | 0.01 | 21.00 |
| FR | fruit: lemon | 248 | 219 | 0.01 | 27.00 |
| FR | fruit: lime | 13 | 12 | 0.00 | 29.00 |
| FR | fruit: mango | 4 | 4 | 0.04 | 18.50 |
| FR | fruit: orange | 32 | 27 | 0.01 | 21.00 |
| FR | fruit: peach | 2 | 2 | 0.00 | 19.50 |
| FR | fruit: pear | 2 | 2 | 0.01 | 25.00 |
| FR | fruit: pineapple | 7 | 7 | 0.01 | 21.00 |
| FR | mixed fruit/vegetable | 5 | 5 | 0.02 | 22.00 |
| FR | other botanical juice | 15 | 12 | 0.02 | 20.00 |
| FR | vegetable blend | 3 | 3 | 0.73 | 20.84 |
| FR | vegetable unspecified | 14 | 14 | 0.41 | 18.75 |
| FR | vegetable: beetroot | 2 | 2 | 0.53 | 31.00 |
| FR | vegetable: carrot | 22 | 22 | 0.10 | 31.00 |
| FR | vegetable: celery | 1 | 1 | 0.60 | 18.00 |
| FR | vegetable: tomato | 268 | 264 | 0.40 | 19.00 |
| UK-IE | boundary concern | 9 | 6 | 0.00 | 20.00 |
| UK-IE | composition unresolved | 5 | 5 | 0.01 | 19.00 |
| UK-IE | fruit blend | 3 | 3 | 0.01 | 18.75 |
| UK-IE | fruit: apple | 6 | 5 | 0.00 | 18.90 |
| UK-IE | fruit: berry | 7 | 6 | 0.01 | 19.00 |
| UK-IE | fruit: cherry | 3 | 3 | 0.01 | 22.00 |
| UK-IE | fruit: cranberry | 9 | 7 | 0.01 | 20.00 |
| UK-IE | fruit: grape | 1 | 1 | 0.40 | 286.00 |
| UK-IE | fruit: grapefruit | 1 | 1 | 0.02 | 16.00 |
| UK-IE | fruit: lemon | 19 | 17 | 0.01 | 25.00 |
| UK-IE | fruit: lime | 4 | 3 | 0.01 | 25.00 |
| UK-IE | fruit: mango | 1 | 1 | 0.01 | 20.00 |
| UK-IE | fruit: orange | 5 | 4 | 0.00 | 19.00 |
| UK-IE | fruit: pineapple | 1 | 1 | 0.01 | 18.00 |
| UK-IE | fruit: pomegranate | 1 | 1 | 0.00 | 17.00 |
| UK-IE | vegetable: beetroot | 1 | 1 | 0.70 | 18.00 |
| UK-IE | vegetable: tomato | 19 | 19 | 0.58 | 19.00 |
| US-CA | composition unresolved | 8 | 7 | 0.01 | 12.94 |
| US-CA | fruit blend | 3 | 3 | 0.04 | 19.00 |
| US-CA | fruit: apple | 1 | 1 | 0.00 | 19.73 |
| US-CA | fruit: cranberry | 3 | 3 | 0.01 | 29.17 |
| US-CA | fruit: grape | 1 | 1 | 0.40 | 286.00 |
| US-CA | fruit: lime | 1 | 1 | 0.01 | 17.00 |
| US-CA | fruit: orange | 4 | 2 | 0.01 | 21.00 |
| US-CA | vegetable unspecified | 9 | 9 | 0.67 | 18.75 |
| US-CA | vegetable: celery | 1 | 1 | 0.19 | 14.12 |
| US-CA | vegetable: tomato | 4 | 4 | 0.44 | 19.50 |

</details>

<details><summary>Salt sensitivity to commercial composition</summary>

| Region | Population at 0.5–<5 | N | Valid salt | Median salt |
| --- | --- | --- | --- | --- |
| FR | all | 840 | 784 | 0.02 |
| FR | without vegetable evidence | 530 | 478 | 0.01 |
| FR | strict fruit | 363 | 324 | 0.01 |
| UK-IE | all | 95 | 84 | 0.01 |
| UK-IE | without vegetable evidence | 75 | 64 | 0.01 |
| UK-IE | strict fruit | 54 | 47 | 0.01 |
| US-CA | all | 35 | 32 | 0.05 |
| US-CA | without vegetable evidence | 21 | 18 | 0.01 |
| US-CA | strict fruit | 13 | 11 | 0.01 |

</details>

<details><summary>Concentrate descriptor, independent of named composition</summary>

| Region | Descriptor | Assignments |
| --- | --- | --- |
| FR |  | 133 |
| FR | explicit from concentrate | 43 |
| FR | explicit not from concentrate | 2 |
| FR | unspecified | 8380 |
| UK-IE |  | 30 |
| UK-IE | explicit from concentrate | 85 |
| UK-IE | explicit not from concentrate | 4 |
| UK-IE | unspecified | 679 |
| US-CA |  | 37 |
| US-CA | explicit from concentrate | 662 |
| US-CA | explicit not from concentrate | 11 |
| US-CA | unspecified | 3795 |

</details>

<details><summary>Low-sugar cohort and very-low-sugar energy audit</summary>

| Region | Cohort | N | Available relevant metric | Salt median or energy median | Energy median or energy>20 N |
| --- | --- | --- | --- | --- | --- |
| FR | 0.5<sugars<5 | 840 | 784 | 0.02 | 22.00 |
| FR | ≤0.5: ambiguous composition | 4 | 4 | 28.00 | 3 |
| FR | ≤0.5: boundary concern | 3 | 3 | 17.00 | 1 |
| FR | ≤0.5: composition unresolved | 29 | 27 | 23.00 | 15 |
| FR | ≤0.5: fruit blend | 8 | 8 | 45.00 | 7 |
| FR | ≤0.5: fruit: apple | 6 | 6 | 46.50 | 6 |
| FR | ≤0.5: fruit: berry | 1 | 1 | 72.00 | 1 |
| FR | ≤0.5: fruit: cranberry | 3 | 3 | 29.00 | 3 |
| FR | ≤0.5: fruit: grape | 5 | 5 | 84.00 | 5 |
| FR | ≤0.5: fruit: grapefruit | 2 | 2 | 43.00 | 2 |
| FR | ≤0.5: fruit: lemon | 33 | 33 | 20.00 | 16 |
| FR | ≤0.5: fruit: lime | 2 | 2 | 21.00 | 1 |
| FR | ≤0.5: fruit: mango | 2 | 2 | 54.00 | 2 |
| FR | ≤0.5: fruit: orange | 4 | 4 | 47.50 | 4 |
| FR | ≤0.5: fruit: pear | 2 | 2 | 34.00 | 2 |
| FR | ≤0.5: fruit: pineapple | 4 | 4 | 46.28 | 4 |
| FR | ≤0.5: other botanical juice | 25 | 24 | 5.50 | 7 |
| FR | ≤0.5: vegetable: tomato | 6 | 6 | 18.50 | 2 |
| UK-IE | 0.5<sugars<5 | 95 | 84 | 0.01 | 20.00 |
| UK-IE | ≤0.5: ambiguous composition | 1 | 1 | 20.00 | 0 |
| UK-IE | ≤0.5: boundary concern | 8 | 8 | 2.00 | 1 |
| UK-IE | ≤0.5: composition unresolved | 2 | 2 | 4.78 | 0 |
| UK-IE | ≤0.5: fruit blend | 4 | 4 | 2.00 | 0 |
| UK-IE | ≤0.5: fruit: apple | 3 | 3 | 46.00 | 2 |
| UK-IE | ≤0.5: fruit: lemon | 1 | 1 | 4.00 | 0 |
| UK-IE | ≤0.5: fruit: orange | 3 | 3 | 2.00 | 0 |
| UK-IE | ≤0.5: fruit: peach | 1 | 1 | 0.80 | 0 |
| UK-IE | ≤0.5: fruit: pineapple | 1 | 1 | 4.00 | 0 |
| US-CA | 0.5<sugars<5 | 35 | 32 | 0.05 | 19.73 |
| US-CA | ≤0.5: ambiguous composition | 1 | 1 | 0.00 | 0 |
| US-CA | ≤0.5: composition unresolved | 6 | 6 | 2.58 | 1 |
| US-CA | ≤0.5: fruit: berry | 1 | 1 | 1.88 | 0 |
| US-CA | ≤0.5: fruit: cranberry | 2 | 2 | 2.10 | 0 |
| US-CA | ≤0.5: fruit: lemon | 3 | 3 | 0.00 | 0 |
| US-CA | ≤0.5: fruit: lime | 1 | 1 | 0.00 | 0 |
| US-CA | ≤0.5: fruit: pomegranate | 1 | 1 | 130.00 | 1 |

</details>

<details><summary>Within-subformat nutrient variation</summary>

| Region | Subformat | Metric | N | Valid | P10 | Q1 | Median | Q3 | P90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FR | fruit blend | sugars | 746 | 673 | 8.32 | 9.30 | 10.00 | 11.00 | 12.00 |
| FR | fruit blend | energy | 746 | 678 | 39.00 | 43.00 | 46.00 | 50.00 | 54.86 |
| FR | fruit blend | salt | 746 | 640 | 0.00 | 0.00 | 0.00 | 0.01 | 0.03 |
| FR | fruit blend | protein | 746 | 676 | 0.00 | 0.10 | 0.30 | 0.50 | 0.60 |
| FR | fruit blend | fat | 746 | 673 | 0.00 | 0.00 | 0.10 | 0.42 | 0.50 |
| FR | fruit blend | fibre | 746 | 456 | 0.00 | 0.15 | 0.50 | 0.81 | 1.31 |
| FR | fruit: apple | sugars | 1928 | 1605 | 9.40 | 9.80 | 10.28 | 11.00 | 11.50 |
| FR | fruit: apple | energy | 1928 | 1631 | 41.10 | 43.00 | 45.00 | 48.00 | 51.00 |
| FR | fruit: apple | salt | 1928 | 1515 | 0.00 | 0.00 | 0.01 | 0.01 | 0.03 |
| FR | fruit: apple | protein | 1928 | 1625 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| FR | fruit: apple | fat | 1928 | 1620 | 0.00 | 0.00 | 0.10 | 0.30 | 0.50 |
| FR | fruit: apple | fibre | 1928 | 950 | 0.00 | 0.00 | 0.23 | 0.50 | 0.91 |
| FR | fruit: apricot | sugars | 6 | 6 | 8.75 | 12.10 | 13.50 | 14.45 | 14.75 |
| FR | fruit: apricot | energy | 6 | 6 | 36.50 | 52.50 | 60.50 | 61.75 | 63.50 |
| FR | fruit: apricot | salt | 6 | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| FR | fruit: apricot | protein | 6 | 6 | 0.00 | 0.03 | 0.10 | 0.18 | 0.30 |
| FR | fruit: apricot | fat | 6 | 6 | 0.00 | 0.00 | 0.00 | 0.08 | 0.15 |
| FR | fruit: apricot | fibre | 6 | 3 | 0.12 | 0.30 | 0.60 | 0.65 | 0.68 |
| FR | fruit: cherry | sugars | 11 | 11 | 9.80 | 10.00 | 10.30 | 13.00 | 13.95 |
| FR | fruit: cherry | energy | 11 | 11 | 42.00 | 42.00 | 54.00 | 62.00 | 80.31 |
| FR | fruit: cherry | salt | 11 | 11 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 |
| FR | fruit: cherry | protein | 11 | 11 | 0.00 | 0.10 | 0.40 | 0.67 | 1.20 |
| FR | fruit: cherry | fat | 11 | 11 | 0.00 | 0.00 | 0.00 | 0.20 | 0.30 |
| FR | fruit: cherry | fibre | 11 | 6 | 0.00 | 0.00 | 0.00 | 0.75 | 1.30 |
| FR | fruit: cranberry | sugars | 72 | 69 | 2.46 | 4.00 | 7.50 | 11.70 | 12.20 |
| FR | fruit: cranberry | energy | 72 | 69 | 16.80 | 28.00 | 39.00 | 48.00 | 55.40 |
| FR | fruit: cranberry | salt | 72 | 65 | 0.00 | 0.00 | 0.01 | 0.01 | 0.04 |
| FR | fruit: cranberry | protein | 72 | 69 | 0.00 | 0.00 | 0.01 | 0.50 | 0.50 |
| FR | fruit: cranberry | fat | 72 | 69 | 0.00 | 0.00 | 0.00 | 0.50 | 0.50 |
| FR | fruit: cranberry | fibre | 72 | 31 | 0.00 | 0.00 | 0.50 | 1.94 | 5.13 |
| FR | fruit: grape | sugars | 402 | 331 | 14.80 | 15.00 | 16.00 | 16.00 | 17.10 |
| FR | fruit: grape | energy | 402 | 334 | 60.00 | 64.00 | 66.00 | 69.00 | 76.00 |
| FR | fruit: grape | salt | 402 | 314 | 0.00 | 0.00 | 0.00 | 0.01 | 0.02 |
| FR | fruit: grape | protein | 402 | 335 | 0.00 | 0.00 | 0.20 | 0.50 | 0.50 |
| FR | fruit: grape | fat | 402 | 332 | 0.00 | 0.00 | 0.00 | 0.50 | 0.50 |
| FR | fruit: grape | fibre | 402 | 196 | 0.00 | 0.00 | 0.50 | 0.90 | 0.90 |
| FR | fruit: grapefruit | sugars | 200 | 181 | 6.70 | 7.60 | 8.00 | 8.70 | 9.40 |
| FR | fruit: grapefruit | energy | 200 | 181 | 33.00 | 36.00 | 39.00 | 41.50 | 44.00 |
| FR | fruit: grapefruit | salt | 200 | 173 | 0.00 | 0.00 | 0.00 | 0.01 | 0.03 |
| FR | fruit: grapefruit | protein | 200 | 181 | 0.00 | 0.40 | 0.50 | 0.60 | 0.70 |
| FR | fruit: grapefruit | fat | 200 | 181 | 0.00 | 0.00 | 0.10 | 0.40 | 0.50 |
| FR | fruit: grapefruit | fibre | 200 | 118 | 0.00 | 0.10 | 0.50 | 0.86 | 1.60 |
| FR | fruit: lemon | sugars | 328 | 296 | 0.41 | 1.70 | 1.80 | 2.00 | 2.40 |
| FR | fruit: lemon | energy | 328 | 298 | 16.40 | 25.00 | 27.00 | 28.00 | 31.00 |
| FR | fruit: lemon | salt | 328 | 262 | 0.00 | 0.00 | 0.00 | 0.01 | 0.02 |
| FR | fruit: lemon | protein | 328 | 300 | 0.00 | 0.10 | 0.40 | 0.40 | 0.50 |
| FR | fruit: lemon | fat | 328 | 300 | 0.00 | 0.00 | 0.03 | 0.10 | 0.50 |
| FR | fruit: lemon | fibre | 328 | 153 | 0.00 | 0.00 | 0.40 | 0.40 | 0.50 |
| FR | fruit: lime | sugars | 17 | 16 | 0.55 | 1.40 | 1.60 | 1.62 | 1.85 |
| FR | fruit: lime | energy | 17 | 16 | 24.50 | 28.00 | 29.00 | 32.00 | 40.00 |
| FR | fruit: lime | salt | 17 | 15 | 0.00 | 0.00 | 0.00 | 0.01 | 0.01 |
| FR | fruit: lime | protein | 17 | 16 | 0.40 | 0.47 | 0.50 | 0.70 | 0.70 |
| FR | fruit: lime | fat | 17 | 16 | 0.07 | 0.10 | 0.10 | 0.20 | 0.50 |
| FR | fruit: lime | fibre | 17 | 6 | 0.00 | 1.07 | 4.30 | 4.30 | 4.30 |
| FR | fruit: mango | sugars | 59 | 58 | 4.94 | 9.12 | 11.00 | 12.50 | 13.77 |
| FR | fruit: mango | energy | 59 | 58 | 38.40 | 45.00 | 50.00 | 57.00 | 67.30 |
| FR | fruit: mango | salt | 59 | 55 | 0.00 | 0.00 | 0.01 | 0.04 | 0.15 |
| FR | fruit: mango | protein | 59 | 58 | 0.00 | 0.00 | 0.16 | 0.47 | 0.50 |
| FR | fruit: mango | fat | 59 | 58 | 0.00 | 0.00 | 0.00 | 0.10 | 0.33 |
| FR | fruit: mango | fibre | 59 | 36 | 0.00 | 0.16 | 0.50 | 1.00 | 1.20 |
| FR | fruit: orange | sugars | 1652 | 1428 | 8.00 | 8.60 | 9.00 | 9.60 | 10.10 |
| FR | fruit: orange | energy | 1652 | 1438 | 38.00 | 40.00 | 43.00 | 46.00 | 48.00 |
| FR | fruit: orange | salt | 1652 | 1334 | 0.00 | 0.00 | 0.00 | 0.01 | 0.03 |
| FR | fruit: orange | protein | 1652 | 1431 | 0.20 | 0.50 | 0.70 | 0.70 | 0.80 |
| FR | fruit: orange | fat | 1652 | 1429 | 0.00 | 0.00 | 0.04 | 0.20 | 0.50 |
| FR | fruit: orange | fibre | 1652 | 970 | 0.00 | 0.20 | 0.30 | 0.50 | 0.80 |
| FR | fruit: peach | sugars | 26 | 24 | 5.15 | 8.47 | 10.25 | 12.12 | 13.21 |
| FR | fruit: peach | energy | 26 | 25 | 26.40 | 38.00 | 49.00 | 53.00 | 56.60 |
| FR | fruit: peach | salt | 26 | 24 | 0.00 | 0.00 | 0.00 | 0.01 | 0.02 |
| FR | fruit: peach | protein | 26 | 25 | 0.00 | 0.10 | 0.34 | 0.50 | 0.72 |
| FR | fruit: peach | fat | 26 | 24 | 0.00 | 0.00 | 0.06 | 0.50 | 0.50 |
| FR | fruit: peach | fibre | 26 | 12 | 0.00 | 0.00 | 0.00 | 0.58 | 0.96 |
| FR | fruit: pear | sugars | 173 | 128 | 8.38 | 9.10 | 10.00 | 11.00 | 12.60 |
| FR | fruit: pear | energy | 173 | 130 | 40.95 | 46.05 | 51.00 | 57.00 | 60.00 |
| FR | fruit: pear | salt | 173 | 118 | 0.00 | 0.00 | 0.01 | 0.01 | 0.02 |
| FR | fruit: pear | protein | 173 | 129 | 0.00 | 0.20 | 0.40 | 0.50 | 0.50 |
| FR | fruit: pear | fat | 173 | 128 | 0.00 | 0.10 | 0.20 | 0.50 | 0.50 |
| FR | fruit: pear | fibre | 173 | 35 | 0.00 | 0.00 | 0.50 | 1.05 | 2.72 |
| FR | fruit: pineapple | sugars | 307 | 287 | 9.20 | 10.40 | 11.00 | 12.00 | 12.34 |
| FR | fruit: pineapple | energy | 307 | 287 | 41.00 | 46.00 | 49.00 | 52.00 | 55.00 |
| FR | fruit: pineapple | salt | 307 | 269 | 0.00 | 0.00 | 0.00 | 0.01 | 0.03 |
| FR | fruit: pineapple | protein | 307 | 287 | 0.00 | 0.10 | 0.40 | 0.50 | 0.50 |
| FR | fruit: pineapple | fat | 307 | 287 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| FR | fruit: pineapple | fibre | 307 | 161 | 0.00 | 0.00 | 0.50 | 0.60 | 1.40 |
| FR | fruit: pomegranate | sugars | 136 | 128 | 9.70 | 12.00 | 12.90 | 13.20 | 15.00 |
| FR | fruit: pomegranate | energy | 136 | 129 | 45.60 | 50.00 | 56.00 | 62.00 | 69.40 |
| FR | fruit: pomegranate | salt | 136 | 117 | 0.00 | 0.00 | 0.01 | 0.02 | 0.03 |
| FR | fruit: pomegranate | protein | 136 | 129 | 0.00 | 0.10 | 0.30 | 0.50 | 0.95 |
| FR | fruit: pomegranate | fat | 136 | 127 | 0.00 | 0.00 | 0.00 | 0.43 | 0.50 |
| FR | fruit: pomegranate | fibre | 136 | 48 | 0.00 | 0.00 | 0.45 | 0.50 | 1.10 |
| FR | fruit: prune | sugars | 41 | 35 | 11.40 | 13.00 | 13.00 | 14.00 | 14.35 |
| FR | fruit: prune | energy | 41 | 35 | 57.56 | 70.00 | 75.00 | 78.00 | 83.00 |
| FR | fruit: prune | salt | 41 | 31 | 0.00 | 0.00 | 0.00 | 0.01 | 0.03 |
| FR | fruit: prune | protein | 41 | 35 | 0.04 | 0.25 | 0.50 | 0.50 | 0.60 |
| FR | fruit: prune | fat | 41 | 35 | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 |
| FR | fruit: prune | fibre | 41 | 23 | 0.64 | 1.00 | 1.30 | 1.80 | 4.46 |
| FR | mixed fruit/vegetable | sugars | 98 | 92 | 6.02 | 7.47 | 8.50 | 9.30 | 10.36 |
| FR | mixed fruit/vegetable | energy | 98 | 91 | 32.00 | 36.00 | 41.00 | 44.00 | 49.00 |
| FR | mixed fruit/vegetable | salt | 98 | 89 | 0.00 | 0.00 | 0.02 | 0.05 | 0.10 |
| FR | mixed fruit/vegetable | protein | 98 | 92 | 0.00 | 0.20 | 0.50 | 0.60 | 0.70 |
| FR | mixed fruit/vegetable | fat | 98 | 91 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| FR | mixed fruit/vegetable | fibre | 98 | 69 | 0.00 | 0.20 | 0.50 | 1.00 | 1.53 |
| FR | vegetable blend | sugars | 7 | 7 | 2.59 | 3.09 | 5.70 | 7.60 | 9.66 |
| FR | vegetable blend | energy | 7 | 7 | 19.67 | 22.82 | 29.00 | 35.50 | 43.20 |
| FR | vegetable blend | salt | 7 | 7 | 0.01 | 0.06 | 0.40 | 0.61 | 0.96 |
| FR | vegetable blend | protein | 7 | 7 | 0.18 | 0.40 | 0.50 | 0.80 | 0.86 |
| FR | vegetable blend | fat | 7 | 7 | 0.00 | 0.05 | 0.10 | 0.11 | 0.16 |
| FR | vegetable blend | fibre | 7 | 5 | 0.08 | 0.20 | 0.50 | 0.96 | 1.01 |
| FR | vegetable: beetroot | sugars | 37 | 37 | 6.50 | 7.00 | 7.80 | 9.10 | 11.00 |
| FR | vegetable: beetroot | energy | 37 | 37 | 31.05 | 36.00 | 41.00 | 45.00 | 52.00 |
| FR | vegetable: beetroot | salt | 37 | 36 | 0.03 | 0.07 | 0.10 | 0.19 | 0.54 |
| FR | vegetable: beetroot | protein | 37 | 37 | 0.24 | 0.70 | 1.00 | 1.10 | 1.96 |
| FR | vegetable: beetroot | fat | 37 | 37 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| FR | vegetable: beetroot | fibre | 37 | 22 | 0.00 | 0.20 | 0.86 | 2.48 | 2.52 |
| FR | vegetable: carrot | sugars | 139 | 129 | 4.70 | 5.30 | 6.00 | 7.10 | 7.84 |
| FR | vegetable: carrot | energy | 139 | 129 | 23.00 | 28.00 | 31.00 | 34.00 | 40.00 |
| FR | vegetable: carrot | salt | 139 | 126 | 0.00 | 0.08 | 0.10 | 0.13 | 0.18 |
| FR | vegetable: carrot | protein | 139 | 129 | 0.00 | 0.50 | 0.50 | 0.60 | 0.80 |
| FR | vegetable: carrot | fat | 139 | 129 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| FR | vegetable: carrot | fibre | 139 | 83 | 0.00 | 0.00 | 0.50 | 2.12 | 2.67 |
| FR | vegetable: celery | sugars | 1 | 1 | 1.60 | 1.60 | 1.60 | 1.60 | 1.60 |
| FR | vegetable: celery | energy | 1 | 1 | 18.00 | 18.00 | 18.00 | 18.00 | 18.00 |
| FR | vegetable: celery | salt | 1 | 1 | 0.60 | 0.60 | 0.60 | 0.60 | 0.60 |
| FR | vegetable: celery | protein | 1 | 1 | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 |
| FR | vegetable: celery | fat | 1 | 1 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 |
| FR | vegetable: celery | fibre | 1 | 0 | — | — | — | — | — |
| FR | vegetable: kale | sugars | 2 | 2 | 8.04 | 8.10 | 8.20 | 8.30 | 8.36 |
| FR | vegetable: kale | energy | 2 | 2 | 38.50 | 39.25 | 40.50 | 41.75 | 42.50 |
| FR | vegetable: kale | salt | 2 | 2 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 |
| FR | vegetable: kale | protein | 2 | 2 | 0.48 | 0.60 | 0.80 | 1.00 | 1.12 |
| FR | vegetable: kale | fat | 2 | 2 | 0.21 | 0.23 | 0.25 | 0.28 | 0.29 |
| FR | vegetable: kale | fibre | 2 | 1 | 1.10 | 1.10 | 1.10 | 1.10 | 1.10 |
| FR | vegetable: tomato | sugars | 310 | 281 | 2.48 | 2.70 | 3.00 | 3.50 | 4.10 |
| FR | vegetable: tomato | energy | 310 | 284 | 15.00 | 17.00 | 19.00 | 22.00 | 24.00 |
| FR | vegetable: tomato | salt | 310 | 277 | 0.03 | 0.30 | 0.40 | 0.60 | 0.71 |
| FR | vegetable: tomato | protein | 310 | 284 | 0.50 | 0.69 | 0.80 | 0.90 | 1.00 |
| FR | vegetable: tomato | fat | 310 | 284 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| FR | vegetable: tomato | fibre | 310 | 139 | 0.00 | 0.50 | 0.80 | 1.20 | 1.20 |
| UK-IE | fruit blend | sugars | 62 | 56 | 4.69 | 8.17 | 10.00 | 11.00 | 11.60 |
| UK-IE | fruit blend | energy | 62 | 56 | 20.88 | 39.75 | 46.50 | 49.25 | 54.25 |
| UK-IE | fruit blend | salt | 62 | 50 | 0.00 | 0.00 | 0.01 | 0.03 | 0.10 |
| UK-IE | fruit blend | protein | 62 | 55 | 0.05 | 0.10 | 0.25 | 0.55 | 0.80 |
| UK-IE | fruit blend | fat | 62 | 56 | 0.00 | 0.00 | 0.10 | 0.20 | 0.50 |
| UK-IE | fruit blend | fibre | 62 | 41 | 0.10 | 0.30 | 0.50 | 0.80 | 1.40 |
| UK-IE | fruit: apple | sugars | 220 | 205 | 8.74 | 9.60 | 10.30 | 11.00 | 11.30 |
| UK-IE | fruit: apple | energy | 220 | 205 | 38.40 | 42.90 | 45.00 | 47.00 | 49.00 |
| UK-IE | fruit: apple | salt | 220 | 169 | 0.00 | 0.00 | 0.00 | 0.01 | 0.08 |
| UK-IE | fruit: apple | protein | 220 | 204 | 0.00 | 0.10 | 0.20 | 0.50 | 0.50 |
| UK-IE | fruit: apple | fat | 220 | 206 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| UK-IE | fruit: apple | fibre | 220 | 127 | 0.00 | 0.00 | 0.30 | 0.50 | 0.60 |
| UK-IE | fruit: cherry | sugars | 4 | 4 | 3.00 | 3.00 | 3.70 | 6.55 | 10.42 |
| UK-IE | fruit: cherry | energy | 4 | 4 | 19.90 | 21.25 | 25.25 | 34.88 | 46.35 |
| UK-IE | fruit: cherry | salt | 4 | 4 | 0.00 | 0.00 | 0.01 | 0.01 | 0.01 |
| UK-IE | fruit: cherry | protein | 4 | 4 | 0.00 | 0.00 | 0.25 | 0.50 | 0.50 |
| UK-IE | fruit: cherry | fat | 4 | 4 | 0.00 | 0.00 | 0.25 | 0.50 | 0.50 |
| UK-IE | fruit: cherry | fibre | 4 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| UK-IE | fruit: cranberry | sugars | 11 | 11 | 0.70 | 1.25 | 4.30 | 4.60 | 5.00 |
| UK-IE | fruit: cranberry | energy | 11 | 11 | 8.00 | 13.00 | 20.00 | 26.50 | 46.00 |
| UK-IE | fruit: cranberry | salt | 11 | 9 | 0.00 | 0.00 | 0.01 | 0.01 | 0.01 |
| UK-IE | fruit: cranberry | protein | 11 | 11 | 0.00 | 0.00 | 0.00 | 0.15 | 0.50 |
| UK-IE | fruit: cranberry | fat | 11 | 11 | 0.00 | 0.00 | 0.00 | 0.05 | 0.50 |
| UK-IE | fruit: cranberry | fibre | 11 | 5 | 0.00 | 0.00 | 0.00 | 0.50 | 3.28 |
| UK-IE | fruit: grape | sugars | 19 | 16 | 9.50 | 14.52 | 15.45 | 16.00 | 17.00 |
| UK-IE | fruit: grape | energy | 19 | 16 | 55.50 | 64.00 | 65.50 | 68.00 | 72.60 |
| UK-IE | fruit: grape | salt | 19 | 13 | 0.00 | 0.00 | 0.00 | 0.03 | 0.09 |
| UK-IE | fruit: grape | protein | 19 | 16 | 0.00 | 0.00 | 0.20 | 0.50 | 0.61 |
| UK-IE | fruit: grape | fat | 19 | 16 | 0.00 | 0.00 | 0.01 | 0.24 | 0.50 |
| UK-IE | fruit: grape | fibre | 19 | 8 | 0.00 | 0.00 | 0.00 | 0.60 | 1.53 |
| UK-IE | fruit: grapefruit | sugars | 9 | 8 | 5.39 | 6.88 | 7.40 | 8.32 | 9.60 |
| UK-IE | fruit: grapefruit | energy | 9 | 8 | 29.30 | 36.50 | 38.50 | 39.45 | 42.96 |
| UK-IE | fruit: grapefruit | salt | 9 | 6 | 0.00 | 0.00 | 0.01 | 0.02 | 0.05 |
| UK-IE | fruit: grapefruit | protein | 9 | 8 | 0.38 | 0.50 | 0.60 | 0.62 | 0.72 |
| UK-IE | fruit: grapefruit | fat | 9 | 8 | 0.00 | 0.08 | 0.10 | 0.23 | 0.50 |
| UK-IE | fruit: grapefruit | fibre | 9 | 6 | 0.00 | 0.07 | 0.40 | 0.65 | 1.15 |
| UK-IE | fruit: lemon | sugars | 21 | 21 | 0.90 | 1.10 | 2.00 | 2.40 | 3.20 |
| UK-IE | fruit: lemon | energy | 21 | 21 | 12.80 | 20.00 | 25.00 | 29.00 | 34.00 |
| UK-IE | fruit: lemon | salt | 21 | 19 | 0.00 | 0.00 | 0.01 | 0.02 | 0.03 |
| UK-IE | fruit: lemon | protein | 21 | 21 | 0.00 | 0.30 | 0.40 | 0.50 | 0.50 |
| UK-IE | fruit: lemon | fat | 21 | 21 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| UK-IE | fruit: lemon | fibre | 21 | 15 | 0.00 | 0.15 | 0.50 | 0.50 | 0.50 |
| UK-IE | fruit: lime | sugars | 5 | 5 | 0.84 | 0.90 | 1.40 | 3.90 | 6.72 |
| UK-IE | fruit: lime | energy | 5 | 5 | 19.00 | 22.00 | 28.00 | 31.00 | 34.00 |
| UK-IE | fruit: lime | salt | 5 | 4 | 0.00 | 0.00 | 0.01 | 0.01 | 0.02 |
| UK-IE | fruit: lime | protein | 5 | 5 | 0.24 | 0.30 | 0.40 | 0.50 | 0.50 |
| UK-IE | fruit: lime | fat | 5 | 5 | 0.08 | 0.20 | 0.20 | 0.50 | 0.50 |
| UK-IE | fruit: lime | fibre | 5 | 5 | 0.16 | 0.40 | 0.50 | 0.50 | 0.56 |
| UK-IE | fruit: mango | sugars | 3 | 3 | 5.24 | 5.90 | 7.00 | 10.00 | 11.80 |
| UK-IE | fruit: mango | energy | 3 | 3 | 21.60 | 24.00 | 28.00 | 42.00 | 50.40 |
| UK-IE | fruit: mango | salt | 3 | 2 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 |
| UK-IE | fruit: mango | protein | 3 | 3 | 0.00 | 0.00 | 0.00 | 0.05 | 0.08 |
| UK-IE | fruit: mango | fat | 3 | 3 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| UK-IE | fruit: mango | fibre | 3 | 2 | 0.71 | 1.02 | 1.55 | 2.08 | 2.39 |
| UK-IE | fruit: orange | sugars | 221 | 214 | 7.70 | 8.40 | 8.92 | 9.60 | 10.50 |
| UK-IE | fruit: orange | energy | 221 | 214 | 37.00 | 41.00 | 42.00 | 46.00 | 48.00 |
| UK-IE | fruit: orange | salt | 221 | 194 | 0.00 | 0.00 | 0.01 | 0.01 | 0.05 |
| UK-IE | fruit: orange | protein | 221 | 214 | 0.50 | 0.50 | 0.60 | 0.70 | 0.80 |
| UK-IE | fruit: orange | fat | 221 | 213 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| UK-IE | fruit: orange | fibre | 221 | 159 | 0.00 | 0.18 | 0.35 | 0.50 | 0.65 |
| UK-IE | fruit: peach | sugars | 2 | 1 | 0.16 | 0.16 | 0.16 | 0.16 | 0.16 |
| UK-IE | fruit: peach | energy | 2 | 1 | 0.80 | 0.80 | 0.80 | 0.80 | 0.80 |
| UK-IE | fruit: peach | salt | 2 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| UK-IE | fruit: peach | protein | 2 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| UK-IE | fruit: peach | fat | 2 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| UK-IE | fruit: peach | fibre | 2 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| UK-IE | fruit: pear | sugars | 4 | 2 | 9.11 | 9.43 | 9.95 | 10.47 | 10.79 |
| UK-IE | fruit: pear | energy | 4 | 2 | 46.88 | 47.90 | 49.60 | 51.30 | 52.32 |
| UK-IE | fruit: pear | salt | 4 | 2 | 0.01 | 0.03 | 0.05 | 0.08 | 0.09 |
| UK-IE | fruit: pear | protein | 4 | 2 | 0.05 | 0.12 | 0.25 | 0.38 | 0.45 |
| UK-IE | fruit: pear | fat | 4 | 2 | 0.02 | 0.05 | 0.10 | 0.15 | 0.18 |
| UK-IE | fruit: pear | fibre | 4 | 1 | 0.60 | 0.60 | 0.60 | 0.60 | 0.60 |
| UK-IE | fruit: pineapple | sugars | 22 | 18 | 7.94 | 10.77 | 11.00 | 11.95 | 12.51 |
| UK-IE | fruit: pineapple | energy | 22 | 18 | 36.20 | 47.25 | 48.50 | 52.75 | 54.00 |
| UK-IE | fruit: pineapple | salt | 22 | 16 | 0.00 | 0.00 | 0.01 | 0.02 | 0.03 |
| UK-IE | fruit: pineapple | protein | 22 | 18 | 0.07 | 0.23 | 0.40 | 0.50 | 0.50 |
| UK-IE | fruit: pineapple | fat | 22 | 18 | 0.00 | 0.00 | 0.10 | 0.40 | 0.50 |
| UK-IE | fruit: pineapple | fibre | 22 | 10 | 0.00 | 0.03 | 0.40 | 1.17 | 1.40 |
| UK-IE | fruit: pomegranate | sugars | 4 | 4 | 6.31 | 11.12 | 13.90 | 27.88 | 52.85 |
| UK-IE | fruit: pomegranate | energy | 4 | 4 | 31.40 | 53.00 | 69.50 | 157.75 | 308.50 |
| UK-IE | fruit: pomegranate | salt | 4 | 3 | 0.00 | 0.01 | 0.02 | 0.08 | 0.12 |
| UK-IE | fruit: pomegranate | protein | 4 | 4 | 0.36 | 0.45 | 0.60 | 0.85 | 1.12 |
| UK-IE | fruit: pomegranate | fat | 4 | 4 | 0.03 | 0.08 | 0.30 | 0.53 | 0.57 |
| UK-IE | fruit: pomegranate | fibre | 4 | 1 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 |
| UK-IE | fruit: prune | sugars | 5 | 5 | 10.40 | 11.00 | 11.00 | 12.00 | 12.60 |
| UK-IE | fruit: prune | energy | 5 | 5 | 65.40 | 69.00 | 69.00 | 69.00 | 72.60 |
| UK-IE | fruit: prune | salt | 5 | 5 | 0.00 | 0.00 | 0.09 | 0.09 | 0.10 |
| UK-IE | fruit: prune | protein | 5 | 5 | 0.22 | 0.40 | 0.50 | 0.70 | 0.70 |
| UK-IE | fruit: prune | fat | 5 | 5 | 0.04 | 0.10 | 0.10 | 0.20 | 0.38 |
| UK-IE | fruit: prune | fibre | 5 | 5 | 0.66 | 0.90 | 1.20 | 1.30 | 1.42 |
| UK-IE | mixed fruit/vegetable | sugars | 11 | 11 | 8.10 | 8.70 | 10.00 | 13.00 | 18.00 |
| UK-IE | mixed fruit/vegetable | energy | 11 | 11 | 39.00 | 43.00 | 46.00 | 60.00 | 76.00 |
| UK-IE | mixed fruit/vegetable | salt | 11 | 8 | 0.00 | 0.00 | 0.01 | 0.05 | 0.10 |
| UK-IE | mixed fruit/vegetable | protein | 11 | 10 | 0.18 | 0.30 | 0.42 | 0.70 | 1.09 |
| UK-IE | mixed fruit/vegetable | fat | 11 | 10 | 0.00 | 0.03 | 0.10 | 0.15 | 0.50 |
| UK-IE | mixed fruit/vegetable | fibre | 11 | 6 | 0.15 | 0.27 | 0.80 | 1.77 | 2.00 |
| UK-IE | vegetable blend | sugars | 1 | 1 | 10.50 | 10.50 | 10.50 | 10.50 | 10.50 |
| UK-IE | vegetable blend | energy | 1 | 1 | 48.00 | 48.00 | 48.00 | 48.00 | 48.00 |
| UK-IE | vegetable blend | salt | 1 | 1 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 |
| UK-IE | vegetable blend | protein | 1 | 1 | 0.30 | 0.30 | 0.30 | 0.30 | 0.30 |
| UK-IE | vegetable blend | fat | 1 | 1 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 |
| UK-IE | vegetable blend | fibre | 1 | 1 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 |
| UK-IE | vegetable: beetroot | sugars | 6 | 6 | 3.48 | 5.45 | 6.80 | 7.10 | 7.65 |
| UK-IE | vegetable: beetroot | energy | 6 | 6 | 24.50 | 31.75 | 36.00 | 38.75 | 39.00 |
| UK-IE | vegetable: beetroot | salt | 6 | 6 | 0.08 | 0.08 | 0.09 | 0.10 | 0.40 |
| UK-IE | vegetable: beetroot | protein | 6 | 6 | 0.40 | 0.64 | 0.85 | 0.97 | 1.10 |
| UK-IE | vegetable: beetroot | fat | 6 | 6 | 0.00 | 0.00 | 0.05 | 0.10 | 0.30 |
| UK-IE | vegetable: beetroot | fibre | 6 | 5 | 0.04 | 0.10 | 2.32 | 2.32 | 2.38 |
| UK-IE | vegetable: carrot | sugars | 4 | 4 | 5.48 | 5.75 | 6.45 | 7.25 | 7.70 |
| UK-IE | vegetable: carrot | energy | 4 | 4 | 25.20 | 27.00 | 29.50 | 33.75 | 38.70 |
| UK-IE | vegetable: carrot | salt | 4 | 4 | 0.03 | 0.08 | 0.12 | 0.13 | 0.14 |
| UK-IE | vegetable: carrot | protein | 4 | 4 | 0.00 | 0.00 | 0.25 | 0.62 | 0.85 |
| UK-IE | vegetable: carrot | fat | 4 | 4 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| UK-IE | vegetable: carrot | fibre | 4 | 3 | 0.00 | 0.00 | 0.00 | 1.35 | 2.16 |
| UK-IE | vegetable: tomato | sugars | 20 | 20 | 2.59 | 2.85 | 3.10 | 3.67 | 4.40 |
| UK-IE | vegetable: tomato | energy | 20 | 20 | 17.90 | 18.00 | 19.00 | 20.25 | 23.10 |
| UK-IE | vegetable: tomato | salt | 20 | 20 | 0.40 | 0.47 | 0.54 | 0.66 | 0.71 |
| UK-IE | vegetable: tomato | protein | 20 | 20 | 0.60 | 0.75 | 0.80 | 0.90 | 1.02 |
| UK-IE | vegetable: tomato | fat | 20 | 20 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| UK-IE | vegetable: tomato | fibre | 20 | 14 | 0.29 | 0.62 | 0.80 | 1.18 | 1.20 |
| US-CA | fruit blend | sugars | 347 | 21 | 4.23 | 8.75 | 9.60 | 10.42 | 12.50 |
| US-CA | fruit blend | energy | 347 | 21 | 21.13 | 38.04 | 45.00 | 50.00 | 54.17 |
| US-CA | fruit blend | salt | 347 | 20 | 0.00 | 0.01 | 0.02 | 0.02 | 0.03 |
| US-CA | fruit blend | protein | 347 | 21 | 0.00 | 0.00 | 0.00 | 0.12 | 0.42 |
| US-CA | fruit blend | fat | 347 | 21 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit blend | fibre | 347 | 11 | 0.00 | 0.00 | 0.00 | 0.00 | 0.28 |
| US-CA | fruit: apple | sugars | 700 | 44 | 9.50 | 10.00 | 11.11 | 11.67 | 13.10 |
| US-CA | fruit: apple | energy | 700 | 44 | 38.06 | 45.00 | 45.92 | 50.00 | 59.40 |
| US-CA | fruit: apple | salt | 700 | 36 | 0.00 | 0.00 | 0.02 | 0.03 | 0.04 |
| US-CA | fruit: apple | protein | 700 | 44 | 0.00 | 0.00 | 0.00 | 0.00 | 0.32 |
| US-CA | fruit: apple | fat | 700 | 44 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: apple | fibre | 700 | 23 | 0.00 | 0.00 | 0.00 | 0.00 | 0.23 |
| US-CA | fruit: cherry | sugars | 51 | 8 | 9.75 | 10.74 | 12.14 | 13.80 | 14.14 |
| US-CA | fruit: cherry | energy | 51 | 8 | 50.49 | 53.89 | 57.87 | 61.46 | 73.67 |
| US-CA | fruit: cherry | salt | 51 | 8 | 0.00 | 0.00 | 0.01 | 0.03 | 0.04 |
| US-CA | fruit: cherry | protein | 51 | 8 | 0.00 | 0.25 | 0.63 | 0.83 | 0.84 |
| US-CA | fruit: cherry | fat | 51 | 8 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: cherry | fibre | 51 | 5 | 0.00 | 0.00 | 0.00 | 0.42 | 0.65 |
| US-CA | fruit: cranberry | sugars | 78 | 7 | 0.00 | 1.88 | 3.75 | 5.62 | 9.17 |
| US-CA | fruit: cranberry | energy | 78 | 7 | 2.10 | 13.56 | 29.17 | 31.08 | 38.13 |
| US-CA | fruit: cranberry | salt | 78 | 7 | 0.01 | 0.01 | 0.02 | 0.03 | 0.03 |
| US-CA | fruit: cranberry | protein | 78 | 7 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: cranberry | fat | 78 | 7 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: cranberry | fibre | 78 | 6 | 0.00 | 0.00 | 0.64 | 4.17 | 5.13 |
| US-CA | fruit: grape | sugars | 214 | 10 | 10.32 | 14.58 | 15.00 | 15.25 | 15.42 |
| US-CA | fruit: grape | energy | 214 | 10 | 56.78 | 58.33 | 61.36 | 62.38 | 88.60 |
| US-CA | fruit: grape | salt | 214 | 10 | 0.01 | 0.01 | 0.02 | 0.04 | 1.92 |
| US-CA | fruit: grape | protein | 214 | 10 | 0.00 | 0.10 | 0.42 | 0.44 | 1.47 |
| US-CA | fruit: grape | fat | 214 | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 1.09 |
| US-CA | fruit: grape | fibre | 214 | 3 | 0.18 | 0.45 | 0.90 | 1.95 | 2.58 |
| US-CA | fruit: grapefruit | sugars | 99 | 5 | 6.79 | 7.08 | 7.08 | 7.08 | 8.33 |
| US-CA | fruit: grapefruit | energy | 99 | 5 | 37.70 | 38.00 | 38.00 | 39.80 | 40.92 |
| US-CA | fruit: grapefruit | salt | 99 | 5 | 0.00 | 0.00 | 0.01 | 0.01 | 0.02 |
| US-CA | fruit: grapefruit | protein | 99 | 5 | 0.32 | 0.42 | 0.42 | 0.42 | 0.67 |
| US-CA | fruit: grapefruit | fat | 99 | 5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.15 |
| US-CA | fruit: grapefruit | fibre | 99 | 3 | 0.00 | 0.00 | 0.00 | 0.40 | 0.64 |
| US-CA | fruit: lemon | sugars | 107 | 3 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: lemon | energy | 107 | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 20.00 |
| US-CA | fruit: lemon | salt | 107 | 4 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: lemon | protein | 107 | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: lemon | fat | 107 | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: lemon | fibre | 107 | 3 | 0.08 | 0.20 | 0.40 | 0.40 | 0.40 |
| US-CA | fruit: lime | sugars | 84 | 2 | 0.39 | 0.97 | 1.95 | 2.92 | 3.51 |
| US-CA | fruit: lime | energy | 84 | 2 | 1.70 | 4.25 | 8.50 | 12.75 | 15.30 |
| US-CA | fruit: lime | salt | 84 | 2 | 0.00 | 0.00 | 0.01 | 0.01 | 0.01 |
| US-CA | fruit: lime | protein | 84 | 2 | 0.05 | 0.12 | 0.25 | 0.38 | 0.45 |
| US-CA | fruit: lime | fat | 84 | 2 | 0.05 | 0.12 | 0.25 | 0.38 | 0.45 |
| US-CA | fruit: lime | fibre | 84 | 2 | 0.05 | 0.12 | 0.25 | 0.38 | 0.45 |
| US-CA | fruit: mango | sugars | 29 | 6 | 9.18 | 10.31 | 11.88 | 12.50 | 17.25 |
| US-CA | fruit: mango | energy | 29 | 6 | 39.35 | 44.46 | 47.92 | 50.00 | 65.00 |
| US-CA | fruit: mango | salt | 29 | 6 | 0.01 | 0.02 | 0.03 | 0.05 | 0.07 |
| US-CA | fruit: mango | protein | 29 | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.06 |
| US-CA | fruit: mango | fat | 29 | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: mango | fibre | 29 | 5 | 0.00 | 0.00 | 0.20 | 0.31 | 0.36 |
| US-CA | fruit: orange | sugars | 906 | 101 | 8.40 | 9.17 | 9.30 | 9.61 | 10.11 |
| US-CA | fruit: orange | energy | 906 | 101 | 43.33 | 45.83 | 46.00 | 47.30 | 50.00 |
| US-CA | fruit: orange | salt | 906 | 95 | 0.00 | 0.00 | 0.00 | 0.01 | 0.02 |
| US-CA | fruit: orange | protein | 906 | 101 | 0.40 | 0.68 | 0.83 | 0.83 | 0.85 |
| US-CA | fruit: orange | fat | 906 | 101 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: orange | fibre | 906 | 83 | 0.00 | 0.00 | 0.00 | 0.28 | 0.41 |
| US-CA | fruit: peach | sugars | 8 | 0 | — | — | — | — | — |
| US-CA | fruit: peach | energy | 8 | 0 | — | — | — | — | — |
| US-CA | fruit: peach | salt | 8 | 0 | — | — | — | — | — |
| US-CA | fruit: peach | protein | 8 | 0 | — | — | — | — | — |
| US-CA | fruit: peach | fat | 8 | 0 | — | — | — | — | — |
| US-CA | fruit: peach | fibre | 8 | 0 | — | — | — | — | — |
| US-CA | fruit: pear | sugars | 14 | 2 | 9.76 | 10.14 | 10.79 | 11.44 | 11.82 |
| US-CA | fruit: pear | energy | 14 | 2 | 51.25 | 53.12 | 56.25 | 59.38 | 61.25 |
| US-CA | fruit: pear | salt | 14 | 1 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 |
| US-CA | fruit: pear | protein | 14 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: pear | fat | 14 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: pear | fibre | 14 | 0 | — | — | — | — | — |
| US-CA | fruit: pineapple | sugars | 79 | 12 | 7.09 | 10.11 | 10.83 | 12.40 | 12.49 |
| US-CA | fruit: pineapple | energy | 79 | 12 | 42.97 | 44.75 | 54.00 | 54.75 | 56.50 |
| US-CA | fruit: pineapple | salt | 79 | 12 | 0.00 | 0.00 | 0.01 | 0.02 | 0.05 |
| US-CA | fruit: pineapple | protein | 79 | 12 | 0.00 | 0.00 | 0.39 | 0.46 | 0.57 |
| US-CA | fruit: pineapple | fat | 79 | 12 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: pineapple | fibre | 79 | 9 | 0.00 | 0.00 | 0.00 | 0.40 | 0.74 |
| US-CA | fruit: pomegranate | sugars | 51 | 8 | 4.00 | 8.63 | 13.53 | 14.41 | 14.46 |
| US-CA | fruit: pomegranate | energy | 51 | 8 | 41.09 | 58.25 | 66.67 | 67.80 | 86.46 |
| US-CA | fruit: pomegranate | salt | 51 | 8 | 0.00 | 0.01 | 0.01 | 0.02 | 0.03 |
| US-CA | fruit: pomegranate | protein | 51 | 8 | 0.00 | 0.00 | 0.08 | 0.25 | 0.55 |
| US-CA | fruit: pomegranate | fat | 51 | 8 | 0.00 | 0.00 | 0.00 | 0.01 | 0.07 |
| US-CA | fruit: pomegranate | fibre | 51 | 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.71 |
| US-CA | fruit: prune | sugars | 53 | 3 | 9.83 | 10.21 | 10.83 | 12.71 | 13.83 |
| US-CA | fruit: prune | energy | 53 | 3 | 75.00 | 75.00 | 75.00 | 75.00 | 75.00 |
| US-CA | fruit: prune | salt | 53 | 3 | 0.01 | 0.01 | 0.02 | 0.02 | 0.03 |
| US-CA | fruit: prune | protein | 53 | 3 | 0.42 | 0.42 | 0.42 | 0.62 | 0.75 |
| US-CA | fruit: prune | fat | 53 | 3 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | fruit: prune | fibre | 53 | 3 | 0.57 | 0.82 | 1.25 | 1.25 | 1.25 |
| US-CA | mixed fruit/vegetable | sugars | 74 | 1 | 8.75 | 8.75 | 8.75 | 8.75 | 8.75 |
| US-CA | mixed fruit/vegetable | energy | 74 | 1 | 45.83 | 45.83 | 45.83 | 45.83 | 45.83 |
| US-CA | mixed fruit/vegetable | salt | 74 | 1 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 |
| US-CA | mixed fruit/vegetable | protein | 74 | 1 | 0.83 | 0.83 | 0.83 | 0.83 | 0.83 |
| US-CA | mixed fruit/vegetable | fat | 74 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | mixed fruit/vegetable | fibre | 74 | 1 | 0.42 | 0.42 | 0.42 | 0.42 | 0.42 |
| US-CA | vegetable blend | sugars | 13 | 0 | — | — | — | — | — |
| US-CA | vegetable blend | energy | 13 | 0 | — | — | — | — | — |
| US-CA | vegetable blend | salt | 13 | 0 | — | — | — | — | — |
| US-CA | vegetable blend | protein | 13 | 0 | — | — | — | — | — |
| US-CA | vegetable blend | fat | 13 | 0 | — | — | — | — | — |
| US-CA | vegetable blend | fibre | 13 | 0 | — | — | — | — | — |
| US-CA | vegetable: beetroot | sugars | 23 | 2 | 5.29 | 5.73 | 6.46 | 7.19 | 7.63 |
| US-CA | vegetable: beetroot | energy | 23 | 2 | 30.00 | 31.25 | 33.33 | 35.42 | 36.67 |
| US-CA | vegetable: beetroot | salt | 23 | 2 | 0.06 | 0.07 | 0.09 | 0.11 | 0.13 |
| US-CA | vegetable: beetroot | protein | 23 | 2 | 0.87 | 0.94 | 1.04 | 1.15 | 1.21 |
| US-CA | vegetable: beetroot | fat | 23 | 2 | 0.03 | 0.06 | 0.13 | 0.19 | 0.23 |
| US-CA | vegetable: beetroot | fibre | 23 | 2 | 0.54 | 0.73 | 1.04 | 1.35 | 1.54 |
| US-CA | vegetable: carrot | sugars | 24 | 4 | 5.06 | 5.15 | 5.31 | 5.45 | 5.51 |
| US-CA | vegetable: carrot | energy | 24 | 4 | 28.27 | 28.67 | 29.03 | 32.29 | 37.92 |
| US-CA | vegetable: carrot | salt | 24 | 4 | 0.14 | 0.15 | 0.15 | 0.16 | 0.16 |
| US-CA | vegetable: carrot | protein | 24 | 4 | 0.53 | 0.70 | 0.82 | 0.85 | 0.87 |
| US-CA | vegetable: carrot | fat | 24 | 4 | 0.00 | 0.00 | 0.00 | 0.03 | 0.08 |
| US-CA | vegetable: carrot | fibre | 24 | 4 | 0.12 | 0.30 | 0.41 | 0.42 | 0.44 |
| US-CA | vegetable: celery | sugars | 6 | 1 | 1.41 | 1.41 | 1.41 | 1.41 | 1.41 |
| US-CA | vegetable: celery | energy | 6 | 1 | 14.12 | 14.12 | 14.12 | 14.12 | 14.12 |
| US-CA | vegetable: celery | salt | 6 | 1 | 0.19 | 0.19 | 0.19 | 0.19 | 0.19 |
| US-CA | vegetable: celery | protein | 6 | 1 | 0.56 | 0.56 | 0.56 | 0.56 | 0.56 |
| US-CA | vegetable: celery | fat | 6 | 1 | 0.14 | 0.14 | 0.14 | 0.14 | 0.14 |
| US-CA | vegetable: celery | fibre | 6 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | vegetable: cucumber | sugars | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: cucumber | energy | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: cucumber | salt | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: cucumber | protein | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: cucumber | fat | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: cucumber | fibre | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: kale | sugars | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: kale | energy | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: kale | salt | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: kale | protein | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: kale | fat | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: kale | fibre | 3 | 0 | — | — | — | — | — |
| US-CA | vegetable: spinach | sugars | 1 | 0 | — | — | — | — | — |
| US-CA | vegetable: spinach | energy | 1 | 0 | — | — | — | — | — |
| US-CA | vegetable: spinach | salt | 1 | 0 | — | — | — | — | — |
| US-CA | vegetable: spinach | protein | 1 | 0 | — | — | — | — | — |
| US-CA | vegetable: spinach | fat | 1 | 0 | — | — | — | — | — |
| US-CA | vegetable: spinach | fibre | 1 | 0 | — | — | — | — | — |
| US-CA | vegetable: tomato | sugars | 141 | 5 | 2.40 | 2.40 | 2.92 | 3.33 | 4.93 |
| US-CA | vegetable: tomato | energy | 141 | 5 | 17.80 | 19.00 | 20.00 | 25.00 | 31.00 |
| US-CA | vegetable: tomato | salt | 141 | 5 | 0.16 | 0.41 | 0.48 | 0.71 | 0.96 |
| US-CA | vegetable: tomato | protein | 141 | 5 | 0.57 | 0.80 | 0.83 | 0.90 | 0.96 |
| US-CA | vegetable: tomato | fat | 141 | 5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| US-CA | vegetable: tomato | fibre | 141 | 5 | 0.24 | 0.60 | 0.80 | 0.80 | 0.92 |

</details>

<details><summary>Candidate sugar-tail rule sensitivity</summary>

| Region | Subformat | Valid sugars | French P20 | French P25 | French P30 | N at P20 | N at P25 | N at P30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FR | fruit blend | 673 | 9.00 | 9.30 | 9.50 | 138 | 182 | 222 |
| FR | fruit: apple | 1605 | 9.70 | 9.80 | 10.00 | 358 | 446 | 708 |
| FR | fruit: cranberry | 69 | 4.00 | 4.00 | 4.14 | 19 | 19 | 21 |
| FR | fruit: grape | 331 | 15.00 | 15.00 | 15.00 | 107 | 107 | 107 |
| FR | fruit: grapefruit | 181 | 7.50 | 7.60 | 7.60 | 37 | 59 | 59 |
| FR | fruit: lemon | 296 | 1.40 | 1.70 | 1.70 | 60 | 111 | 111 |
| FR | fruit: mango | 58 | 8.68 | 9.12 | 9.51 | 12 | 15 | 18 |
| FR | fruit: orange | 1428 | 8.54 | 8.60 | 8.70 | 286 | 362 | 608 |
| FR | fruit: pear | 128 | 9.00 | 9.10 | 9.51 | 27 | 35 | 39 |
| FR | fruit: pineapple | 287 | 10.00 | 10.40 | 11.00 | 67 | 73 | 151 |
| FR | fruit: pomegranate | 128 | 11.50 | 12.00 | 12.00 | 26 | 47 | 47 |
| FR | fruit: prune | 35 | 12.58 | 13.00 | 13.00 | 7 | 20 | 20 |
| FR | mixed fruit/vegetable | 92 | 7.02 | 7.47 | 7.53 | 19 | 23 | 28 |
| FR | vegetable: beetroot | 37 | 6.98 | 7.00 | 7.10 | 8 | 10 | 12 |
| FR | vegetable: carrot | 129 | 5.00 | 5.30 | 5.50 | 27 | 35 | 45 |
| FR | vegetable: tomato | 281 | 2.70 | 2.70 | 2.80 | 80 | 80 | 100 |
| UK-IE | fruit blend | 56 | 9.00 | 9.30 | 9.50 | 19 | 20 | 21 |
| UK-IE | fruit: apple | 205 | 9.70 | 9.80 | 10.00 | 55 | 66 | 90 |
| UK-IE | fruit: lemon | 21 | 1.40 | 1.70 | 1.70 | 8 | 10 | 10 |
| UK-IE | fruit: orange | 214 | 8.54 | 8.60 | 8.70 | 65 | 73 | 82 |
| UK-IE | vegetable: tomato | 20 | 2.70 | 2.70 | 2.80 | 5 | 5 | 5 |
| US-CA | fruit blend | 21 | 9.00 | 9.30 | 9.50 | 8 | 10 | 10 |
| US-CA | fruit: apple | 44 | 9.70 | 9.80 | 10.00 | 8 | 8 | 13 |
| US-CA | fruit: orange | 101 | 8.54 | 8.60 | 8.70 | 13 | 13 | 13 |

</details>

<details><summary>Low versus other sugars within named composition</summary>

| Region | Subformat | <5 joint N | ≥5 joint N | Energy low | Energy other | Salt low | Salt other |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FR | fruit blend | 23 | 650 | 21.00 | 46.00 | 0.00 | 0.00 |
| FR | fruit: apple | 17 | 1586 | 43.00 | 45.00 | 0.01 | 0.01 |
| FR | fruit: cranberry | 26 | 43 | 22.00 | 46.00 | 0.01 | 0.01 |
| FR | fruit: lemon | 280 | 14 | 27.00 | 44.30 | 0.00 | 0.00 |
| FR | fruit: orange | 36 | 1389 | 22.92 | 43.00 | 0.01 | 0.00 |
| FR | fruit: pineapple | 11 | 276 | 27.00 | 49.00 | 0.01 | 0.00 |
| FR | vegetable: carrot | 22 | 107 | 31.00 | 31.00 | 0.10 | 0.10 |

</details>

<details><summary>Representative and boundary observations</summary>

| Region | Subformat | Example | Text GTIN | Recorded name | Sugars | Energy | Salt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FR | fruit: apple | near typical | 3564980000292 | Jus de pommes | 10.28 | 46.00 | 0.10 |
| FR | fruit: apple | near sugar 5 boundary | 5601192601515 | Jus de pomme | 5.20 | 23.00 | 0.01 |
| FR | fruit: apple | very-low sugars | 3274490970854 | Jus de pomme | 0.00 | 48.00 | 0.00 |
| FR | fruit: lemon | near typical | 0560507103555 | Pur jus de citron de Sicile | 1.80 | 28.00 | 0.01 |
| FR | fruit: lemon | near sugar 5 boundary | 3439495012101 | Jus de citron | 6.80 | 30.00 | 0.00 |
| FR | fruit: lemon | very-low sugars | 0036192122671 | Organic Pure Lemon Juice | 0.00 | 0.00 | 0.00 |
| FR | fruit: orange | near typical | 0016300151700 | Florida's Natural - Orange Juice - Original | 9.00 | 46.00 | 0.00 |
| FR | fruit: orange | near sugar 5 boundary | 0025000100710 | Simply Light Orange Juice Pulp Free | 4.65 | 21.13 | 0.01 |
| FR | fruit: orange | very-low sugars | 5290040003627 | Prima Orange Juice | 0.00 | 47.00 | 0.00 |
| FR | vegetable: tomato | near typical | 20495916 | Jus de tomate | 3.00 | 16.00 | 0.30 |
| FR | vegetable: tomato | near sugar 5 boundary | 7613269580027 | Jus de Tomate du Valais | 5.00 | 50.90 | — |
| FR | vegetable: tomato | very-low sugars | 26088594 | Jus de tomate | 0.00 | 1.00 | 0.00 |
| UK-IE | fruit: apple | near typical | 00438087 | british cloudy apple juice | 10.30 | 48.00 | — |
| UK-IE | fruit: apple | near sugar 5 boundary | 4088600123929 | Apple Juice | 6.73 | 28.00 | 0.01 |
| UK-IE | fruit: apple | very-low sugars | 00488464 | Apple Juice from Concentrate | 0.50 | 46.00 | 0.06 |
| UK-IE | fruit: lemon | near typical | 5013635410415 | KTC Lemon Juice | 2.00 | 27.00 | 0.00 |
| UK-IE | fruit: lemon | near sugar 5 boundary | 5010251638230 | Lemon Juice | 5.20 | 35.00 | 0.00 |
| UK-IE | fruit: orange | near typical | 2000000139590 | Princes Orange Juice | 8.90 | 41.00 | 0.01 |
| UK-IE | fruit: orange | near sugar 5 boundary | 5000129380910 | orange juice | 5.67 | 28.68 | 0.01 |
| UK-IE | fruit: orange | very-low sugars | 0793591227184 | Orange Juice | 0.00 | 0.00 | 0.00 |
| UK-IE | vegetable: tomato | near typical | 5000128442688 | Tomato juice | 3.10 | 19.00 | 0.48 |
| UK-IE | vegetable: tomato | near sugar 5 boundary | 00846677 | Spiced Tomato Juice | 5.30 | 30.00 | 0.50 |

</details>
