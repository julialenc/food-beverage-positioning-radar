# Savoury snacks · Wave 2 formulation CHECK

**Closed by Julia on 16 November 2026.** The three format decisions below are accepted. For potato crisps, retain observed construction alongside the nutritional profile. An explicit baked or fried description can refine the comparison; missing wording leaves the cooking method unknown. The ≤20 g fat/100 g cutoff identifies a descriptive low-fat tail across the two primary regions. Its exact boundary is a research choice. For tortilla/corn chips, retain the commercial format and describe the continuous fat variation. For puffed/extruded snacks, distinguish potato, pulse and other identifiable bases or constructions when product evidence supports them. Further nutritional subdivision remains unsupported.

**Learning for the Radar.** Commercial format establishes the comparison. Within that comparison the evidence can support an individual-product formulation profile, a continuous nutritional spectrum, or a finer commercial distinction. The useful depth of the hierarchy varies by product. Communicated positioning remains a separate layer assessed on packs with usable evidence.

**Decision. Retain a descriptive lower-fat profile within potato crisps. Keep tortilla/corn chips as a commercial format with nutritional variation. For puffed/extruded snacks, retain the construction and base-material descriptors; the evidence for an additional nutritional segment is insufficient.**

| Commercial form | France · assignments / valid fat | UK/Ireland · assignments / valid fat | US/Canada · assignments / valid fat |
|---|---:|---:|---:|
| Potato crisps | 2,932 / 2,807 | 825 / 773 | 4,273 / 457 |
| Tortilla/corn chips | 621 / 586 | 190 / 183 | 2,418 / 305 |
| Puffed/extruded | 409 / 389 | 128 / 121 | 300 / 83 |

**Potato crisps.** Use a product-level rule of **≤20 g observed fat per 100 g** within identifiable potato crisps. It identifies 100/2,807 French and 90/773 UK/Irish assignments; the exploratory US/Canadian count is 53/457. The low-fat products had median fat of **13 g in both primary regions**, against 32.1 and 29.0 g in the remaining products. Their energy medians were 428 versus 529 kcal in France and 429 versus 512 kcal in UK/Ireland. Energy and total fat are related. Other measurements give the comparison commercial meaning: median saturated fat was roughly halved, whereas median protein differed by only 0.4 g in each region, in opposite directions, and median fibre was virtually identical. Fibre coverage was 67% in FR and 81% in UK/IE; it is optional for assignment. Salt medians were modestly lower in the lower-fat products. The data do not show how individual manufacturers achieved these differences.

Some qualifying products explicitly say baked. The pattern also includes 17 French and 12 UK/Irish qualifiers with potato-crisp form evidence in the name, and 93 and 83 qualifiers respectively after removing barcodes seen in the other primary region. The lower energy difference persisted in comparisons within the same recorded flavour and construction cues, covering 74 and 68 low-fat products with valid energy. Unspecified wording can hide real construction differences. Changing the boundary to 18 or 22 g changes the French count from 100 to 82 or 143 and the UK/Irish count from 90 to 79 or 116. The low-fat end recurs, while the exact cutoff remains a research convention. A representative French product, *Cuites au four*, has 13 g fat and 439 kcal. A French sea-salt crisp sits exactly at 20 g; *Salt & vinegar chiplets* sits just outside at 20.8 g and a similar 463 kcal. These near neighbours explain why the label should travel with the measured amount.

**Tortilla/corn chips.** Median fat was already 22.0 g in France and 22.3 g in UK/Ireland. Moving the cutoff from 18 to 22 g changes the count from **34 to 313** in France and **17 to 79** in UK/Ireland. At 20 g, French protein and salt medians were identical on either side (6.6 and 1.1 g respectively); median energy differed by only 21 kcal. UK/Ireland showed a similarly modest energy contrast. Keep the fat distribution and saturated-fat detail as measurements. Applying the potato rule here would divide the middle of the format.

**Puffed/extruded snacks.** Heterogeneity depends on which products OFF captures. In UK/Ireland the middle half ranged from **14.7 to 30.0 g fat**, substantially wider than potato crisps (25.3–30.7). In France the two middle ranges were similar (26.0–31.0 versus 28.9–34.0). Higher protein often tracked commercially visible base material: among UK/Irish puffs with pulse-only base wording, 9/10 with valid protein reached 10 g protein; among potato-only wording, 0/83 did. The corresponding French counts were 3/3 and 0/363. At equal recorded base, construction and flavour, the lower-fat energy comparison had support for only three French lower-fat products and none in UK/Ireland under the three-per-arm floor. The broad format combines stacked potato products, popped products and pulse puffs. Report that variation and preserve those descriptors. A separate formulation split within like-for-like puffs remains exploratory.

**Evidence and scope.** The [versioned analysis](savoury_snacks_v1.py) reuses the corrected master reader, prior assignments and governed nutrient validity. The [product-level classifications](savoury_snack_assignments_v1.parquet) cover all 151,461 governed snack assignments on their original text GTIN, region and category. Commercial labels use names and OFF tags, independently of all nutrient values. Generic chips wording alone leaves the material unresolved. Puffed construction can refine an explicit material; incompatible cues and sweet or mixed contexts are retained separately. The screen also identifies popcorn, pretzels, savoury crackers, nuts/seeds, breadsticks, rice cakes, mixes and other supported forms. It is conservative, particularly for names without explicit material or construction wording. Prior confidence describes the inherited subtype.

All six nutrients use their own valid denominators in the named food-basis groups. Energy is kcal/100 g; the others are g/100 g. Percentiles describe recorded variation, including observed zeros. The matched-wording tables compare medians among lower-fat and other products in strata with at least three in each arm, weighting by the number of lower-fat products. Wording establishes observed descriptors only. US/Canadian comparisons describe the measurable subset. The nullable fat screen is a diagnostic in each primary format; only the potato comparison receives a retained formulation label. Missing fat stays unknown.

One French tortilla/corn-chip distinction warrants recording. Among products with 20–25 g total fat, 42/378 had at least 30% of their fat recorded as saturated, compared with 2/126 in UK/Ireland. Median saturated fat was 2.1 g in each region, but the French 90th percentile reached 9.0 g versus 2.75 g in UK/Ireland. This identifies an exploratory French tail at comparable total fat; evidence for a recurring profile across the primary regions is limited.

<!-- evidence -->

<details><summary>Commercial screen</summary>

| Outcome | FR | UK-IE | US-CA |
| --- | --- | --- | --- |
| breadsticks | 6 | 0 | 8 |
| conflicting | 344 | 163 | 641 |
| nuts/seeds | 22 | 5 | 53 |
| other chips | 328 | 117 | 921 |
| other savoury | 35 | 7 | 826 |
| outside screen | 65049 | 7874 | 45787 |
| popcorn | 462 | 184 | 2133 |
| potato crisps | 2932 | 825 | 4273 |
| pretzels | 82 | 36 | 1660 |
| puffed/extruded | 409 | 128 | 300 |
| rice cakes | 83 | 18 | 75 |
| savoury crackers | 1770 | 328 | 3894 |
| savoury mix | 15 | 7 | 397 |
| scope caution | 1514 | 65 | 728 |
| scope unresolved | 4 | 0 | 23 |
| tortilla/corn chips | 621 | 190 | 2418 |
| unresolved | 1606 | 553 | 1542 |

</details>

<details><summary>Coverage and variation per 100 g</summary>

| Form | Region | Nutrient | N | Valid | Coverage | P10 | Q1 | Median | Q3 | P90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| potato crisps | FR | fat | 2932 | 2807 | 96% | 25.00 | 28.90 | 32.00 | 34.00 | 37.00 |
| potato crisps | FR | saturated_fat | 2932 | 2801 | 96% | 2.20 | 2.60 | 3.00 | 3.50 | 4.50 |
| potato crisps | FR | salt | 2932 | 2796 | 95% | 0.65 | 1.00 | 1.22 | 1.46 | 1.80 |
| potato crisps | FR | protein | 2932 | 2807 | 96% | 5.00 | 5.70 | 6.10 | 6.50 | 7.20 |
| potato crisps | FR | fibre | 2932 | 1964 | 67% | 1.34 | 4.00 | 4.50 | 5.00 | 5.67 |
| potato crisps | FR | energy | 2932 | 2787 | 95% | 485.00 | 508.80 | 527.00 | 543.00 | 557.00 |
| potato crisps | UK-IE | fat | 825 | 773 | 94% | 18.00 | 25.25 | 28.80 | 30.70 | 32.48 |
| potato crisps | UK-IE | saturated_fat | 825 | 766 | 93% | 1.60 | 2.20 | 2.50 | 3.00 | 3.57 |
| potato crisps | UK-IE | salt | 825 | 754 | 91% | 0.62 | 0.91 | 1.20 | 1.58 | 2.13 |
| potato crisps | UK-IE | protein | 825 | 771 | 93% | 4.30 | 5.60 | 6.30 | 6.82 | 7.60 |
| potato crisps | UK-IE | fibre | 825 | 667 | 81% | 1.93 | 3.40 | 4.10 | 4.80 | 6.00 |
| potato crisps | UK-IE | energy | 825 | 765 | 93% | 441.40 | 491.00 | 509.00 | 523.00 | 535.43 |
| potato crisps | US-CA | fat | 4273 | 457 | 11% | 17.86 | 26.67 | 31.00 | 32.92 | 35.71 |
| potato crisps | US-CA | saturated_fat | 4273 | 451 | 11% | 1.79 | 3.00 | 3.57 | 5.36 | 8.93 |
| potato crisps | US-CA | salt | 4273 | 450 | 11% | 0.76 | 1.10 | 1.42 | 1.70 | 2.17 |
| potato crisps | US-CA | protein | 4273 | 455 | 11% | 3.57 | 6.00 | 7.14 | 7.14 | 7.14 |
| potato crisps | US-CA | fibre | 4273 | 418 | 10% | 2.10 | 3.57 | 3.57 | 4.20 | 7.14 |
| potato crisps | US-CA | energy | 4273 | 459 | 11% | 470.45 | 500.00 | 535.71 | 536.00 | 571.43 |
| puffed/extruded | FR | fat | 409 | 389 | 95% | 24.80 | 26.00 | 30.00 | 31.00 | 32.20 |
| puffed/extruded | FR | saturated_fat | 409 | 392 | 96% | 2.20 | 2.50 | 3.00 | 3.40 | 6.40 |
| puffed/extruded | FR | salt | 409 | 392 | 96% | 0.85 | 1.20 | 1.40 | 1.60 | 1.80 |
| puffed/extruded | FR | protein | 409 | 394 | 96% | 4.00 | 4.12 | 4.50 | 5.28 | 6.40 |
| puffed/extruded | FR | fibre | 409 | 308 | 75% | 2.40 | 2.70 | 3.50 | 3.90 | 4.70 |
| puffed/extruded | FR | energy | 409 | 393 | 96% | 486.00 | 500.00 | 508.00 | 521.00 | 532.96 |
| puffed/extruded | UK-IE | fat | 128 | 121 | 95% | 12.94 | 14.71 | 29.00 | 30.00 | 32.00 |
| puffed/extruded | UK-IE | saturated_fat | 128 | 121 | 95% | 1.18 | 1.50 | 2.70 | 3.00 | 5.00 |
| puffed/extruded | UK-IE | salt | 128 | 121 | 95% | 0.59 | 1.00 | 1.40 | 1.60 | 1.91 |
| puffed/extruded | UK-IE | protein | 128 | 121 | 95% | 4.10 | 4.70 | 6.00 | 6.60 | 12.67 |
| puffed/extruded | UK-IE | fibre | 128 | 104 | 81% | 2.00 | 2.90 | 3.63 | 4.50 | 5.38 |
| puffed/extruded | UK-IE | energy | 128 | 118 | 92% | 425.26 | 445.08 | 509.00 | 522.75 | 530.30 |
| puffed/extruded | US-CA | fat | 300 | 83 | 28% | 17.14 | 28.57 | 32.14 | 32.14 | 32.14 |
| puffed/extruded | US-CA | saturated_fat | 300 | 82 | 27% | 2.28 | 3.57 | 8.87 | 8.93 | 8.99 |
| puffed/extruded | US-CA | salt | 300 | 81 | 27% | 1.01 | 1.30 | 1.52 | 1.79 | 2.59 |
| puffed/extruded | US-CA | protein | 300 | 83 | 28% | 3.57 | 3.57 | 3.57 | 5.79 | 7.14 |
| puffed/extruded | US-CA | fibre | 300 | 81 | 27% | 0.00 | 2.80 | 3.57 | 3.60 | 3.80 |
| puffed/extruded | US-CA | energy | 300 | 82 | 27% | 464.29 | 507.13 | 535.71 | 535.71 | 536.00 |
| tortilla/corn chips | FR | fat | 621 | 586 | 94% | 20.00 | 20.00 | 22.00 | 25.71 | 26.70 |
| tortilla/corn chips | FR | saturated_fat | 621 | 585 | 94% | 1.80 | 2.00 | 2.20 | 3.10 | 9.00 |
| tortilla/corn chips | FR | salt | 621 | 583 | 94% | 0.63 | 0.80 | 1.10 | 1.50 | 1.72 |
| tortilla/corn chips | FR | protein | 621 | 586 | 94% | 5.50 | 6.10 | 6.60 | 6.80 | 7.50 |
| tortilla/corn chips | FR | fibre | 621 | 403 | 65% | 2.01 | 3.90 | 4.00 | 5.70 | 6.50 |
| tortilla/corn chips | FR | energy | 621 | 581 | 94% | 464.63 | 472.00 | 480.00 | 500.00 | 520.00 |
| tortilla/corn chips | UK-IE | fat | 190 | 183 | 96% | 19.10 | 21.00 | 22.30 | 24.55 | 26.00 |
| tortilla/corn chips | UK-IE | saturated_fat | 190 | 179 | 94% | 1.80 | 2.00 | 2.20 | 2.60 | 3.42 |
| tortilla/corn chips | UK-IE | salt | 190 | 172 | 91% | 0.57 | 0.76 | 0.99 | 1.28 | 1.80 |
| tortilla/corn chips | UK-IE | protein | 190 | 183 | 96% | 5.50 | 5.90 | 6.40 | 6.89 | 7.80 |
| tortilla/corn chips | UK-IE | fibre | 190 | 159 | 84% | 3.00 | 4.40 | 5.50 | 6.15 | 7.64 |
| tortilla/corn chips | UK-IE | energy | 190 | 181 | 95% | 467.86 | 477.00 | 482.00 | 497.00 | 507.00 |
| tortilla/corn chips | US-CA | fat | 2418 | 305 | 13% | 14.03 | 21.43 | 25.00 | 28.57 | 32.14 |
| tortilla/corn chips | US-CA | saturated_fat | 2418 | 303 | 13% | 1.50 | 1.79 | 3.57 | 3.57 | 6.17 |
| tortilla/corn chips | US-CA | salt | 2418 | 302 | 12% | 0.40 | 0.76 | 1.07 | 1.60 | 2.07 |
| tortilla/corn chips | US-CA | protein | 2418 | 305 | 13% | 3.54 | 6.80 | 7.14 | 7.14 | 7.14 |
| tortilla/corn chips | US-CA | fibre | 2418 | 289 | 12% | 1.69 | 3.57 | 3.60 | 7.14 | 7.14 |
| tortilla/corn chips | US-CA | energy | 2418 | 304 | 13% | 464.29 | 500.00 | 500.00 | 535.71 | 535.71 |

</details>

<details><summary>Lower-fat sensitivity</summary>

| Form | Region | Valid fat | ≤15 g | ≤18 g | ≤20 g | ≤22 g | ≤25 g | Share ≤20 g |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| potato crisps | FR | 2807 | 65 | 82 | 100 | 143 | 309 | 3.6% |
| potato crisps | UK-IE | 773 | 67 | 79 | 90 | 116 | 189 | 11.6% |
| potato crisps | US-CA | 457 | 34 | 49 | 53 | 70 | 108 | 11.6% |
| puffed/extruded | FR | 389 | 25 | 28 | 29 | 29 | 84 | 7.5% |
| puffed/extruded | UK-IE | 121 | 33 | 43 | 47 | 49 | 51 | 38.8% |
| puffed/extruded | US-CA | 83 | 7 | 9 | 9 | 11 | 16 | 10.8% |
| tortilla/corn chips | FR | 586 | 28 | 34 | 190 | 313 | 423 | 32.4% |
| tortilla/corn chips | UK-IE | 183 | 13 | 17 | 34 | 79 | 152 | 18.6% |
| tortilla/corn chips | US-CA | 305 | 34 | 42 | 45 | 96 | 203 | 14.8% |

</details>

<details><summary>Saturated fat at 20–25 g total fat</summary>

| Form | Region | Valid pair | Median saturated fat | P90 | Share ≥25% N | Share ≥30% N | Share ≥35% N |
| --- | --- | --- | --- | --- | --- | --- | --- |
| potato crisps | FR | 212 | 2.20 | 3.48 | 17 | 17 | 15 |
| potato crisps | UK-IE | 97 | 2.10 | 2.84 | 0 | 0 | 0 |
| potato crisps | US-CA | 54 | 3.55 | 10.71 | 12 | 9 | 9 |
| puffed/extruded | FR | 55 | 2.50 | 2.80 | 3 | 2 | 2 |
| puffed/extruded | UK-IE | 4 | 2.10 | 2.37 | 0 | 0 | 0 |
| puffed/extruded | US-CA | 7 | 2.78 | 11.69 | 3 | 2 | 2 |
| tortilla/corn chips | FR | 378 | 2.10 | 9.00 | 42 | 42 | 41 |
| tortilla/corn chips | UK-IE | 126 | 2.10 | 2.75 | 2 | 2 | 2 |
| tortilla/corn chips | US-CA | 159 | 3.57 | 3.57 | 13 | 9 | 9 |

</details>

<details><summary>Fat distribution, counts by upper bin edge (g)</summary>

| Form | Region | 10 | 15 | 20 | 25 | 30 | 35 | 40 | above 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| potato crisps | FR | 33 | 32 | 35 | 209 | 662 | 1403 | 376 | 57 |
| potato crisps | UK-IE | 28 | 39 | 23 | 99 | 355 | 218 | 7 | 4 |
| potato crisps | US-CA | 24 | 10 | 19 | 55 | 114 | 139 | 94 | 2 |
| puffed/extruded | FR | 16 | 9 | 4 | 55 | 143 | 161 | 1 | 0 |
| puffed/extruded | UK-IE | 8 | 25 | 14 | 4 | 41 | 29 | 0 | 0 |
| puffed/extruded | US-CA | 2 | 5 | 2 | 7 | 16 | 50 | 0 | 1 |
| tortilla/corn chips | FR | 16 | 12 | 162 | 233 | 139 | 16 | 7 | 1 |
| tortilla/corn chips | UK-IE | 7 | 6 | 21 | 118 | 26 | 4 | 1 | 0 |
| tortilla/corn chips | US-CA | 28 | 6 | 11 | 158 | 69 | 8 | 25 | 0 |

</details>

<details><summary>Composition, low / other fat medians</summary>

| Form | Region | Restriction | ≤20 N | >20 N | fat | saturated_fat | salt | protein | fibre | energy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| potato crisps | FR | all | 100 | 2707 | 13.00 / 32.10 | 1.50 / 3.00 | 1.10 / 1.22 | 6.50 / 6.10 | 4.50 / 4.50 | 428.00 / 529.00 |
| potato crisps | FR | unspecified (construction) | 83 | 2476 | 13.00 / 32.10 | 1.56 / 3.00 | 1.00 / 1.25 | 6.67 / 6.10 | 4.30 / 4.50 | 424.00 / 529.00 |
| potato crisps | FR | cheese (flavour) | 6 | 116 | 11.50 / 31.00 | 1.20 / 2.90 | 1.30 / 1.37 | 8.15 / 6.30 | 6.70 / 4.40 | 362.00 / 522.00 |
| potato crisps | FR | plain/salt wording (flavour) | 11 | 366 | 15.00 / 34.00 | 1.40 / 2.90 | 0.94 / 1.10 | 5.90 / 6.00 | 3.80 / 4.50 | 429.00 / 533.50 |
| potato crisps | FR | unspecified (flavour) | 66 | 1811 | 13.00 / 32.80 | 1.65 / 3.00 | 1.00 / 1.20 | 6.10 / 6.10 | 4.00 / 4.50 | 419.00 / 531.00 |
| potato crisps | UK-IE | all | 90 | 683 | 13.00 / 29.00 | 1.36 / 2.60 | 0.94 / 1.21 | 5.90 / 6.30 | 4.11 / 4.10 | 429.41 / 512.00 |
| potato crisps | UK-IE | unspecified (construction) | 71 | 632 | 13.02 / 29.00 | 1.36 / 2.53 | 1.10 / 1.25 | 5.60 / 6.30 | 4.00 / 4.00 | 425.26 / 512.00 |
| potato crisps | UK-IE | cheese (flavour) | 14 | 86 | 13.54 / 29.00 | 1.30 / 2.70 | 1.00 / 1.21 | 5.91 / 6.60 | 5.10 / 4.13 | 436.36 / 513.00 |
| potato crisps | UK-IE | plain/salt wording (flavour) | 7 | 100 | 13.00 / 30.25 | 1.40 / 2.75 | 0.95 / 1.00 | 6.40 / 6.10 | 5.00 / 4.00 | 437.18 / 518.00 |
| potato crisps | UK-IE | unspecified (flavour) | 47 | 339 | 12.73 / 29.00 | 1.20 / 2.53 | 0.89 / 1.21 | 3.60 / 6.30 | 3.20 / 4.00 | 250.00 / 512.00 |
| potato crisps | US-CA | all | 53 | 404 | 11.00 / 32.14 | 1.50 / 3.57 | 0.67 / 1.43 | 3.00 / 7.14 | 2.00 / 3.57 | 464.29 / 535.71 |
| potato crisps | US-CA | kettle (construction) | 9 | 106 | 11.00 / 28.57 | 1.00 / 3.57 | 0.47 / 1.25 | 3.00 / 7.14 | 2.00 / 3.57 | 514.14 / 535.71 |
| potato crisps | US-CA | unspecified (construction) | 32 | 289 | 10.00 / 32.14 | 1.50 / 5.30 | 0.47 / 1.43 | 2.50 / 7.14 | 1.83 / 3.57 | 465.64 / 535.71 |
| potato crisps | US-CA | cheese (flavour) | 8 | 37 | 10.00 / 32.14 | 1.50 / 5.36 | 0.44 / 1.61 | 2.00 / 7.14 | 1.00 / 3.57 | 500.00 / 535.71 |
| potato crisps | US-CA | plain/salt wording (flavour) | 13 | 75 | 15.68 / 32.14 | 1.60 / 3.60 | 1.07 / 1.07 | 6.27 / 7.14 | 3.57 / 3.57 | 464.29 / 535.71 |
| potato crisps | US-CA | unspecified (flavour) | 23 | 229 | 10.00 / 31.80 | 1.15 / 3.57 | 0.50 / 1.43 | 2.00 / 7.14 | 1.36 / 3.57 | 464.29 / 535.71 |
| puffed/extruded | FR | all | 29 | 360 | 9.00 / 30.00 | 1.00 / 3.10 | 1.20 / 1.40 | 7.83 / 4.50 | 4.30 / 3.45 | 400.00 / 509.50 |
| puffed/extruded | FR | unspecified (flavour) | 20 | 213 | 9.00 / 30.00 | 1.10 / 3.00 | 1.00 / 1.40 | 8.50 / 4.40 | 4.25 / 3.50 | 400.00 / 509.00 |
| puffed/extruded | UK-IE | all | 47 | 74 | 14.00 / 30.00 | 1.30 / 2.90 | 1.10 / 1.48 | 6.60 / 5.19 | 4.50 / 3.30 | 434.78 / 520.00 |
| puffed/extruded | UK-IE | unspecified (construction) | 17 | 9 | 17.00 / 30.40 | 1.36 / 3.70 | 1.40 / 1.51 | 6.20 / 5.20 | 4.00 / 2.00 | 448.00 / 532.00 |
| puffed/extruded | UK-IE | unspecified (flavour) | 26 | 39 | 13.55 / 30.00 | 1.30 / 2.90 | 1.04 / 1.50 | 6.70 / 5.00 | 4.50 / 3.20 | 431.00 / 518.52 |
| puffed/extruded | US-CA | all | 9 | 74 | 13.00 / 32.14 | 0.56 / 8.93 | 1.76 / 1.52 | 5.56 / 3.57 | 3.57 / 3.57 | 434.78 / 535.71 |
| puffed/extruded | US-CA | unspecified (flavour) | 5 | 37 | 11.76 / 32.14 | 0.00 / 8.93 | 1.76 / 1.61 | 5.88 / 3.57 | 3.57 / 3.57 | 411.76 / 535.71 |
| tortilla/corn chips | FR | all | 190 | 396 | 20.00 / 24.95 | 2.00 / 2.50 | 1.10 / 1.10 | 6.60 / 6.60 | 4.00 / 4.80 | 472.00 / 493.00 |
| tortilla/corn chips | FR | unspecified (construction) | 190 | 394 | 20.00 / 24.80 | 2.00 / 2.50 | 1.10 / 1.10 | 6.60 / 6.60 | 4.00 / 4.80 | 472.00 / 493.00 |
| tortilla/corn chips | FR | cheese (flavour) | 24 | 67 | 20.00 / 26.00 | 2.00 / 2.60 | 1.60 / 1.30 | 6.60 / 6.50 | 4.00 / 4.35 | 472.00 / 499.00 |
| tortilla/corn chips | FR | plain/salt wording (flavour) | 29 | 38 | 20.00 / 23.60 | 2.00 / 2.20 | 0.90 / 0.80 | 6.60 / 6.70 | 4.00 / 3.95 | 472.00 / 492.00 |
| tortilla/corn chips | FR | unspecified (flavour) | 93 | 212 | 20.00 / 24.70 | 2.00 / 2.60 | 0.90 / 0.94 | 6.60 / 6.60 | 4.00 / 5.20 | 472.00 / 492.00 |
| tortilla/corn chips | FR | corn (base_wording) | 182 | 381 | 20.00 / 24.90 | 2.00 / 2.50 | 1.10 / 1.10 | 6.60 / 6.60 | 4.00 / 4.80 | 472.00 / 492.75 |
| tortilla/corn chips | UK-IE | all | 34 | 149 | 18.33 / 23.00 | 1.90 / 2.20 | 0.98 / 1.00 | 6.84 / 6.20 | 5.50 / 5.50 | 469.00 / 488.00 |
| tortilla/corn chips | UK-IE | unspecified (construction) | 33 | 148 | 18.80 / 23.00 | 1.95 / 2.20 | 0.98 / 1.00 | 6.90 / 6.20 | 5.70 / 5.55 | 469.00 / 487.50 |
| tortilla/corn chips | UK-IE | unspecified (flavour) | 26 | 90 | 17.60 / 23.05 | 1.80 / 2.20 | 1.00 / 0.89 | 6.74 / 6.20 | 5.70 / 5.25 | 469.00 / 489.50 |
| tortilla/corn chips | UK-IE | corn (base_wording) | 32 | 138 | 18.95 / 23.00 | 1.95 / 2.29 | 0.98 / 1.00 | 6.74 / 6.10 | 5.28 / 5.60 | 469.00 / 489.00 |
| tortilla/corn chips | US-CA | all | 45 | 260 | 9.00 / 25.00 | 1.00 / 3.57 | 0.42 / 1.16 | 4.17 / 7.14 | 2.00 / 4.10 | 464.29 / 500.00 |
| tortilla/corn chips | US-CA | unspecified (construction) | 45 | 259 | 9.00 / 25.00 | 1.00 / 3.57 | 0.42 / 1.16 | 4.17 / 7.14 | 2.00 / 4.07 | 464.29 / 500.00 |
| tortilla/corn chips | US-CA | cheese (flavour) | 3 | 29 | 7.80 / 28.00 | 0.90 / 3.57 | 0.26 / 1.52 | 1.90 / 7.14 | 1.00 / 3.57 | 160.00 / 520.00 |
| tortilla/corn chips | US-CA | plain/salt wording (flavour) | 5 | 34 | 8.24 / 25.00 | 1.00 / 3.57 | 0.38 / 0.94 | 2.00 / 7.14 | 1.18 / 3.60 | 392.86 / 500.00 |
| tortilla/corn chips | US-CA | unspecified (flavour) | 34 | 183 | 9.50 / 25.00 | 1.00 / 3.57 | 0.46 / 1.07 | 5.50 / 7.14 | 2.05 / 6.00 | 464.29 / 500.00 |
| tortilla/corn chips | US-CA | corn (base_wording) | 45 | 236 | 9.00 / 25.00 | 1.00 / 3.57 | 0.42 / 1.18 | 4.17 / 7.14 | 2.00 / 4.02 | 464.29 / 500.00 |

</details>

<details><summary>Difference within comparable wording strata</summary>

| Form | Region | Nutrient | Supported strata | Lower-fat products represented | Lower minus other |
| --- | --- | --- | --- | --- | --- |
| potato crisps | FR | energy | 7 | 74 | -125.13 |
| potato crisps | FR | protein | 7 | 82 | 0.66 |
| potato crisps | FR | salt | 7 | 79 | -0.16 |
| potato crisps | FR | saturated_fat | 7 | 81 | -1.32 |
| potato crisps | FR | fibre | 4 | 51 | -0.18 |
| potato crisps | UK-IE | energy | 7 | 68 | -189.30 |
| potato crisps | UK-IE | protein | 7 | 73 | -1.80 |
| potato crisps | UK-IE | salt | 7 | 70 | -0.13 |
| potato crisps | UK-IE | saturated_fat | 7 | 73 | -1.33 |
| potato crisps | UK-IE | fibre | 7 | 66 | -0.29 |
| potato crisps | US-CA | energy | 4 | 32 | -62.21 |
| potato crisps | US-CA | protein | 4 | 32 | -4.45 |
| potato crisps | US-CA | salt | 4 | 30 | -0.82 |
| potato crisps | US-CA | saturated_fat | 4 | 31 | -3.26 |
| potato crisps | US-CA | fibre | 3 | 26 | -1.82 |
| puffed/extruded | FR | energy | 1 | 3 | -360.00 |
| puffed/extruded | FR | protein | 1 | 3 | -3.40 |
| puffed/extruded | FR | salt | 1 | 3 | -0.82 |
| puffed/extruded | FR | saturated_fat | 1 | 3 | -0.50 |
| puffed/extruded | FR | fibre | 0 | 0 | — |
| puffed/extruded | UK-IE | energy | 0 | 0 | — |
| puffed/extruded | UK-IE | protein | 0 | 0 | — |
| puffed/extruded | UK-IE | salt | 0 | 0 | — |
| puffed/extruded | UK-IE | saturated_fat | 0 | 0 | — |
| puffed/extruded | UK-IE | fibre | 0 | 0 | — |
| puffed/extruded | US-CA | energy | 0 | 0 | — |
| puffed/extruded | US-CA | protein | 0 | 0 | — |
| puffed/extruded | US-CA | salt | 0 | 0 | — |
| puffed/extruded | US-CA | saturated_fat | 0 | 0 | — |
| puffed/extruded | US-CA | fibre | 0 | 0 | — |
| tortilla/corn chips | FR | energy | 5 | 185 | -19.62 |
| tortilla/corn chips | FR | protein | 5 | 189 | -0.03 |
| tortilla/corn chips | FR | salt | 5 | 188 | 0.08 |
| tortilla/corn chips | FR | saturated_fat | 5 | 189 | -0.36 |
| tortilla/corn chips | FR | fibre | 4 | 127 | -0.78 |
| tortilla/corn chips | UK-IE | energy | 1 | 23 | -21.00 |
| tortilla/corn chips | UK-IE | protein | 1 | 25 | 0.59 |
| tortilla/corn chips | UK-IE | salt | 1 | 22 | 0.07 |
| tortilla/corn chips | UK-IE | saturated_fat | 1 | 24 | -0.35 |
| tortilla/corn chips | UK-IE | fibre | 1 | 22 | 0.45 |
| tortilla/corn chips | US-CA | energy | 4 | 44 | -68.21 |
| tortilla/corn chips | US-CA | protein | 4 | 45 | -2.19 |
| tortilla/corn chips | US-CA | salt | 4 | 45 | -0.60 |
| tortilla/corn chips | US-CA | saturated_fat | 4 | 45 | -2.04 |
| tortilla/corn chips | US-CA | fibre | 3 | 38 | -3.64 |

</details>

<details><summary>Commercial and regional sensitivities</summary>

| Form | Region | Restriction | Valid fat | Fat ≤20 | Valid protein | Protein ≥10 |
| --- | --- | --- | --- | --- | --- | --- |
| potato crisps | FR | explicit form in name | 283 | 17 | 282 | 1 |
| potato crisps | FR | GTIN absent in UK-IE | 2701 | 93 | 2701 | 14 |
| potato crisps | FR | construction unspecified | 2559 | 83 | 2559 | 14 |
| potato crisps | UK-IE | explicit form in name | 143 | 12 | 142 | 0 |
| potato crisps | UK-IE | GTIN absent in FR | 667 | 83 | 665 | 10 |
| potato crisps | UK-IE | construction unspecified | 703 | 71 | 701 | 11 |
| potato crisps | US-CA | explicit form in name | 309 | 27 | 308 | 7 |
| potato crisps | US-CA | GTIN absent in FR | 415 | 51 | 413 | 15 |
| potato crisps | US-CA | construction unspecified | 321 | 32 | 319 | 12 |
| puffed/extruded | FR | explicit form in name | 21 | 19 | 21 | 6 |
| puffed/extruded | FR | GTIN absent in UK-IE | 370 | 27 | 375 | 7 |
| puffed/extruded | FR | construction unspecified | 12 | 10 | 12 | 5 |
| puffed/extruded | FR | base: corn | 4 | 2 | 4 | 1 |
| puffed/extruded | FR | base: corn+potato | 8 | 1 | 8 | 0 |
| puffed/extruded | FR | base: potato | 358 | 13 | 363 | 0 |
| puffed/extruded | FR | base: pulse | 3 | 3 | 3 | 3 |
| puffed/extruded | FR | base: rice | 2 | 2 | 2 | 0 |
| puffed/extruded | FR | base: rice+potato | 6 | 0 | 6 | 0 |
| puffed/extruded | FR | base: unspecified | 8 | 8 | 8 | 3 |
| puffed/extruded | UK-IE | explicit form in name | 55 | 45 | 55 | 16 |
| puffed/extruded | UK-IE | GTIN absent in FR | 102 | 45 | 102 | 17 |
| puffed/extruded | UK-IE | construction unspecified | 26 | 17 | 26 | 10 |
| puffed/extruded | UK-IE | base: corn | 4 | 3 | 4 | 0 |
| puffed/extruded | UK-IE | base: corn+potato | 3 | 1 | 3 | 0 |
| puffed/extruded | UK-IE | base: potato | 83 | 19 | 83 | 0 |
| puffed/extruded | UK-IE | base: pulse | 10 | 8 | 10 | 9 |
| puffed/extruded | UK-IE | base: pulse+potato | 1 | 1 | 1 | 1 |
| puffed/extruded | UK-IE | base: rice+potato | 1 | 0 | 1 | 0 |
| puffed/extruded | UK-IE | base: unspecified | 19 | 15 | 19 | 7 |
| puffed/extruded | US-CA | explicit form in name | 13 | 6 | 13 | 3 |
| puffed/extruded | US-CA | GTIN absent in FR | 64 | 6 | 64 | 2 |
| puffed/extruded | US-CA | construction unspecified | 7 | 2 | 7 | 1 |
| puffed/extruded | US-CA | base: corn | 5 | 3 | 5 | 0 |
| puffed/extruded | US-CA | base: corn+potato | 1 | 0 | 1 | 0 |
| puffed/extruded | US-CA | base: corn+rice | 1 | 0 | 1 | 0 |
| puffed/extruded | US-CA | base: potato | 70 | 4 | 70 | 0 |
| puffed/extruded | US-CA | base: pulse | 1 | 0 | 1 | 1 |
| puffed/extruded | US-CA | base: pulse+corn+potato | 1 | 0 | 1 | 0 |
| puffed/extruded | US-CA | base: rice | 1 | 1 | 1 | 0 |
| puffed/extruded | US-CA | base: unspecified | 3 | 1 | 3 | 2 |
| tortilla/corn chips | FR | explicit form in name | 319 | 123 | 319 | 3 |
| tortilla/corn chips | FR | GTIN absent in UK-IE | 554 | 187 | 554 | 11 |
| tortilla/corn chips | FR | construction unspecified | 584 | 190 | 584 | 12 |
| tortilla/corn chips | UK-IE | explicit form in name | 80 | 13 | 80 | 0 |
| tortilla/corn chips | UK-IE | GTIN absent in FR | 151 | 31 | 151 | 4 |
| tortilla/corn chips | UK-IE | construction unspecified | 181 | 33 | 181 | 5 |
| tortilla/corn chips | US-CA | explicit form in name | 164 | 17 | 164 | 1 |
| tortilla/corn chips | US-CA | GTIN absent in FR | 270 | 42 | 270 | 6 |
| tortilla/corn chips | US-CA | construction unspecified | 304 | 45 | 304 | 6 |

</details>

<details><summary>Potato crisp examples</summary>

| Region | Example | GTIN | Name | Construction | Fat | Energy | Protein | Salt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FR | typical | 3168930002970 | Cuites au four | baked+stacked | 13.00 | 439.00 | 5.80 | 1.20 |
| FR | near inside | 0020685084423 | Croustilles cuites en marmite - Sel de mer | unspecified | 20.00 | 460.00 | 8.00 | 1.10 |
| FR | near outside | 00762724 | Salt & vinegar chiplets | unspecified | 20.80 | 463.00 | 6.30 | 2.80 |
| UK-IE | typical | 5000237139394 | sour cream & onion flavour potato snacks | unspecified | 13.00 | 423.53 | 6.70 | 1.10 |
| UK-IE | near inside | 00066549 | Sweet & Smoky BBQ | unspecified | 19.67 | 463.33 | 7.33 | 1.08 |
| UK-IE | near outside | 5000169610862 | Sea Salt, Chilli & Lime Mix | unspecified | 20.10 | 465.00 | 3.80 | 2.13 |

</details>
