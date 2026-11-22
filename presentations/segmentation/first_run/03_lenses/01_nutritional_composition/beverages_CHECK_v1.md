# Beverages · format-first formulation CHECK

**Scope decision from Julia.** The soda and energy-drink very-low-sugar profiles and commercial plant-base distinctions are approved. Alcohol is excluded from nutritional segmentation; its source records and existing Streamlit view are retained. The alcohol distributions below are descriptive historical output from the initial follow-up. Preparations remain a separate population, with numerical comparison deferred where basis is unverified. The researched formulation chapter closed on 16 November; the bounded juice-classification correction was completed on 19 November. [Correction CHECK](juice_classification_CHECK_v1.md).

**Decision. Retain a descriptive very-low-sugars formulation within soda and energy drinks. Plant base supplies the strongest commercial distinction in plant drinks. Other observable liquid formats show nutritional variation or insufficient replication. Preparation nutrition is deferred until the recorded basis can establish a like-for-like comparison.**

## The reporting split and analytical basis

Streamlit labels its two main views **ready-to-drink beverages** and **beverage preparations and alcohol**. The corrected Wave 2 assignments total 59,983, 45,785 and 11,828 respectively for those views and the unresolved view. Alcohol is therefore in the second reporting view even when the product is a finished liquid. The original view is preserved beside each analytical format. Liquid alcohol formats receive their own descriptive comparisons using the existing liquid convention. A view label alone cannot establish physical form or a nutrition basis. [Streamlit definition](../../../../../shared/beverage_segments.py)

The starting population is all **117,596 governed beverage assignments**. Commercial refinement uses the existing subtype, names and tags, independently of nutrition or claim fields. Specific liquid forms use the baseline per-100-ml convention. The master does not independently verify pack-level g/ml or as-sold/prepared declarations. Syrups, concentrates, dry mixtures, coffee, tea and unverified forms retain their existing basis flags. Nutrient availability for these products is shown in the evidence tables, while numerical comparisons require a comparable liquid basis.

## Decision per commercial format

| Form | Decision and reason |
|---|---|
| **Soda** | Retain a very-low-sugars profile, defined as **≤0.5 g observed total sugars/100 ml**. Among jointly measured products, 710/3,457 FR and 255/640 UK/IE qualify. Median energy is 0.6 and 1.0 kcal. In the same format's ≥5 g sugar group, energy medians are 38.0 and 39.2 kcal. The profile persists after restricting to the Streamlit RTD view and removing GTINs shared between primary regions. |
| **Energy drinks** | Retain the same product-level nutritional rule within the explicitly identified energy-drink format. The jointly measured populations include 151/684 FR and 87/241 UK/IE at ≤0.5 g sugars, with energy medians of 3 versus 46 kcal in the ≥5 g groups. The distinction recurs in the selected US/CA measurements. Commercial energy-drink identification is separate from the locked communicated energy-positioning field. |
| **Sports/electrolyte liquids** | Keep a separate commercial format. Only eight UK/Irish sugar measurements were available in the initial screen. Evidence is insufficient for a replicated formulation subdivision. Recorded salt cannot substitute for electrolyte or hydration evidence. |
| **Iced tea** | Retain sugar variation and a French very-low-sugar tail as exploratory. France has 69 valid-sugar observations at ≤0.5 g versus only two in UK/IE; only 25 UK/Irish sugar values are available in total. |
| **Iced coffee** | Retain the format and measured composition. France has only 11 valid sugar measurements. Milk content and other construction differences could explain the protein and energy variation; a recurring within-format profile is unsupported. |
| **Juice** | Retain composition-based commercial types and observed variation. The population and distributions below use the corrected 19 November name/tag rule; no additional nutritional profile is proposed. |
| **Nectar** | Retain the independently supported commercial form. Conflicting juice names and nectar tags remain unresolved; no further nutritional subdivision is proposed. |
| **Smoothie** | Retain independently supported smoothies and observed nutritional variation. Nested juice-family tags do not create a second product or a new nutritional profile. |
| **Fruit drinks** | Use explicit fruit-drink evidence, not the broad parent tag ‘boissons aux fruits’. Rebuilt distributions replace the earlier mixture of juices and fruit drinks; the earlier France–UK contrast is withdrawn. |
| **Flavoured water** | Retain flavouring as a commercial distinction and show sugar variation. A ≤0.5 g band is common, but a higher-sugar arm of ≥20 jointly measured products was unavailable in UK/IE (10 products). A second descriptive profile adds limited supported information. |
| **Water, flavour unspecified** | Retain the unresolved flavour descriptor. Many observations are zero, but others contain substantial recorded sugars. Generic water wording does not establish plain water. Keep these records and avoid naming a new nutritional segment from this mixture. |
| **Coconut water** | Retain a distinct commercial form. Median sugars are 3.65 g FR and 4.0 g UK/IE. No further nutritional profile is established. |
| **Soy drinks** | Retain soy as the base and describe sugars within it. Median protein is 3.3 g FR and 3.2 g UK/IE, versus 0.7 and 0.6 g in almond drinks. This is evidence for the commercial base distinction. UK/IE has only 12 observations in the ≥5 g sugars arm, limiting subdivision. |
| **Almond drinks** | Retain almond as the base, with observed sugar variation. Only three UK/Irish products have ≥5 g sugars. |
| **Oat, rice and coconut plant drinks** | Keep the identifiable bases. Primary-region samples are too small for another formulation split. |
| **Mixed or unresolved plant base** | Retain the broader plant-drink population and unresolved base. Sparse captured oat and rice populations also reflect the limitations of the inherited subtype screen. |
| **Fermented soft drinks** | Retain the format and show its sugar continuum. France has 37 ≥5 g observations but UK/IE has one. A replicated two-profile interpretation is unsupported. |
| **Beer, cider, wine, spirits/liqueurs, and cocktail/alcohol-style drinks** | Keep separate commercial forms. Record the measured per-liquid distributions descriptively. The selected master lacks a usable alcohol concentration field, so differences in energy cannot establish otherwise comparable formulations. In particular, protein/fibre per calorie offers little interpretable structure here. Conflicting alcohol-form cues remain unresolved. |
| **Syrups/concentrates** | Retain the preparation form. No within-form nutritional profile is supported until as-sold versus diluted measurement basis is established. |
| **Chocolate preparations** | Retain the preparation form and availability counts. Different dilution and milk/water preparation instructions make the present numeric basis insufficient. |
| **Coffee preparations** | Retain separately from iced coffee. Ground coffee, soluble coffee and mixtures can carry nutrition for materially different preparation states; the master cannot resolve that basis. |
| **Tea/infusion preparations** | Retain separately from iced tea. Leaf versus brewed values cannot be treated as comparable under the recorded fields alone. |
| **Sports powder/tablet preparations** | Retain the preparation form, separate from finished sports drinks. Numeric assessment requires a verified dilution and reporting basis. |
| **Other preparations, conflicting or unresolved forms** | Keep all assignments with their explicit unresolved status. No subtype is inferred from nutrients. |

## What the retained profile means

**Individual-value caution.** Among very-low-sugar records with valid energy, energy exceeded 20 kcal/100 ml in 23/710 French and 1/255 UK/Irish sodas, and 9/151 French and 2/87 UK/Irish energy drinks. US/Canadian counts were 3/95 and 6/97. These can reflect other energy sources or questionable source observations. A French boundary example, *Boisson speedstar energy drink*, records 0.5 g sugars with 333 kcal/100 ml. Preserve these observations and show their measured energy. The retained profile is defined by sugars, with a low-energy association at group level. The numerical baseline gate alone cannot validate a pack-level measurement.

The ≤0.5 g definition is an exploratory nutritional convention chosen for this follow-up. The comparison arm ≥5 g exposes a substantial compositional contrast; intermediate products remain visible. These labels describe measurements, and their thresholds differ from the prior food cutoffs. For soda, tightening to ≤0.1 g retained 597 French and 200 UK/Irish jointly measured products; widening to ≤1 g gave 728 and 265. Many records are measured zero. The near-zero end is recurrent, while the exact boundary is conventional and some products lie between the low and higher-sugar bands.

Sugar contributes energy, so their association is partly mathematical. Protein and fat medians in the soda and energy-drink arms are close to zero, making this a recognizable sugar/energy formulation distinction within a commercial format. The measurements cannot establish a recipe substitution, sweetener use, regulatory claim eligibility or an assessed pack claim. Energy ratios with zero denominators are undefined. Plant protein should first be interpreted in grams per 100 ml within its named base.

Examples include French *Fiz Citron Vert* at 0.50 g sugars and 4 kcal/100 ml, UK/Irish *Bitter lemon* at 0.50 g and 12 kcal, and a UK/Irish orange soft drink just outside at 0.52 g and 2.12 kcal. The latter illustrates that the sugar boundary does not identify a natural energy discontinuity. Examples and text GTINs are in the final evidence table.

## Audit and reproducibility

The [builder](beverages_v1.py) imports the shared master reader, which verifies the corrected Wave 2 digest and all prior nutrient-valid counts. It reconciles the original 117,596 beverage assignment keys and reads the existing Streamlit view and analytical basis from the baseline. It uses juice_classification_v1.py to distinguish specific identities from broad parent tags, retain conflicting evidence as unresolved, and preserve original analytical labels. Meal-replacement name cues remain basis-unresolved. Known sports cues prevent silently treating them as a confirmed energy-drink form. Classifications are derived interpretations of the available names and tags.

The [product-level assignments](beverage_assignments_v1.parquet) preserve text GTIN, region, canonical category, inherited membership, subtype, confidence, Streamlit view and basis. The new fields give the analytical format, comparison eligibility, sugar band and a nullable retained profile for soda/energy drinks. Missing sugars produce an unknown profile. Unknown or inapplicable forms retain null labels. Availability tables show each nutrient independently. Energy comparisons use jointly observed energy and sugars, including recorded zero. US/Canada remains exploratory because the measurable products are strongly selected.

Preparation comparability and alcohol concentration are limitations of this follow-up. The numerical liquid convention is inherited from the completed baseline. It has no independent pack-level basis verification. Claims, functional benefits and NOVA remain separately governed overlays.

<!-- evidence -->

<details><summary>Streamlit split, retained exactly</summary>

| View | Region | Assignments |
| --- | --- | --- |
| beverage_preparations_and_alcohol | FR | 31878 |
| beverage_preparations_and_alcohol | UK-IE | 2143 |
| beverage_preparations_and_alcohol | US-CA | 11764 |
| ready_to_drink_beverages | FR | 30446 |
| ready_to_drink_beverages | UK-IE | 3200 |
| ready_to_drink_beverages | US-CA | 26337 |
| unknown_beverage_segment | FR | 4335 |
| unknown_beverage_segment | UK-IE | 1019 |
| unknown_beverage_segment | US-CA | 6474 |

</details>

<details><summary>Format coverage and individual nutrient availability</summary>

| Form | Region | Assignments | Energy N | Sugars N | Protein N | Fat N | Salt N |
| --- | --- | --- | --- | --- | --- | --- | --- |
| alcohol: beer | FR | 4986 | 1284 | 1281 | 1105 | 1092 | 1183 |
| alcohol: beer | UK-IE | 523 | 205 | 170 | 150 | 150 | 134 |
| alcohol: beer | US-CA | 454 | 32 | 26 | 28 | 24 | 17 |
| alcohol: cider | FR | 871 | 188 | 214 | 175 | 175 | 217 |
| alcohol: cider | UK-IE | 102 | 36 | 31 | 24 | 24 | 22 |
| alcohol: cider | US-CA | 331 | 4 | 4 | 4 | 4 | 4 |
| alcohol: cocktail/alcohol-style | FR | 33 | 12 | 13 | 13 | 13 | 14 |
| alcohol: cocktail/alcohol-style | UK-IE | 5 | 3 | 3 | 3 | 3 | 3 |
| alcohol: cocktail/alcohol-style | US-CA | 128 | 3 | 3 | 3 | 3 | 3 |
| alcohol: spirits/liqueurs | FR | 1083 | 158 | 212 | 189 | 189 | 217 |
| alcohol: spirits/liqueurs | UK-IE | 120 | 34 | 32 | 28 | 30 | 28 |
| alcohol: spirits/liqueurs | US-CA | 252 | 10 | 13 | 8 | 7 | 7 |
| alcohol: unresolved/conflicting | FR | 1010 | 199 | 195 | 173 | 173 | 212 |
| alcohol: unresolved/conflicting | UK-IE | 83 | 38 | 39 | 29 | 28 | 27 |
| alcohol: unresolved/conflicting | US-CA | 887 | 26 | 26 | 25 | 23 | 21 |
| alcohol: wine | FR | 7985 | 898 | 1155 | 807 | 812 | 1168 |
| alcohol: wine | UK-IE | 419 | 87 | 105 | 69 | 70 | 66 |
| alcohol: wine | US-CA | 356 | 4 | 7 | 3 | 2 | 3 |
| basis/form unresolved | FR | 14730 | 11851 | 11810 | 11814 | 11802 | 11373 |
| basis/form unresolved | UK-IE | 1190 | 937 | 912 | 923 | 926 | 823 |
| basis/form unresolved | US-CA | 13822 | 771 | 741 | 768 | 767 | 731 |
| chocolate preparation | FR | 752 | 677 | 686 | 692 | 691 | 675 |
| chocolate preparation | UK-IE | 51 | 49 | 50 | 50 | 50 | 50 |
| chocolate preparation | US-CA | 685 | 48 | 46 | 48 | 48 | 47 |
| coconut water | FR | 218 | 207 | 206 | 207 | 207 | 201 |
| coconut water | UK-IE | 32 | 30 | 30 | 30 | 30 | 29 |
| coconut water | US-CA | 570 | 76 | 75 | 76 | 76 | 76 |
| coffee preparation | FR | 1617 | 920 | 719 | 932 | 932 | 907 |
| coffee preparation | UK-IE | 101 | 53 | 44 | 53 | 53 | 52 |
| coffee preparation | US-CA | 221 | 24 | 20 | 25 | 25 | 25 |
| energy drink | FR | 740 | 700 | 691 | 694 | 691 | 665 |
| energy drink | UK-IE | 278 | 259 | 243 | 249 | 249 | 226 |
| energy drink | US-CA | 629 | 175 | 145 | 169 | 169 | 168 |
| energy/sports unresolved | FR | 29 | 27 | 27 | 26 | 26 | 25 |
| energy/sports unresolved | US-CA | 11 | 8 | 8 | 8 | 8 | 8 |
| fermented soft drink | FR | 688 | 649 | 644 | 639 | 639 | 580 |
| fermented soft drink | UK-IE | 158 | 150 | 148 | 146 | 147 | 120 |
| fermented soft drink | US-CA | 926 | 50 | 50 | 50 | 50 | 45 |
| flavoured water | FR | 388 | 347 | 335 | 345 | 344 | 330 |
| flavoured water | UK-IE | 250 | 183 | 181 | 179 | 179 | 162 |
| flavoured water | US-CA | 1939 | 79 | 66 | 79 | 79 | 71 |
| fruit drink | FR | 102 | 99 | 99 | 99 | 99 | 94 |
| fruit drink | UK-IE | 40 | 38 | 38 | 38 | 38 | 36 |
| fruit drink | US-CA | 805 | 31 | 31 | 31 | 31 | 31 |
| iced coffee | FR | 14 | 11 | 11 | 12 | 12 | 10 |
| iced coffee | UK-IE | 25 | 25 | 25 | 25 | 25 | 25 |
| iced coffee | US-CA | 583 | 27 | 26 | 27 | 27 | 26 |
| iced tea | FR | 704 | 660 | 660 | 659 | 657 | 623 |
| iced tea | UK-IE | 26 | 25 | 25 | 25 | 25 | 24 |
| iced tea | US-CA | 1114 | 54 | 54 | 52 | 52 | 47 |
| juice | FR | 8558 | 7599 | 7550 | 7587 | 7564 | 7093 |
| juice | UK-IE | 798 | 745 | 746 | 743 | 744 | 648 |
| juice | US-CA | 4505 | 322 | 318 | 322 | 321 | 301 |
| juice family unresolved | FR | 452 | 428 | 426 | 430 | 431 | 408 |
| juice family unresolved | UK-IE | 92 | 86 | 84 | 85 | 85 | 73 |
| juice family unresolved | US-CA | 357 | 44 | 44 | 44 | 43 | 41 |
| nectar | FR | 1930 | 1770 | 1765 | 1765 | 1763 | 1641 |
| nectar | UK-IE | 14 | 13 | 12 | 13 | 13 | 11 |
| nectar | US-CA | 252 | 36 | 36 | 36 | 36 | 29 |
| other preparation | FR | 2236 | 1249 | 1047 | 1251 | 1250 | 1200 |
| other preparation | UK-IE | 42 | 29 | 26 | 27 | 27 | 23 |
| other preparation | US-CA | 1632 | 107 | 99 | 104 | 105 | 105 |
| plant drink: almond | FR | 307 | 297 | 294 | 298 | 298 | 292 |
| plant drink: almond | UK-IE | 56 | 53 | 52 | 54 | 54 | 50 |
| plant drink: almond | US-CA | 413 | 63 | 60 | 63 | 63 | 62 |
| plant drink: coconut | FR | 31 | 29 | 29 | 29 | 29 | 27 |
| plant drink: coconut | UK-IE | 13 | 13 | 13 | 13 | 13 | 11 |
| plant drink: coconut | US-CA | 38 | 11 | 10 | 11 | 11 | 11 |
| plant drink: mixed/unresolved | FR | 67 | 67 | 67 | 67 | 67 | 64 |
| plant drink: mixed/unresolved | UK-IE | 41 | 37 | 37 | 36 | 37 | 34 |
| plant drink: mixed/unresolved | US-CA | 439 | 27 | 25 | 27 | 27 | 27 |
| plant drink: oat | FR | 10 | 10 | 10 | 10 | 10 | 9 |
| plant drink: oat | UK-IE | 5 | 5 | 3 | 5 | 5 | 4 |
| plant drink: oat | US-CA | 31 | 5 | 4 | 5 | 5 | 4 |
| plant drink: rice | FR | 9 | 7 | 7 | 7 | 7 | 7 |
| plant drink: rice | UK-IE | 1 | 1 | 1 | 1 | 1 | 1 |
| plant drink: rice | US-CA | 19 | 0 | 0 | 0 | 0 | 0 |
| plant drink: soy | FR | 282 | 253 | 255 | 255 | 253 | 249 |
| plant drink: soy | UK-IE | 80 | 79 | 78 | 79 | 79 | 75 |
| plant drink: soy | US-CA | 112 | 20 | 20 | 20 | 20 | 16 |
| scope unresolved | FR | 2296 | 1339 | 1354 | 1306 | 1305 | 1272 |
| scope unresolved | UK-IE | 186 | 104 | 97 | 91 | 89 | 84 |
| scope unresolved | US-CA | 192 | 55 | 52 | 54 | 55 | 50 |
| smoothie | FR | 544 | 517 | 521 | 519 | 520 | 467 |
| smoothie | UK-IE | 171 | 161 | 160 | 160 | 162 | 143 |
| smoothie | US-CA | 586 | 57 | 57 | 57 | 57 | 56 |
| soda | FR | 3837 | 3515 | 3473 | 3494 | 3490 | 3271 |
| soda | UK-IE | 728 | 669 | 643 | 645 | 649 | 571 |
| soda | US-CA | 6406 | 449 | 420 | 447 | 447 | 420 |
| sports powder/tablet preparation | FR | 11 | 9 | 10 | 10 | 10 | 10 |
| sports powder/tablet preparation | US-CA | 93 | 17 | 17 | 17 | 17 | 17 |
| sports/electrolyte drink | FR | 36 | 34 | 32 | 34 | 33 | 33 |
| sports/electrolyte drink | UK-IE | 9 | 8 | 8 | 8 | 8 | 8 |
| sports/electrolyte drink | US-CA | 255 | 40 | 35 | 40 | 40 | 40 |
| syrup/concentrate | FR | 3439 | 2887 | 2925 | 2873 | 2870 | 2646 |
| syrup/concentrate | UK-IE | 134 | 120 | 117 | 117 | 119 | 100 |
| syrup/concentrate | US-CA | 288 | 26 | 26 | 25 | 26 | 23 |
| tea/coffee RTD unresolved | FR | 9 | 9 | 9 | 9 | 9 | 9 |
| tea/coffee RTD unresolved | UK-IE | 2 | 2 | 2 | 2 | 2 | 1 |
| tea/coffee RTD unresolved | US-CA | 10 | 2 | 2 | 2 | 2 | 2 |
| tea/infusion preparation | FR | 4027 | 2366 | 2311 | 2340 | 2340 | 2173 |
| tea/infusion preparation | UK-IE | 305 | 174 | 165 | 166 | 168 | 159 |
| tea/infusion preparation | US-CA | 2004 | 83 | 78 | 82 | 81 | 74 |
| water: unspecified flavour | FR | 2628 | 1870 | 1853 | 1851 | 1847 | 1869 |
| water: unspecified flavour | UK-IE | 282 | 219 | 207 | 211 | 212 | 183 |
| water: unspecified flavour | US-CA | 3230 | 239 | 226 | 236 | 236 | 230 |

</details>

<details><summary>Comparable liquids, existing-valid values</summary>

| Form | Region | Metric | N | P10 | Q1 | Median | Q3 | P90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| alcohol: beer | FR | energy | 1284 | 18.79 | 27.00 | 40.50 | 54.00 | 74.00 |
| alcohol: beer | FR | sugars | 1281 | 0.00 | 0.00 | 0.50 | 3.10 | 5.70 |
| alcohol: beer | FR | protein | 1105 | 0.00 | 0.00 | 0.40 | 0.50 | 0.60 |
| alcohol: beer | FR | fat | 1092 | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 |
| alcohol: beer | FR | salt | 1183 | 0.00 | 0.00 | 0.01 | 0.01 | 0.10 |
| alcohol: beer | UK-IE | energy | 205 | 15.95 | 23.00 | 35.00 | 41.00 | 55.40 |
| alcohol: beer | UK-IE | sugars | 170 | 0.00 | 0.00 | 0.30 | 1.80 | 3.90 |
| alcohol: beer | UK-IE | protein | 150 | 0.00 | 0.10 | 0.30 | 0.40 | 0.60 |
| alcohol: beer | UK-IE | fat | 150 | 0.00 | 0.00 | 0.00 | 0.10 | 0.20 |
| alcohol: beer | UK-IE | salt | 134 | 0.00 | 0.00 | 0.01 | 0.01 | 0.10 |
| alcohol: beer | US-CA | energy | 32 | 17.70 | 25.27 | 39.01 | 48.42 | 95.90 |
| alcohol: beer | US-CA | sugars | 26 | 0.00 | 0.00 | 0.00 | 3.48 | 6.70 |
| alcohol: beer | US-CA | protein | 28 | 0.00 | 0.00 | 0.31 | 0.52 | 0.70 |
| alcohol: beer | US-CA | fat | 24 | 0.00 | 0.00 | 0.00 | 0.00 | 0.09 |
| alcohol: beer | US-CA | salt | 17 | 0.00 | 0.00 | 0.00 | 0.01 | 0.02 |
| alcohol: cider | FR | energy | 188 | 10.00 | 32.50 | 48.90 | 48.90 | 49.30 |
| alcohol: cider | FR | sugars | 214 | 0.00 | 0.02 | 3.85 | 10.10 | 10.41 |
| alcohol: cider | FR | protein | 175 | 0.00 | 0.00 | 0.11 | 0.27 | 0.27 |
| alcohol: cider | FR | fat | 175 | 0.00 | 0.00 | 0.13 | 0.13 | 0.18 |
| alcohol: cider | FR | salt | 217 | 0.00 | 0.00 | 0.00 | 0.01 | 0.02 |
| alcohol: cider | UK-IE | energy | 36 | 27.70 | 33.91 | 40.92 | 45.50 | 51.50 |
| alcohol: cider | UK-IE | sugars | 31 | 0.00 | 1.58 | 4.00 | 6.95 | 9.20 |
| alcohol: cider | UK-IE | protein | 24 | 0.00 | 0.00 | 0.00 | 0.16 | 0.50 |
| alcohol: cider | UK-IE | fat | 24 | 0.00 | 0.00 | 0.00 | 0.07 | 0.50 |
| alcohol: cider | UK-IE | salt | 22 | 0.00 | 0.01 | 0.01 | 0.01 | 0.01 |
| alcohol: cider | US-CA | energy | 4 | 7.20 | 9.00 | 33.50 | 137.99 | 283.77 |
| alcohol: cider | US-CA | sugars | 4 | 1.67 | 1.67 | 4.58 | 29.43 | 68.92 |
| alcohol: cider | US-CA | protein | 4 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| alcohol: cider | US-CA | fat | 4 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| alcohol: cider | US-CA | salt | 4 | 0.00 | 0.00 | 0.01 | 0.10 | 0.25 |
| alcohol: cocktail/alcohol-style | FR | energy | 12 | 3.60 | 36.00 | 44.00 | 63.50 | 96.35 |
| alcohol: cocktail/alcohol-style | FR | sugars | 13 | 1.66 | 8.80 | 11.30 | 13.20 | 14.61 |
| alcohol: cocktail/alcohol-style | FR | protein | 13 | 0.00 | 0.00 | 0.10 | 0.50 | 0.66 |
| alcohol: cocktail/alcohol-style | FR | fat | 13 | 0.00 | 0.00 | 0.00 | 0.20 | 0.50 |
| alcohol: cocktail/alcohol-style | FR | salt | 14 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 |
| alcohol: cocktail/alcohol-style | UK-IE | energy | 3 | 20.20 | 20.50 | 21.00 | 29.00 | 33.80 |
| alcohol: cocktail/alcohol-style | UK-IE | sugars | 3 | 4.82 | 5.00 | 5.30 | 7.25 | 8.42 |
| alcohol: cocktail/alcohol-style | UK-IE | protein | 3 | 0.00 | 0.00 | 0.00 | 0.05 | 0.08 |
| alcohol: cocktail/alcohol-style | UK-IE | fat | 3 | 0.00 | 0.00 | 0.00 | 0.05 | 0.08 |
| alcohol: cocktail/alcohol-style | UK-IE | salt | 3 | 0.00 | 0.00 | 0.00 | 0.01 | 0.01 |
| alcohol: cocktail/alcohol-style | US-CA | energy | 3 | 1.13 | 2.82 | 5.63 | 12.95 | 17.34 |
| alcohol: cocktail/alcohol-style | US-CA | sugars | 3 | 0.17 | 0.42 | 0.85 | 2.45 | 3.41 |
| alcohol: cocktail/alcohol-style | US-CA | protein | 3 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| alcohol: cocktail/alcohol-style | US-CA | fat | 3 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| alcohol: cocktail/alcohol-style | US-CA | salt | 3 | 0.00 | 0.00 | 0.01 | 0.02 | 0.02 |
| alcohol: spirits/liqueurs | FR | energy | 158 | 0.00 | 55.80 | 209.50 | 253.25 | 381.20 |
| alcohol: spirits/liqueurs | FR | sugars | 212 | 0.00 | 0.00 | 0.10 | 5.31 | 31.71 |
| alcohol: spirits/liqueurs | FR | protein | 189 | 0.00 | 0.00 | 0.00 | 0.06 | 0.93 |
| alcohol: spirits/liqueurs | FR | fat | 189 | 0.00 | 0.00 | 0.00 | 0.01 | 2.00 |
| alcohol: spirits/liqueurs | FR | salt | 217 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 |
| alcohol: spirits/liqueurs | UK-IE | energy | 34 | 56.60 | 192.75 | 224.71 | 265.00 | 298.90 |
| alcohol: spirits/liqueurs | UK-IE | sugars | 32 | 0.00 | 0.00 | 0.00 | 0.10 | 9.91 |
| alcohol: spirits/liqueurs | UK-IE | protein | 28 | 0.00 | 0.00 | 0.00 | 0.00 | 0.37 |
| alcohol: spirits/liqueurs | UK-IE | fat | 30 | 0.00 | 0.00 | 0.00 | 0.00 | 0.30 |
| alcohol: spirits/liqueurs | UK-IE | salt | 28 | 0.00 | 0.00 | 0.00 | 0.01 | 0.09 |
| alcohol: spirits/liqueurs | US-CA | energy | 10 | 0.00 | 44.88 | 208.23 | 221.00 | 418.99 |
| alcohol: spirits/liqueurs | US-CA | sugars | 13 | 0.00 | 0.00 | 0.00 | 0.00 | 0.23 |
| alcohol: spirits/liqueurs | US-CA | protein | 8 | 0.00 | 0.00 | 0.00 | 0.00 | 0.54 |
| alcohol: spirits/liqueurs | US-CA | fat | 7 | 0.00 | 0.00 | 0.00 | 0.00 | 6.00 |
| alcohol: spirits/liqueurs | US-CA | salt | 7 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| alcohol: wine | FR | energy | 898 | 0.00 | 33.10 | 73.40 | 86.75 | 660.10 |
| alcohol: wine | FR | sugars | 1155 | 0.00 | 0.00 | 0.00 | 1.40 | 15.00 |
| alcohol: wine | FR | protein | 807 | 0.00 | 0.00 | 0.07 | 0.30 | 0.72 |
| alcohol: wine | FR | fat | 812 | 0.00 | 0.00 | 0.00 | 0.16 | 0.60 |
| alcohol: wine | FR | salt | 1168 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 |
| alcohol: wine | UK-IE | energy | 87 | 18.60 | 55.10 | 73.20 | 82.10 | 268.80 |
| alcohol: wine | UK-IE | sugars | 105 | 0.00 | 0.00 | 0.50 | 2.50 | 9.86 |
| alcohol: wine | UK-IE | protein | 69 | 0.00 | 0.00 | 0.07 | 0.30 | 0.72 |
| alcohol: wine | UK-IE | fat | 70 | 0.00 | 0.00 | 0.00 | 0.14 | 0.50 |
| alcohol: wine | UK-IE | salt | 66 | 0.00 | 0.00 | 0.00 | 0.01 | 0.09 |
| alcohol: wine | US-CA | energy | 4 | 41.72 | 62.04 | 79.17 | 96.25 | 116.50 |
| alcohol: wine | US-CA | sugars | 7 | 0.00 | 0.00 | 0.00 | 2.25 | 8.30 |
| alcohol: wine | US-CA | protein | 3 | 0.00 | 0.00 | 0.00 | 0.14 | 0.23 |
| alcohol: wine | US-CA | fat | 2 | 0.07 | 0.18 | 0.35 | 0.53 | 0.63 |
| alcohol: wine | US-CA | salt | 3 | 0.00 | 0.00 | 0.01 | 0.01 | 0.02 |
| coconut water | FR | energy | 207 | 14.00 | 16.00 | 19.00 | 22.68 | 28.32 |
| coconut water | FR | sugars | 206 | 2.00 | 2.60 | 3.65 | 4.90 | 5.61 |
| coconut water | FR | protein | 207 | 0.00 | 0.00 | 0.00 | 0.20 | 0.50 |
| coconut water | FR | fat | 207 | 0.00 | 0.00 | 0.00 | 0.06 | 0.20 |
| coconut water | FR | salt | 201 | 0.00 | 0.03 | 0.05 | 0.10 | 0.13 |
| coconut water | UK-IE | energy | 30 | 13.18 | 16.50 | 18.88 | 22.00 | 27.20 |
| coconut water | UK-IE | sugars | 30 | 2.20 | 2.78 | 4.00 | 4.15 | 5.01 |
| coconut water | UK-IE | protein | 30 | 0.00 | 0.00 | 0.00 | 0.10 | 0.10 |
| coconut water | UK-IE | fat | 30 | 0.00 | 0.00 | 0.00 | 0.10 | 0.51 |
| coconut water | UK-IE | salt | 29 | 0.00 | 0.04 | 0.08 | 0.10 | 0.13 |
| coconut water | US-CA | energy | 76 | 18.00 | 18.75 | 20.92 | 25.00 | 32.50 |
| coconut water | US-CA | sugars | 75 | 2.96 | 3.80 | 4.55 | 5.63 | 6.81 |
| coconut water | US-CA | protein | 76 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| coconut water | US-CA | fat | 76 | 0.00 | 0.00 | 0.00 | 0.00 | 0.20 |
| coconut water | US-CA | salt | 76 | 0.03 | 0.04 | 0.05 | 0.06 | 0.10 |
| energy drink | FR | energy | 700 | 3.00 | 16.00 | 39.00 | 46.00 | 50.50 |
| energy drink | FR | sugars | 691 | 0.00 | 3.00 | 8.70 | 11.00 | 11.50 |
| energy drink | FR | protein | 694 | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 |
| energy drink | FR | fat | 691 | 0.00 | 0.00 | 0.00 | 0.00 | 0.50 |
| energy drink | FR | salt | 665 | 0.00 | 0.03 | 0.10 | 0.19 | 0.23 |
| energy drink | UK-IE | energy | 259 | 2.00 | 3.00 | 20.00 | 45.00 | 48.00 |
| energy drink | UK-IE | sugars | 243 | 0.00 | 0.00 | 4.30 | 9.00 | 11.00 |
| energy drink | UK-IE | protein | 249 | 0.00 | 0.00 | 0.00 | 0.00 | 0.50 |
| energy drink | UK-IE | fat | 249 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| energy drink | UK-IE | salt | 226 | 0.00 | 0.05 | 0.10 | 0.16 | 0.20 |
| energy drink | US-CA | energy | 175 | 1.41 | 2.11 | 2.82 | 25.68 | 47.76 |
| energy drink | US-CA | sugars | 145 | 0.00 | 0.00 | 0.00 | 5.75 | 11.00 |
| energy drink | US-CA | protein | 169 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| energy drink | US-CA | fat | 169 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| energy drink | US-CA | salt | 168 | 0.00 | 0.01 | 0.07 | 0.16 | 0.25 |
| fermented soft drink | FR | energy | 649 | 10.00 | 12.70 | 15.80 | 18.00 | 23.00 |
| fermented soft drink | FR | sugars | 644 | 0.50 | 2.50 | 3.49 | 4.00 | 4.60 |
| fermented soft drink | FR | protein | 639 | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 |
| fermented soft drink | FR | fat | 639 | 0.00 | 0.00 | 0.00 | 0.00 | 0.20 |
| fermented soft drink | FR | salt | 580 | 0.00 | 0.00 | 0.00 | 0.00 | 0.10 |
| fermented soft drink | UK-IE | energy | 150 | 2.73 | 9.00 | 14.00 | 17.00 | 20.00 |
| fermented soft drink | UK-IE | sugars | 148 | 0.00 | 1.60 | 2.70 | 3.40 | 3.93 |
| fermented soft drink | UK-IE | protein | 146 | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 |
| fermented soft drink | UK-IE | fat | 147 | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 |
| fermented soft drink | UK-IE | salt | 120 | 0.00 | 0.00 | 0.00 | 0.03 | 0.10 |
| fermented soft drink | US-CA | energy | 50 | 3.76 | 10.68 | 13.67 | 16.91 | 19.11 |
| fermented soft drink | US-CA | sugars | 50 | 0.75 | 2.06 | 2.91 | 3.79 | 4.43 |
| fermented soft drink | US-CA | protein | 50 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 |
| fermented soft drink | US-CA | fat | 50 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| fermented soft drink | US-CA | salt | 45 | 0.00 | 0.00 | 0.00 | 0.01 | 0.03 |
| flavoured water | FR | energy | 347 | 0.00 | 0.00 | 1.00 | 17.00 | 21.13 |
| flavoured water | FR | sugars | 335 | 0.00 | 0.00 | 0.00 | 4.15 | 4.90 |
| flavoured water | FR | protein | 345 | 0.00 | 0.00 | 0.00 | 0.00 | 0.50 |
| flavoured water | FR | fat | 344 | 0.00 | 0.00 | 0.00 | 0.00 | 0.50 |
| flavoured water | FR | salt | 330 | 0.00 | 0.00 | 0.01 | 0.02 | 0.04 |
| flavoured water | UK-IE | energy | 183 | 0.00 | 0.00 | 1.00 | 8.00 | 20.00 |
| flavoured water | UK-IE | sugars | 181 | 0.00 | 0.00 | 0.00 | 0.50 | 4.80 |
| flavoured water | UK-IE | protein | 179 | 0.00 | 0.00 | 0.00 | 0.00 | 0.10 |
| flavoured water | UK-IE | fat | 179 | 0.00 | 0.00 | 0.00 | 0.00 | 0.10 |
| flavoured water | UK-IE | salt | 162 | 0.00 | 0.00 | 0.00 | 0.01 | 0.05 |
| flavoured water | US-CA | energy | 79 | 0.00 | 0.00 | 0.00 | 0.00 | 10.39 |
| flavoured water | US-CA | sugars | 66 | 0.00 | 0.00 | 0.00 | 0.00 | 1.26 |
| flavoured water | US-CA | protein | 79 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| flavoured water | US-CA | fat | 79 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| flavoured water | US-CA | salt | 71 | 0.00 | 0.00 | 0.00 | 0.01 | 0.02 |
| fruit drink | FR | energy | 99 | 19.20 | 29.00 | 41.67 | 48.00 | 54.20 |
| fruit drink | FR | sugars | 99 | 2.67 | 6.33 | 9.58 | 11.40 | 13.00 |
| fruit drink | FR | protein | 99 | 0.00 | 0.00 | 0.00 | 0.26 | 0.50 |
| fruit drink | FR | fat | 99 | 0.00 | 0.00 | 0.00 | 0.10 | 0.50 |
| fruit drink | FR | salt | 94 | 0.00 | 0.00 | 0.01 | 0.04 | 0.10 |
| fruit drink | UK-IE | energy | 38 | 6.40 | 14.25 | 22.50 | 33.00 | 54.00 |
| fruit drink | UK-IE | sugars | 38 | 0.50 | 1.27 | 4.65 | 7.62 | 12.02 |
| fruit drink | UK-IE | protein | 38 | 0.00 | 0.00 | 0.10 | 0.20 | 0.50 |
| fruit drink | UK-IE | fat | 38 | 0.00 | 0.00 | 0.00 | 0.10 | 0.23 |
| fruit drink | UK-IE | salt | 36 | 0.00 | 0.00 | 0.01 | 0.09 | 0.10 |
| fruit drink | US-CA | energy | 31 | 8.47 | 24.62 | 40.00 | 46.33 | 50.00 |
| fruit drink | US-CA | sugars | 31 | 1.41 | 4.23 | 7.92 | 10.62 | 11.67 |
| fruit drink | US-CA | protein | 31 | 0.00 | 0.00 | 0.00 | 0.00 | 0.28 |
| fruit drink | US-CA | fat | 31 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| fruit drink | US-CA | salt | 31 | 0.00 | 0.01 | 0.03 | 0.05 | 0.11 |
| iced coffee | FR | energy | 11 | 30.00 | 40.00 | 49.00 | 76.80 | 94.00 |
| iced coffee | FR | sugars | 11 | 3.60 | 4.60 | 8.00 | 9.80 | 12.00 |
| iced coffee | FR | protein | 12 | 0.34 | 0.78 | 1.80 | 3.25 | 3.40 |
| iced coffee | FR | fat | 12 | 0.07 | 0.78 | 1.30 | 1.75 | 3.43 |
| iced coffee | FR | salt | 10 | 0.00 | 0.01 | 0.12 | 0.20 | 0.20 |
| iced coffee | UK-IE | energy | 25 | 37.08 | 39.00 | 41.80 | 54.00 | 55.80 |
| iced coffee | UK-IE | sugars | 25 | 1.54 | 4.30 | 4.90 | 5.60 | 6.74 |
| iced coffee | UK-IE | protein | 25 | 0.50 | 1.30 | 2.20 | 2.90 | 5.52 |
| iced coffee | UK-IE | fat | 25 | 0.44 | 1.00 | 1.10 | 1.20 | 1.60 |
| iced coffee | UK-IE | salt | 25 | 0.05 | 0.13 | 0.17 | 0.18 | 0.20 |
| iced coffee | US-CA | energy | 27 | 4.17 | 11.03 | 41.33 | 51.55 | 60.12 |
| iced coffee | US-CA | sugars | 26 | 0.00 | 0.08 | 4.15 | 5.70 | 10.22 |
| iced coffee | US-CA | protein | 27 | 0.00 | 0.41 | 1.23 | 2.12 | 2.22 |
| iced coffee | US-CA | fat | 27 | 0.00 | 0.00 | 1.10 | 1.84 | 2.05 |
| iced coffee | US-CA | salt | 26 | 0.00 | 0.01 | 0.09 | 0.13 | 0.18 |
| iced tea | FR | energy | 660 | 8.90 | 17.00 | 20.00 | 28.00 | 34.00 |
| iced tea | FR | sugars | 660 | 0.50 | 3.50 | 4.50 | 6.30 | 8.00 |
| iced tea | FR | protein | 659 | 0.00 | 0.00 | 0.00 | 0.50 | 0.50 |
| iced tea | FR | fat | 657 | 0.00 | 0.00 | 0.00 | 0.50 | 0.50 |
| iced tea | FR | salt | 623 | 0.00 | 0.01 | 0.02 | 0.03 | 0.08 |
| iced tea | UK-IE | energy | 25 | 5.63 | 13.00 | 14.00 | 19.20 | 28.60 |
| iced tea | UK-IE | sugars | 25 | 1.09 | 3.00 | 3.60 | 4.50 | 6.19 |
| iced tea | UK-IE | protein | 25 | 0.00 | 0.00 | 0.00 | 0.20 | 0.50 |
| iced tea | UK-IE | fat | 25 | 0.00 | 0.00 | 0.00 | 0.20 | 0.50 |
| iced tea | UK-IE | salt | 24 | 0.00 | 0.00 | 0.03 | 0.03 | 0.07 |
| iced tea | US-CA | energy | 54 | 1.22 | 18.37 | 23.08 | 33.84 | 135.66 |
| iced tea | US-CA | sugars | 54 | 0.00 | 4.43 | 5.38 | 8.87 | 16.73 |
| iced tea | US-CA | protein | 52 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| iced tea | US-CA | fat | 52 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| iced tea | US-CA | salt | 47 | 0.00 | 0.00 | 0.01 | 0.01 | 0.05 |
| juice | FR | energy | 7599 | 27.00 | 40.00 | 45.00 | 49.00 | 57.00 |
| juice | FR | sugars | 7550 | 3.50 | 8.50 | 9.80 | 11.00 | 12.40 |
| juice | FR | protein | 7587 | 0.00 | 0.10 | 0.50 | 0.60 | 0.75 |
| juice | FR | fat | 7564 | 0.00 | 0.00 | 0.10 | 0.40 | 0.50 |
| juice | FR | salt | 7093 | 0.00 | 0.00 | 0.01 | 0.02 | 0.10 |
| juice | UK-IE | energy | 745 | 20.00 | 39.00 | 44.00 | 47.00 | 53.00 |
| juice | UK-IE | sugars | 746 | 3.10 | 8.00 | 9.40 | 10.60 | 11.40 |
| juice | UK-IE | protein | 743 | 0.00 | 0.10 | 0.50 | 0.60 | 0.80 |
| juice | UK-IE | fat | 744 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| juice | UK-IE | salt | 648 | 0.00 | 0.00 | 0.01 | 0.03 | 0.10 |
| juice | US-CA | energy | 322 | 19.07 | 37.50 | 45.83 | 50.00 | 59.54 |
| juice | US-CA | sugars | 318 | 3.08 | 7.60 | 9.58 | 10.83 | 12.50 |
| juice | US-CA | protein | 322 | 0.00 | 0.00 | 0.40 | 0.83 | 0.83 |
| juice | US-CA | fat | 321 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| juice | US-CA | salt | 301 | 0.00 | 0.00 | 0.01 | 0.03 | 0.10 |
| nectar | FR | energy | 1770 | 34.00 | 42.00 | 48.00 | 54.00 | 60.00 |
| nectar | FR | sugars | 1765 | 7.14 | 9.20 | 11.00 | 12.00 | 13.46 |
| nectar | FR | protein | 1765 | 0.00 | 0.10 | 0.40 | 0.50 | 0.50 |
| nectar | FR | fat | 1763 | 0.00 | 0.00 | 0.10 | 0.50 | 0.50 |
| nectar | FR | salt | 1641 | 0.00 | 0.00 | 0.00 | 0.01 | 0.03 |
| nectar | UK-IE | energy | 13 | 6.57 | 20.00 | 26.00 | 52.00 | 57.40 |
| nectar | UK-IE | sugars | 12 | 0.91 | 3.55 | 5.85 | 9.43 | 12.77 |
| nectar | UK-IE | protein | 13 | 0.02 | 0.10 | 0.30 | 0.50 | 0.98 |
| nectar | UK-IE | fat | 13 | 0.00 | 0.00 | 0.10 | 0.35 | 0.50 |
| nectar | UK-IE | salt | 11 | 0.00 | 0.00 | 0.01 | 0.01 | 0.16 |
| nectar | US-CA | energy | 36 | 45.30 | 48.25 | 58.67 | 65.53 | 80.00 |
| nectar | US-CA | sugars | 36 | 9.64 | 10.55 | 12.61 | 14.46 | 16.80 |
| nectar | US-CA | protein | 36 | 0.00 | 0.00 | 0.00 | 0.00 | 0.21 |
| nectar | US-CA | fat | 36 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| nectar | US-CA | salt | 29 | 0.00 | 0.00 | 0.02 | 0.04 | 0.07 |
| plant drink: almond | FR | energy | 297 | 16.00 | 24.00 | 34.00 | 49.00 | 63.00 |
| plant drink: almond | FR | sugars | 294 | 0.00 | 0.30 | 2.50 | 4.20 | 7.17 |
| plant drink: almond | FR | protein | 298 | 0.40 | 0.50 | 0.70 | 1.11 | 1.70 |
| plant drink: almond | FR | fat | 298 | 1.08 | 1.25 | 1.85 | 2.68 | 4.00 |
| plant drink: almond | FR | salt | 292 | 0.01 | 0.05 | 0.10 | 0.13 | 0.15 |
| plant drink: almond | UK-IE | energy | 53 | 14.00 | 16.00 | 23.00 | 28.00 | 38.20 |
| plant drink: almond | UK-IE | sugars | 52 | 0.00 | 0.11 | 0.50 | 2.50 | 3.20 |
| plant drink: almond | UK-IE | protein | 54 | 0.50 | 0.50 | 0.60 | 0.80 | 0.97 |
| plant drink: almond | UK-IE | fat | 54 | 1.00 | 1.12 | 1.40 | 1.68 | 2.20 |
| plant drink: almond | UK-IE | salt | 50 | 0.10 | 0.10 | 0.14 | 0.16 | 0.18 |
| plant drink: almond | US-CA | energy | 63 | 12.50 | 14.58 | 25.00 | 37.71 | 76.00 |
| plant drink: almond | US-CA | sugars | 60 | 0.00 | 0.00 | 0.42 | 3.62 | 7.00 |
| plant drink: almond | US-CA | protein | 63 | 0.40 | 0.42 | 0.42 | 1.00 | 2.82 |
| plant drink: almond | US-CA | fat | 63 | 1.00 | 1.04 | 1.20 | 1.98 | 3.40 |
| plant drink: almond | US-CA | salt | 62 | 0.06 | 0.13 | 0.16 | 0.18 | 0.26 |
| plant drink: coconut | FR | energy | 29 | 19.75 | 28.00 | 61.00 | 172.00 | 209.40 |
| plant drink: coconut | FR | sugars | 29 | 0.00 | 0.30 | 1.60 | 2.10 | 6.68 |
| plant drink: coconut | FR | protein | 29 | 0.00 | 0.20 | 0.50 | 1.20 | 1.72 |
| plant drink: coconut | FR | fat | 29 | 1.48 | 1.90 | 4.00 | 17.00 | 21.20 |
| plant drink: coconut | FR | salt | 27 | 0.04 | 0.05 | 0.09 | 0.10 | 0.13 |
| plant drink: coconut | UK-IE | energy | 13 | 19.04 | 21.00 | 28.00 | 54.00 | 65.20 |
| plant drink: coconut | UK-IE | sugars | 13 | 0.24 | 1.10 | 2.20 | 3.00 | 4.02 |
| plant drink: coconut | UK-IE | protein | 13 | 0.22 | 0.50 | 0.50 | 1.10 | 1.52 |
| plant drink: coconut | UK-IE | fat | 13 | 0.83 | 1.10 | 1.40 | 2.00 | 5.54 |
| plant drink: coconut | UK-IE | salt | 11 | 0.08 | 0.08 | 0.10 | 0.11 | 0.13 |
| plant drink: coconut | US-CA | energy | 11 | 20.00 | 20.92 | 45.00 | 77.00 | 112.68 |
| plant drink: coconut | US-CA | sugars | 10 | 0.06 | 0.25 | 0.42 | 1.80 | 4.70 |
| plant drink: coconut | US-CA | protein | 11 | 0.00 | 0.00 | 0.42 | 1.50 | 5.45 |
| plant drink: coconut | US-CA | fat | 11 | 1.80 | 1.85 | 2.08 | 5.65 | 7.04 |
| plant drink: coconut | US-CA | salt | 11 | 0.01 | 0.02 | 0.03 | 0.16 | 0.18 |
| plant drink: oat | FR | energy | 10 | 40.70 | 44.25 | 52.00 | 54.75 | 73.60 |
| plant drink: oat | FR | sugars | 10 | 1.12 | 2.10 | 4.00 | 4.42 | 6.77 |
| plant drink: oat | FR | protein | 10 | 0.29 | 0.46 | 0.60 | 1.20 | 2.99 |
| plant drink: oat | FR | fat | 10 | 1.30 | 1.62 | 1.95 | 2.15 | 2.46 |
| plant drink: oat | FR | salt | 9 | 0.07 | 0.09 | 0.10 | 0.12 | 0.15 |
| plant drink: oat | UK-IE | energy | 5 | 37.60 | 40.00 | 40.00 | 48.00 | 49.80 |
| plant drink: oat | UK-IE | sugars | 3 | 3.44 | 3.50 | 3.60 | 3.70 | 3.76 |
| plant drink: oat | UK-IE | protein | 5 | 0.28 | 0.40 | 1.10 | 1.20 | 1.26 |
| plant drink: oat | UK-IE | fat | 5 | 1.16 | 1.40 | 1.50 | 1.50 | 1.98 |
| plant drink: oat | UK-IE | salt | 4 | 0.08 | 0.09 | 0.12 | 0.14 | 0.14 |
| plant drink: oat | US-CA | energy | 5 | 29.40 | 30.00 | 33.07 | 40.00 | 94.00 |
| plant drink: oat | US-CA | sugars | 4 | 0.67 | 1.04 | 2.62 | 4.04 | 4.10 |
| plant drink: oat | US-CA | protein | 5 | 0.08 | 0.20 | 0.36 | 0.42 | 0.67 |
| plant drink: oat | US-CA | fat | 5 | 0.93 | 1.00 | 1.25 | 1.50 | 1.85 |
| plant drink: oat | US-CA | salt | 4 | 0.11 | 0.12 | 0.18 | 0.29 | 0.37 |
| plant drink: rice | FR | energy | 7 | 49.20 | 58.50 | 61.00 | 73.50 | 76.80 |
| plant drink: rice | FR | sugars | 7 | 3.92 | 4.90 | 7.40 | 8.15 | 8.50 |
| plant drink: rice | FR | protein | 7 | 0.20 | 0.35 | 0.50 | 0.90 | 1.48 |
| plant drink: rice | FR | fat | 7 | 0.90 | 1.20 | 1.60 | 2.55 | 3.04 |
| plant drink: rice | FR | salt | 7 | 0.08 | 0.08 | 0.10 | 0.15 | 0.36 |
| plant drink: rice | UK-IE | energy | 1 | 49.00 | 49.00 | 49.00 | 49.00 | 49.00 |
| plant drink: rice | UK-IE | sugars | 1 | 3.00 | 3.00 | 3.00 | 3.00 | 3.00 |
| plant drink: rice | UK-IE | protein | 1 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 |
| plant drink: rice | UK-IE | fat | 1 | 1.20 | 1.20 | 1.20 | 1.20 | 1.20 |
| plant drink: rice | UK-IE | salt | 1 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 |
| plant drink: rice | US-CA | energy | 0 | — | — | — | — | — |
| plant drink: rice | US-CA | sugars | 0 | — | — | — | — | — |
| plant drink: rice | US-CA | protein | 0 | — | — | — | — | — |
| plant drink: rice | US-CA | fat | 0 | — | — | — | — | — |
| plant drink: rice | US-CA | salt | 0 | — | — | — | — | — |
| plant drink: soy | FR | energy | 253 | 34.00 | 39.00 | 48.00 | 61.00 | 72.00 |
| plant drink: soy | FR | sugars | 255 | 0.40 | 0.70 | 3.00 | 5.90 | 8.00 |
| plant drink: soy | FR | protein | 255 | 2.34 | 3.00 | 3.30 | 3.70 | 3.86 |
| plant drink: soy | FR | fat | 253 | 1.40 | 1.70 | 1.90 | 2.10 | 2.80 |
| plant drink: soy | FR | salt | 249 | 0.01 | 0.04 | 0.10 | 0.12 | 0.16 |
| plant drink: soy | UK-IE | energy | 79 | 28.00 | 32.00 | 38.00 | 42.50 | 65.20 |
| plant drink: soy | UK-IE | sugars | 78 | 0.00 | 0.40 | 1.35 | 2.50 | 5.92 |
| plant drink: soy | UK-IE | protein | 79 | 2.00 | 3.00 | 3.20 | 3.40 | 3.95 |
| plant drink: soy | UK-IE | fat | 79 | 1.20 | 1.60 | 1.80 | 1.90 | 2.32 |
| plant drink: soy | UK-IE | salt | 75 | 0.03 | 0.08 | 0.10 | 0.14 | 0.20 |
| plant drink: soy | US-CA | energy | 20 | 33.30 | 37.12 | 41.67 | 47.87 | 91.00 |
| plant drink: soy | US-CA | sugars | 20 | 0.42 | 0.42 | 2.50 | 4.69 | 6.10 |
| plant drink: soy | US-CA | protein | 20 | 2.84 | 2.92 | 3.33 | 3.75 | 6.64 |
| plant drink: soy | US-CA | fat | 20 | 1.24 | 1.46 | 1.67 | 1.88 | 3.51 |
| plant drink: soy | US-CA | salt | 16 | 0.05 | 0.09 | 0.10 | 0.12 | 0.18 |
| smoothie | FR | energy | 517 | 44.00 | 50.00 | 54.00 | 60.00 | 70.00 |
| smoothie | FR | sugars | 521 | 8.00 | 9.90 | 11.00 | 12.00 | 13.00 |
| smoothie | FR | protein | 519 | 0.00 | 0.50 | 0.53 | 0.77 | 1.00 |
| smoothie | FR | fat | 520 | 0.00 | 0.00 | 0.20 | 0.50 | 1.00 |
| smoothie | FR | salt | 467 | 0.00 | 0.00 | 0.01 | 0.02 | 0.10 |
| smoothie | UK-IE | energy | 161 | 42.07 | 47.00 | 52.00 | 58.00 | 66.00 |
| smoothie | UK-IE | sugars | 160 | 8.40 | 9.50 | 10.00 | 11.04 | 12.04 |
| smoothie | UK-IE | protein | 160 | 0.20 | 0.40 | 0.50 | 0.70 | 1.27 |
| smoothie | UK-IE | fat | 162 | 0.00 | 0.00 | 0.30 | 0.50 | 0.90 |
| smoothie | UK-IE | salt | 143 | 0.00 | 0.00 | 0.01 | 0.02 | 0.06 |
| smoothie | US-CA | energy | 57 | 43.60 | 50.68 | 61.95 | 79.65 | 104.00 |
| smoothie | US-CA | sugars | 57 | 4.58 | 8.45 | 9.89 | 11.00 | 13.17 |
| smoothie | US-CA | protein | 57 | 0.40 | 0.60 | 1.00 | 2.15 | 4.38 |
| smoothie | US-CA | fat | 57 | 0.00 | 0.00 | 0.33 | 0.88 | 1.89 |
| smoothie | US-CA | salt | 56 | 0.00 | 0.01 | 0.02 | 0.09 | 0.12 |
| soda | FR | energy | 3515 | 0.40 | 18.00 | 32.00 | 41.08 | 46.00 |
| soda | FR | sugars | 3473 | 0.00 | 4.00 | 7.60 | 10.00 | 11.03 |
| soda | FR | protein | 3494 | 0.00 | 0.00 | 0.00 | 0.00 | 0.20 |
| soda | FR | fat | 3490 | 0.00 | 0.00 | 0.00 | 0.00 | 0.10 |
| soda | FR | salt | 3271 | 0.00 | 0.00 | 0.01 | 0.02 | 0.04 |
| soda | UK-IE | energy | 669 | 0.40 | 1.00 | 15.60 | 23.00 | 42.00 |
| soda | UK-IE | sugars | 643 | 0.00 | 0.00 | 3.60 | 4.90 | 10.40 |
| soda | UK-IE | protein | 645 | 0.00 | 0.00 | 0.00 | 0.00 | 0.10 |
| soda | UK-IE | fat | 649 | 0.00 | 0.00 | 0.00 | 0.00 | 0.10 |
| soda | UK-IE | salt | 571 | 0.00 | 0.00 | 0.01 | 0.03 | 0.06 |
| soda | US-CA | energy | 449 | 0.00 | 3.66 | 36.62 | 45.00 | 50.00 |
| soda | US-CA | sugars | 420 | 0.00 | 0.85 | 9.30 | 11.25 | 12.78 |
| soda | US-CA | protein | 447 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| soda | US-CA | fat | 447 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| soda | US-CA | salt | 420 | 0.00 | 0.01 | 0.02 | 0.04 | 0.09 |
| sports/electrolyte drink | FR | energy | 34 | 4.46 | 17.75 | 22.54 | 24.00 | 362.00 |
| sports/electrolyte drink | FR | sugars | 32 | 0.00 | 3.90 | 4.75 | 5.83 | 18.02 |
| sports/electrolyte drink | FR | protein | 34 | 0.00 | 0.00 | 0.00 | 0.00 | 0.07 |
| sports/electrolyte drink | FR | fat | 33 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| sports/electrolyte drink | FR | salt | 33 | 0.00 | 0.02 | 0.13 | 0.15 | 0.27 |
| sports/electrolyte drink | UK-IE | energy | 8 | 4.00 | 4.00 | 4.70 | 19.24 | 24.46 |
| sports/electrolyte drink | UK-IE | sugars | 8 | 0.34 | 0.40 | 0.40 | 4.10 | 4.43 |
| sports/electrolyte drink | UK-IE | protein | 8 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 |
| sports/electrolyte drink | UK-IE | fat | 8 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 |
| sports/electrolyte drink | UK-IE | salt | 8 | 0.00 | 0.00 | 0.01 | 0.10 | 0.12 |
| sports/electrolyte drink | US-CA | energy | 40 | 1.17 | 4.00 | 13.33 | 23.00 | 23.82 |
| sports/electrolyte drink | US-CA | sugars | 35 | 0.00 | 0.40 | 5.35 | 5.82 | 5.92 |
| sports/electrolyte drink | US-CA | protein | 40 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| sports/electrolyte drink | US-CA | fat | 40 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| sports/electrolyte drink | US-CA | salt | 40 | 0.01 | 0.02 | 0.11 | 0.12 | 0.27 |
| water: unspecified flavour | FR | energy | 1870 | 0.00 | 0.00 | 0.00 | 2.00 | 28.00 |
| water: unspecified flavour | FR | sugars | 1853 | 0.00 | 0.00 | 0.00 | 0.00 | 5.70 |
| water: unspecified flavour | FR | protein | 1851 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| water: unspecified flavour | FR | fat | 1847 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| water: unspecified flavour | FR | salt | 1869 | 0.00 | 0.00 | 0.00 | 0.01 | 0.08 |
| water: unspecified flavour | UK-IE | energy | 219 | 0.00 | 0.00 | 1.00 | 15.00 | 25.00 |
| water: unspecified flavour | UK-IE | sugars | 207 | 0.00 | 0.00 | 0.00 | 2.02 | 4.54 |
| water: unspecified flavour | UK-IE | protein | 211 | 0.00 | 0.00 | 0.00 | 0.00 | 0.10 |
| water: unspecified flavour | UK-IE | fat | 212 | 0.00 | 0.00 | 0.00 | 0.00 | 0.10 |
| water: unspecified flavour | UK-IE | salt | 183 | 0.00 | 0.00 | 0.00 | 0.01 | 0.07 |
| water: unspecified flavour | US-CA | energy | 239 | 0.00 | 0.00 | 0.00 | 3.38 | 22.00 |
| water: unspecified flavour | US-CA | sugars | 226 | 0.00 | 0.00 | 0.00 | 0.28 | 4.00 |
| water: unspecified flavour | US-CA | protein | 236 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| water: unspecified flavour | US-CA | fat | 236 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| water: unspecified flavour | US-CA | salt | 230 | 0.00 | 0.00 | 0.00 | 0.01 | 0.06 |

</details>

<details><summary>Sugar thresholds and zeros</summary>

| Form | Region | Valid sugars | ≤0.1 | ≤0.5 | ≤1 | ≤2 | ≤5 | ≥5 | Observed zero |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| alcohol: beer | FR | 1281 | 558 | 680 | 759 | 829 | 1106 | 183 | 433 |
| alcohol: beer | UK-IE | 170 | 76 | 95 | 109 | 134 | 161 | 10 | 56 |
| alcohol: beer | US-CA | 26 | 17 | 17 | 17 | 18 | 21 | 5 | 16 |
| alcohol: cider | FR | 214 | 55 | 56 | 64 | 91 | 114 | 101 | 53 |
| alcohol: cider | UK-IE | 31 | 7 | 7 | 7 | 10 | 20 | 11 | 7 |
| alcohol: cider | US-CA | 4 | 0 | 0 | 0 | 2 | 2 | 2 | 0 |
| alcohol: cocktail/alcohol-style | FR | 13 | 2 | 2 | 2 | 2 | 2 | 11 | 2 |
| alcohol: cocktail/alcohol-style | UK-IE | 3 | 0 | 0 | 0 | 0 | 1 | 2 | 0 |
| alcohol: cocktail/alcohol-style | US-CA | 3 | 1 | 1 | 2 | 2 | 3 | 0 | 1 |
| alcohol: spirits/liqueurs | FR | 212 | 146 | 149 | 151 | 156 | 158 | 54 | 99 |
| alcohol: spirits/liqueurs | UK-IE | 32 | 28 | 28 | 28 | 28 | 28 | 4 | 23 |
| alcohol: spirits/liqueurs | US-CA | 13 | 11 | 12 | 12 | 12 | 12 | 1 | 11 |
| alcohol: wine | FR | 1155 | 606 | 684 | 824 | 912 | 968 | 191 | 584 |
| alcohol: wine | UK-IE | 105 | 49 | 53 | 60 | 76 | 91 | 15 | 49 |
| alcohol: wine | US-CA | 7 | 5 | 5 | 5 | 5 | 6 | 1 | 5 |
| coconut water | FR | 206 | 4 | 4 | 5 | 26 | 167 | 51 | 4 |
| coconut water | UK-IE | 30 | 0 | 0 | 1 | 1 | 27 | 3 | 0 |
| coconut water | US-CA | 75 | 0 | 2 | 2 | 3 | 50 | 30 | 0 |
| energy drink | FR | 691 | 148 | 153 | 155 | 162 | 260 | 439 | 129 |
| energy drink | UK-IE | 243 | 85 | 88 | 93 | 93 | 163 | 81 | 78 |
| energy drink | US-CA | 145 | 93 | 97 | 99 | 101 | 107 | 38 | 92 |
| fermented soft drink | FR | 644 | 51 | 69 | 72 | 100 | 612 | 37 | 49 |
| fermented soft drink | UK-IE | 148 | 25 | 31 | 35 | 48 | 147 | 1 | 22 |
| fermented soft drink | US-CA | 50 | 4 | 4 | 7 | 11 | 47 | 3 | 4 |
| flavoured water | FR | 335 | 186 | 199 | 207 | 214 | 308 | 30 | 175 |
| flavoured water | UK-IE | 181 | 118 | 136 | 138 | 144 | 171 | 10 | 105 |
| flavoured water | US-CA | 66 | 57 | 57 | 59 | 60 | 64 | 2 | 57 |
| fruit drink | FR | 99 | 1 | 3 | 6 | 10 | 20 | 81 | 1 |
| fruit drink | UK-IE | 38 | 1 | 6 | 8 | 11 | 23 | 16 | 1 |
| fruit drink | US-CA | 31 | 1 | 2 | 2 | 6 | 9 | 22 | 1 |
| iced coffee | FR | 11 | 0 | 1 | 1 | 1 | 4 | 7 | 0 |
| iced coffee | UK-IE | 25 | 2 | 3 | 3 | 3 | 16 | 9 | 0 |
| iced coffee | US-CA | 26 | 7 | 8 | 8 | 9 | 18 | 8 | 7 |
| iced tea | FR | 660 | 51 | 69 | 72 | 83 | 428 | 240 | 44 |
| iced tea | UK-IE | 25 | 0 | 2 | 3 | 4 | 21 | 4 | 0 |
| iced tea | US-CA | 54 | 8 | 8 | 9 | 9 | 22 | 32 | 8 |
| juice | FR | 7550 | 107 | 139 | 196 | 474 | 993 | 6571 | 91 |
| juice | UK-IE | 746 | 10 | 24 | 37 | 52 | 123 | 627 | 8 |
| juice | US-CA | 318 | 14 | 15 | 16 | 18 | 52 | 268 | 14 |
| nectar | FR | 1765 | 12 | 12 | 13 | 15 | 96 | 1687 | 12 |
| nectar | UK-IE | 12 | 0 | 1 | 3 | 3 | 4 | 8 | 0 |
| nectar | US-CA | 36 | 0 | 0 | 0 | 0 | 0 | 36 | 0 |
| plant drink: almond | FR | 294 | 59 | 119 | 120 | 127 | 241 | 54 | 44 |
| plant drink: almond | UK-IE | 52 | 12 | 33 | 33 | 34 | 49 | 3 | 8 |
| plant drink: almond | US-CA | 60 | 26 | 32 | 33 | 33 | 47 | 14 | 26 |
| plant drink: coconut | FR | 29 | 7 | 11 | 13 | 18 | 25 | 4 | 6 |
| plant drink: coconut | UK-IE | 13 | 0 | 3 | 3 | 4 | 12 | 1 | 0 |
| plant drink: coconut | US-CA | 10 | 2 | 6 | 6 | 8 | 9 | 1 | 1 |
| plant drink: oat | FR | 10 | 0 | 1 | 1 | 3 | 8 | 2 | 0 |
| plant drink: oat | UK-IE | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| plant drink: oat | US-CA | 4 | 0 | 1 | 1 | 2 | 4 | 0 | 0 |
| plant drink: rice | FR | 7 | 0 | 0 | 0 | 0 | 3 | 5 | 0 |
| plant drink: rice | UK-IE | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| plant drink: rice | US-CA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| plant drink: soy | FR | 255 | 10 | 42 | 78 | 95 | 173 | 84 | 9 |
| plant drink: soy | UK-IE | 78 | 15 | 33 | 38 | 45 | 68 | 12 | 13 |
| plant drink: soy | US-CA | 20 | 1 | 6 | 7 | 7 | 17 | 5 | 1 |
| smoothie | FR | 521 | 4 | 5 | 5 | 9 | 22 | 499 | 3 |
| smoothie | UK-IE | 160 | 0 | 1 | 3 | 4 | 6 | 154 | 0 |
| smoothie | US-CA | 57 | 1 | 1 | 1 | 1 | 7 | 50 | 1 |
| soda | FR | 3473 | 600 | 713 | 731 | 786 | 1135 | 2359 | 559 |
| soda | UK-IE | 643 | 200 | 255 | 265 | 287 | 485 | 158 | 177 |
| soda | US-CA | 420 | 87 | 96 | 111 | 158 | 182 | 240 | 85 |
| sports/electrolyte drink | FR | 32 | 5 | 6 | 6 | 6 | 18 | 14 | 4 |
| sports/electrolyte drink | UK-IE | 8 | 0 | 5 | 5 | 5 | 8 | 0 | 0 |
| sports/electrolyte drink | US-CA | 35 | 6 | 13 | 13 | 13 | 16 | 19 | 6 |
| water: unspecified flavour | FR | 1853 | 1439 | 1469 | 1481 | 1505 | 1646 | 215 | 1409 |
| water: unspecified flavour | UK-IE | 207 | 134 | 145 | 151 | 155 | 194 | 13 | 127 |
| water: unspecified flavour | US-CA | 226 | 163 | 174 | 186 | 196 | 212 | 16 | 162 |

</details>

<details><summary>Composition by sugar band</summary>

| Form | Region | Sugars band | N | energy | sugars | protein | fat | salt | Energy N | Protein N |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| alcohol: beer | FR | ≤0.5 | 680 | 45.00 | 0.00 | 0.40 | 0.00 | 0.01 | 499 | 482 |
| alcohol: beer | FR | 0.5–5 | 418 | 29.00 | 2.60 | 0.50 | 0.00 | 0.01 | 416 | 411 |
| alcohol: beer | FR | ≥5 | 183 | 32.00 | 6.30 | 0.20 | 0.00 | 0.01 | 181 | 179 |
| alcohol: beer | UK-IE | ≤0.5 | 95 | 39.00 | 0.00 | 0.30 | 0.00 | 0.00 | 67 | 60 |
| alcohol: beer | UK-IE | 0.5–5 | 65 | 23.00 | 1.80 | 0.29 | 0.00 | 0.01 | 64 | 62 |
| alcohol: beer | UK-IE | ≥5 | 10 | 33.20 | 6.25 | 0.40 | 0.05 | 0.01 | 10 | 10 |
| alcohol: beer | US-CA | ≤0.5 | 17 | 45.00 | 0.00 | 0.36 | 0.00 | 0.00 | 8 | 8 |
| alcohol: beer | US-CA | 0.5–5 | 4 | 19.05 | 3.25 | 0.33 | 0.00 | 0.00 | 4 | 4 |
| alcohol: beer | US-CA | ≥5 | 5 | 47.89 | 7.10 | 0.20 | 0.00 | 0.01 | 5 | 5 |
| alcohol: cider | FR | ≤0.5 | 56 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 21 | 20 |
| alcohol: cider | FR | 0.5–5 | 57 | 32.50 | 1.58 | 0.00 | 0.00 | 0.01 | 55 | 54 |
| alcohol: cider | FR | ≥5 | 101 | 48.90 | 10.10 | 0.27 | 0.13 | 0.00 | 100 | 100 |
| alcohol: cider | UK-IE | ≤0.5 | 7 | 42.50 | 0.00 | 0.00 | 0.00 | 0.00 | 2 | 1 |
| alcohol: cider | UK-IE | 0.5–5 | 13 | 40.85 | 4.00 | 0.00 | 0.00 | 0.01 | 13 | 13 |
| alcohol: cider | UK-IE | ≥5 | 11 | 38.00 | 9.00 | 0.27 | 0.13 | 0.01 | 11 | 9 |
| alcohol: cider | US-CA | ≤0.5 | 0 | — | — | — | — | — | 0 | 0 |
| alcohol: cider | US-CA | 0.5–5 | 2 | 8.00 | 1.67 | 0.00 | 0.00 | 0.01 | 2 | 2 |
| alcohol: cider | US-CA | ≥5 | 2 | 218.98 | 51.37 | 0.00 | 0.00 | 0.18 | 2 | 2 |
| alcohol: cocktail/alcohol-style | FR | ≤0.5 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 2 | 2 |
| alcohol: cocktail/alcohol-style | FR | 0.5–5 | 0 | — | — | — | — | — | 0 | 0 |
| alcohol: cocktail/alcohol-style | FR | ≥5 | 11 | 49.50 | 12.00 | 0.10 | 0.01 | 0.00 | 10 | 11 |
| alcohol: cocktail/alcohol-style | UK-IE | ≤0.5 | 0 | — | — | — | — | — | 0 | 0 |
| alcohol: cocktail/alcohol-style | UK-IE | 0.5–5 | 1 | 20.00 | 4.70 | 0.00 | 0.00 | 0.00 | 1 | 1 |
| alcohol: cocktail/alcohol-style | UK-IE | ≥5 | 2 | 29.00 | 7.25 | 0.05 | 0.05 | 0.01 | 2 | 2 |
| alcohol: cocktail/alcohol-style | US-CA | ≤0.5 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1 | 1 |
| alcohol: cocktail/alcohol-style | US-CA | 0.5–5 | 2 | 12.95 | 2.45 | 0.00 | 0.00 | 0.02 | 2 | 2 |
| alcohol: cocktail/alcohol-style | US-CA | ≥5 | 0 | — | — | — | — | — | 0 | 0 |
| alcohol: spirits/liqueurs | FR | ≤0.5 | 149 | 220.00 | 0.00 | 0.00 | 0.00 | 0.00 | 69 | 110 |
| alcohol: spirits/liqueurs | FR | 0.5–5 | 9 | 63.00 | 1.78 | 0.74 | 2.00 | 0.02 | 7 | 9 |
| alcohol: spirits/liqueurs | FR | ≥5 | 54 | 182.58 | 25.74 | 0.10 | 0.10 | 0.01 | 36 | 52 |
| alcohol: spirits/liqueurs | UK-IE | ≤0.5 | 28 | 242.00 | 0.00 | 0.00 | 0.00 | 0.00 | 17 | 21 |
| alcohol: spirits/liqueurs | UK-IE | 0.5–5 | 0 | — | — | — | — | — | 0 | 0 |
| alcohol: spirits/liqueurs | UK-IE | ≥5 | 4 | — | 29.15 | 0.55 | 2.65 | 0.06 | 0 | 4 |
| alcohol: spirits/liqueurs | US-CA | ≤0.5 | 12 | 195.45 | 0.00 | 0.00 | 0.00 | 0.00 | 7 | 7 |
| alcohol: spirits/liqueurs | US-CA | 0.5–5 | 0 | — | — | — | — | — | 0 | 0 |
| alcohol: spirits/liqueurs | US-CA | ≥5 | 1 | 392.20 | 61.20 | 1.80 | 15.00 | 0.00 | 1 | 1 |
| alcohol: wine | FR | ≤0.5 | 684 | 85.00 | 0.00 | 0.00 | 0.00 | 0.00 | 347 | 327 |
| alcohol: wine | FR | 0.5–5 | 280 | 81.70 | 1.02 | 0.07 | 0.00 | 0.00 | 272 | 277 |
| alcohol: wine | FR | ≥5 | 191 | 73.20 | 15.50 | 0.72 | 0.16 | 0.01 | 179 | 188 |
| alcohol: wine | UK-IE | ≤0.5 | 53 | 78.55 | 0.00 | 0.00 | 0.00 | 0.00 | 20 | 17 |
| alcohol: wine | UK-IE | 0.5–5 | 37 | 66.40 | 1.40 | 0.10 | 0.00 | 0.00 | 35 | 35 |
| alcohol: wine | UK-IE | ≥5 | 15 | 73.20 | 15.50 | 0.56 | 0.16 | 0.01 | 11 | 15 |
| alcohol: wine | US-CA | ≤0.5 | 5 | 85.00 | 0.00 | 0.00 | — | 0.00 | 1 | 1 |
| alcohol: wine | US-CA | 0.5–5 | 1 | 28.17 | 4.51 | 0.28 | 0.70 | 0.01 | 1 | 1 |
| alcohol: wine | US-CA | ≥5 | 1 | 73.33 | 14.00 | 0.00 | 0.00 | 0.02 | 1 | 1 |
| coconut water | FR | ≤0.5 | 4 | 17.50 | 0.00 | 0.12 | 0.00 | 0.04 | 4 | 4 |
| coconut water | FR | 0.5–5 | 151 | 18.75 | 3.30 | 0.00 | 0.00 | 0.06 | 151 | 151 |
| coconut water | FR | ≥5 | 51 | 24.00 | 5.50 | 0.00 | 0.00 | 0.04 | 51 | 51 |
| coconut water | UK-IE | ≤0.5 | 0 | — | — | — | — | — | 0 | 0 |
| coconut water | UK-IE | 0.5–5 | 27 | 18.00 | 3.60 | 0.00 | 0.00 | 0.08 | 27 | 27 |
| coconut water | UK-IE | ≥5 | 3 | 26.00 | 6.00 | 0.00 | 0.00 | 0.04 | 3 | 3 |
| coconut water | US-CA | ≤0.5 | 2 | 17.44 | 0.37 | 0.00 | 0.00 | 0.05 | 2 | 2 |
| coconut water | US-CA | 0.5–5 | 43 | 18.75 | 3.94 | 0.00 | 0.00 | 0.06 | 43 | 43 |
| coconut water | US-CA | ≥5 | 30 | 25.48 | 6.05 | 0.00 | 0.00 | 0.05 | 30 | 30 |
| energy drink | FR | ≤0.5 | 153 | 3.00 | 0.00 | 0.00 | 0.00 | 0.11 | 151 | 147 |
| energy drink | FR | 0.5–5 | 99 | 20.00 | 4.40 | 0.00 | 0.00 | 0.09 | 98 | 98 |
| energy drink | FR | ≥5 | 439 | 46.00 | 11.00 | 0.00 | 0.00 | 0.10 | 435 | 434 |
| energy drink | UK-IE | ≤0.5 | 88 | 3.00 | 0.00 | 0.00 | 0.00 | 0.12 | 87 | 85 |
| energy drink | UK-IE | 0.5–5 | 74 | 21.00 | 4.49 | 0.00 | 0.00 | 0.08 | 73 | 69 |
| energy drink | UK-IE | ≥5 | 81 | 46.00 | 11.00 | 0.00 | 0.00 | 0.10 | 81 | 79 |
| energy drink | US-CA | ≤0.5 | 97 | 2.82 | 0.00 | 0.00 | 0.00 | 0.02 | 97 | 95 |
| energy drink | US-CA | 0.5–5 | 10 | 19.00 | 2.26 | 0.00 | 0.00 | 0.09 | 10 | 10 |
| energy drink | US-CA | ≥5 | 38 | 45.07 | 10.74 | 0.00 | 0.00 | 0.10 | 38 | 37 |
| fermented soft drink | FR | ≤0.5 | 69 | 6.40 | 0.00 | 0.00 | 0.00 | 0.00 | 69 | 69 |
| fermented soft drink | FR | 0.5–5 | 538 | 15.80 | 3.50 | 0.00 | 0.00 | 0.00 | 536 | 533 |
| fermented soft drink | FR | ≥5 | 37 | 24.00 | 5.90 | 0.00 | 0.00 | 0.00 | 37 | 35 |
| fermented soft drink | UK-IE | ≤0.5 | 31 | 2.73 | 0.00 | 0.00 | 0.00 | 0.00 | 31 | 31 |
| fermented soft drink | UK-IE | 0.5–5 | 116 | 15.00 | 2.93 | 0.10 | 0.00 | 0.00 | 116 | 113 |
| fermented soft drink | UK-IE | ≥5 | 1 | 45.00 | 11.00 | — | — | — | 1 | 0 |
| fermented soft drink | US-CA | ≤0.5 | 4 | 2.48 | 0.00 | 0.00 | 0.00 | 0.00 | 4 | 4 |
| fermented soft drink | US-CA | 0.5–5 | 43 | 14.00 | 2.96 | 0.00 | 0.00 | 0.00 | 43 | 43 |
| fermented soft drink | US-CA | ≥5 | 3 | 76.26 | 16.00 | 0.00 | 0.00 | 0.03 | 3 | 3 |
| flavoured water | FR | ≤0.5 | 199 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 199 | 198 |
| flavoured water | FR | 0.5–5 | 106 | 18.00 | 4.20 | 0.00 | 0.00 | 0.00 | 106 | 106 |
| flavoured water | FR | ≥5 | 30 | 28.00 | 6.80 | 0.00 | 0.00 | 0.01 | 30 | 29 |
| flavoured water | UK-IE | ≤0.5 | 136 | 0.40 | 0.00 | 0.00 | 0.00 | 0.00 | 135 | 135 |
| flavoured water | UK-IE | 0.5–5 | 35 | 17.00 | 4.20 | 0.00 | 0.00 | 0.00 | 35 | 34 |
| flavoured water | UK-IE | ≥5 | 10 | 30.50 | 7.35 | 0.10 | 0.10 | 0.01 | 10 | 9 |
| flavoured water | US-CA | ≤0.5 | 57 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 57 | 57 |
| flavoured water | US-CA | 0.5–5 | 7 | 16.67 | 4.33 | 0.00 | 0.00 | 0.00 | 7 | 7 |
| flavoured water | US-CA | ≥5 | 2 | 77.50 | 20.25 | 0.00 | 0.00 | 0.07 | 2 | 2 |
| fruit drink | FR | ≤0.5 | 3 | 41.00 | 0.40 | 0.10 | 0.10 | 0.01 | 3 | 3 |
| fruit drink | FR | 0.5–5 | 15 | 16.00 | 2.92 | 0.10 | 0.10 | 0.01 | 15 | 15 |
| fruit drink | FR | ≥5 | 81 | 44.00 | 10.00 | 0.00 | 0.00 | 0.02 | 81 | 81 |
| fruit drink | UK-IE | ≤0.5 | 6 | 7.60 | 0.45 | 0.10 | 0.05 | 0.06 | 6 | 6 |
| fruit drink | UK-IE | 0.5–5 | 16 | 19.00 | 2.92 | 0.10 | 0.00 | 0.01 | 16 | 16 |
| fruit drink | UK-IE | ≥5 | 16 | 41.80 | 10.30 | 0.15 | 0.10 | 0.01 | 16 | 16 |
| fruit drink | US-CA | ≤0.5 | 2 | 19.75 | 0.21 | 0.00 | 0.00 | 11.50 | 2 | 2 |
| fruit drink | US-CA | 0.5–5 | 7 | 11.30 | 1.69 | 0.00 | 0.00 | 0.01 | 7 | 7 |
| fruit drink | US-CA | ≥5 | 22 | 41.66 | 9.64 | 0.00 | 0.00 | 0.03 | 22 | 22 |
| iced coffee | FR | ≤0.5 | 1 | — | 0.30 | 6.00 | 1.40 | 0.20 | 0 | 1 |
| iced coffee | FR | 0.5–5 | 3 | 41.00 | 4.40 | 0.80 | 1.30 | 0.05 | 3 | 3 |
| iced coffee | FR | ≥5 | 7 | 63.60 | 8.60 | 2.90 | 0.80 | 0.12 | 7 | 7 |
| iced coffee | UK-IE | ≤0.5 | 3 | 5.20 | 0.10 | 0.20 | 0.12 | 0.02 | 3 | 3 |
| iced coffee | UK-IE | 0.5–5 | 13 | 39.00 | 4.90 | 2.20 | 1.10 | 0.17 | 13 | 13 |
| iced coffee | UK-IE | ≥5 | 9 | 54.00 | 6.10 | 3.00 | 1.00 | 0.18 | 9 | 9 |
| iced coffee | US-CA | ≤0.5 | 8 | 4.39 | 0.00 | 0.14 | 0.00 | 0.00 | 8 | 8 |
| iced coffee | US-CA | 0.5–5 | 10 | 42.18 | 4.15 | 2.15 | 1.27 | 0.13 | 10 | 10 |
| iced coffee | US-CA | ≥5 | 8 | 58.33 | 9.38 | 1.53 | 1.56 | 0.09 | 8 | 8 |
| iced tea | FR | ≤0.5 | 69 | 1.00 | 0.00 | 0.00 | 0.00 | 0.01 | 68 | 69 |
| iced tea | FR | 0.5–5 | 351 | 19.00 | 4.50 | 0.00 | 0.00 | 0.03 | 350 | 351 |
| iced tea | FR | ≥5 | 240 | 29.00 | 7.00 | 0.00 | 0.00 | 0.01 | 239 | 238 |
| iced tea | UK-IE | ≤0.5 | 2 | 1.48 | 0.12 | 0.02 | 0.00 | 0.04 | 2 | 2 |
| iced tea | UK-IE | 0.5–5 | 19 | 14.00 | 3.20 | 0.00 | 0.00 | 0.03 | 19 | 19 |
| iced tea | UK-IE | ≥5 | 4 | 29.50 | 7.05 | 0.10 | 0.05 | 0.01 | 4 | 4 |
| iced tea | US-CA | ≤0.5 | 8 | 1.00 | 0.00 | 0.00 | 0.00 | 0.01 | 7 | 7 |
| iced tea | US-CA | 0.5–5 | 14 | 18.46 | 4.59 | 0.00 | 0.00 | 0.00 | 14 | 13 |
| iced tea | US-CA | ≥5 | 32 | 30.56 | 8.14 | 0.00 | 0.00 | 0.00 | 32 | 32 |
| juice | FR | ≤0.5 | 139 | 25.70 | 0.00 | 0.10 | 0.00 | 0.00 | 136 | 138 |
| juice | FR | 0.5–5 | 840 | 22.00 | 2.70 | 0.50 | 0.10 | 0.02 | 839 | 837 |
| juice | FR | ≥5 | 6571 | 45.83 | 10.00 | 0.50 | 0.10 | 0.00 | 6561 | 6557 |
| juice | UK-IE | ≤0.5 | 24 | 2.00 | 0.18 | 0.01 | 0.02 | 0.04 | 24 | 23 |
| juice | UK-IE | 0.5–5 | 95 | 20.00 | 3.10 | 0.30 | 0.00 | 0.01 | 95 | 95 |
| juice | UK-IE | ≥5 | 627 | 45.00 | 9.90 | 0.50 | 0.10 | 0.01 | 624 | 623 |
| juice | US-CA | ≤0.5 | 15 | 1.88 | 0.00 | 0.00 | 0.00 | 0.02 | 15 | 15 |
| juice | US-CA | 0.5–5 | 35 | 19.73 | 3.09 | 0.42 | 0.00 | 0.05 | 35 | 35 |
| juice | US-CA | ≥5 | 268 | 46.00 | 9.71 | 0.42 | 0.00 | 0.01 | 268 | 268 |
| nectar | FR | ≤0.5 | 12 | 46.00 | 0.00 | 0.00 | 0.00 | 0.00 | 11 | 11 |
| nectar | FR | 0.5–5 | 66 | 23.00 | 4.45 | 0.30 | 0.10 | 0.01 | 66 | 66 |
| nectar | FR | ≥5 | 1687 | 48.00 | 11.00 | 0.40 | 0.10 | 0.00 | 1682 | 1680 |
| nectar | UK-IE | ≤0.5 | 1 | 2.00 | 0.20 | 0.10 | 0.10 | — | 1 | 1 |
| nectar | UK-IE | 0.5–5 | 3 | 23.00 | 1.00 | 0.50 | 0.35 | 0.02 | 3 | 3 |
| nectar | UK-IE | ≥5 | 8 | 41.50 | 8.40 | 0.32 | 0.14 | 0.01 | 8 | 8 |
| nectar | US-CA | ≤0.5 | 0 | — | — | — | — | — | 0 | 0 |
| nectar | US-CA | 0.5–5 | 0 | — | — | — | — | — | 0 | 0 |
| nectar | US-CA | ≥5 | 36 | 58.67 | 12.61 | 0.00 | 0.00 | 0.02 | 36 | 36 |
| plant drink: almond | FR | ≤0.5 | 119 | 25.00 | 0.12 | 0.70 | 1.70 | 0.10 | 119 | 119 |
| plant drink: almond | FR | 0.5–5 | 121 | 38.00 | 3.40 | 0.60 | 1.90 | 0.09 | 120 | 121 |
| plant drink: almond | FR | ≥5 | 54 | 59.50 | 7.25 | 0.80 | 2.10 | 0.08 | 54 | 54 |
| plant drink: almond | UK-IE | ≤0.5 | 33 | 18.00 | 0.20 | 0.60 | 1.30 | 0.15 | 33 | 33 |
| plant drink: almond | UK-IE | 0.5–5 | 16 | 29.00 | 2.55 | 0.66 | 1.45 | 0.14 | 16 | 16 |
| plant drink: almond | UK-IE | ≥5 | 3 | 55.00 | 5.70 | 0.80 | 1.80 | 0.12 | 2 | 3 |
| plant drink: almond | US-CA | ≤0.5 | 32 | 14.89 | 0.00 | 0.42 | 1.25 | 0.15 | 32 | 32 |
| plant drink: almond | US-CA | 0.5–5 | 14 | 25.00 | 2.92 | 0.42 | 1.04 | 0.16 | 14 | 14 |
| plant drink: almond | US-CA | ≥5 | 14 | 58.70 | 7.00 | 0.92 | 2.50 | 0.17 | 14 | 14 |
| plant drink: coconut | FR | ≤0.5 | 11 | 34.00 | 0.00 | 0.20 | 2.70 | 0.09 | 11 | 11 |
| plant drink: coconut | FR | 0.5–5 | 14 | 171.00 | 2.05 | 1.15 | 16.50 | 0.08 | 14 | 14 |
| plant drink: coconut | FR | ≥5 | 4 | 80.00 | 7.35 | 0.75 | 4.60 | 0.12 | 4 | 4 |
| plant drink: coconut | UK-IE | ≤0.5 | 3 | 19.00 | 0.20 | 1.20 | 1.40 | 0.10 | 3 | 3 |
| plant drink: coconut | UK-IE | 0.5–5 | 9 | 32.00 | 2.36 | 0.50 | 1.40 | 0.10 | 9 | 9 |
| plant drink: coconut | UK-IE | ≥5 | 1 | 503.00 | 22.00 | 4.30 | 27.50 | — | 1 | 1 |
| plant drink: coconut | US-CA | ≤0.5 | 6 | 27.15 | 0.30 | 0.00 | 1.98 | 0.03 | 6 | 6 |
| plant drink: coconut | US-CA | 0.5–5 | 3 | 112.68 | 1.90 | 5.45 | 7.04 | 0.16 | 3 | 3 |
| plant drink: coconut | US-CA | ≥5 | 1 | 90.00 | 9.00 | 1.00 | 5.00 | 0.28 | 1 | 1 |
| plant drink: oat | FR | ≤0.5 | 1 | 29.00 | 0.42 | 0.42 | 1.25 | 0.10 | 1 | 1 |
| plant drink: oat | FR | 0.5–5 | 7 | 51.00 | 4.00 | 0.60 | 2.00 | 0.10 | 7 | 7 |
| plant drink: oat | FR | ≥5 | 2 | 63.00 | 8.65 | 1.00 | 1.80 | 0.11 | 2 | 2 |
| plant drink: oat | UK-IE | ≤0.5 | 0 | — | — | — | — | — | 0 | 0 |
| plant drink: oat | UK-IE | 0.5–5 | 3 | 48.00 | 3.60 | 1.20 | 1.40 | 0.13 | 3 | 3 |
| plant drink: oat | UK-IE | ≥5 | 0 | — | — | — | — | — | 0 | 0 |
| plant drink: oat | US-CA | ≤0.5 | 1 | 29.00 | 0.42 | 0.42 | 1.25 | 0.10 | 1 | 1 |
| plant drink: oat | US-CA | 0.5–5 | 3 | 33.07 | 4.00 | 0.36 | 1.00 | 0.25 | 3 | 3 |
| plant drink: oat | US-CA | ≥5 | 0 | — | — | — | — | — | 0 | 0 |
| plant drink: rice | FR | ≤0.5 | 0 | — | — | — | — | — | 0 | 0 |
| plant drink: rice | FR | 0.5–5 | 2 | 57.50 | 3.70 | 1.20 | 1.80 | 0.14 | 2 | 2 |
| plant drink: rice | FR | ≥5 | 5 | 61.00 | 7.80 | 0.50 | 1.60 | 0.10 | 5 | 5 |
| plant drink: rice | UK-IE | ≤0.5 | 0 | — | — | — | — | — | 0 | 0 |
| plant drink: rice | UK-IE | 0.5–5 | 1 | 49.00 | 3.00 | 0.50 | 1.20 | 0.05 | 1 | 1 |
| plant drink: rice | UK-IE | ≥5 | 0 | — | — | — | — | — | 0 | 0 |
| plant drink: rice | US-CA | ≤0.5 | 0 | — | — | — | — | — | 0 | 0 |
| plant drink: rice | US-CA | 0.5–5 | 0 | — | — | — | — | — | 0 | 0 |
| plant drink: rice | US-CA | ≥5 | 0 | — | — | — | — | — | 0 | 0 |
| plant drink: soy | FR | ≤0.5 | 42 | 35.50 | 0.40 | 3.25 | 1.95 | 0.07 | 42 | 42 |
| plant drink: soy | FR | 0.5–5 | 129 | 42.00 | 2.50 | 3.30 | 1.90 | 0.09 | 129 | 129 |
| plant drink: soy | FR | ≥5 | 84 | 64.50 | 7.20 | 3.20 | 2.00 | 0.10 | 82 | 84 |
| plant drink: soy | UK-IE | ≤0.5 | 33 | 32.00 | 0.20 | 3.20 | 1.70 | 0.08 | 33 | 33 |
| plant drink: soy | UK-IE | 0.5–5 | 33 | 42.00 | 2.40 | 3.00 | 1.80 | 0.12 | 33 | 33 |
| plant drink: soy | UK-IE | ≥5 | 12 | 63.60 | 6.45 | 3.30 | 1.90 | 0.14 | 12 | 12 |
| plant drink: soy | US-CA | ≤0.5 | 6 | 36.67 | 0.42 | 3.33 | 1.77 | 0.07 | 6 | 6 |
| plant drink: soy | US-CA | 0.5–5 | 9 | 41.67 | 2.50 | 2.92 | 1.67 | 0.10 | 9 | 9 |
| plant drink: soy | US-CA | ≥5 | 5 | 90.00 | 6.00 | 6.60 | 3.50 | 0.24 | 5 | 5 |
| smoothie | FR | ≤0.5 | 5 | 54.00 | 0.00 | 0.60 | 0.10 | 0.01 | 5 | 5 |
| smoothie | FR | 0.5–5 | 17 | 42.50 | 3.40 | 0.93 | 0.70 | 0.07 | 16 | 17 |
| smoothie | FR | ≥5 | 499 | 54.83 | 11.00 | 0.50 | 0.20 | 0.01 | 496 | 497 |
| smoothie | UK-IE | ≤0.5 | 1 | — | 0.50 | 0.50 | 0.10 | 0.00 | 0 | 1 |
| smoothie | UK-IE | 0.5–5 | 5 | 17.00 | 1.33 | 0.80 | 0.50 | 0.03 | 5 | 5 |
| smoothie | UK-IE | ≥5 | 154 | 52.83 | 10.20 | 0.50 | 0.30 | 0.01 | 154 | 153 |
| smoothie | US-CA | ≤0.5 | 1 | 46.36 | 0.00 | 0.66 | 0.33 | 0.02 | 1 | 1 |
| smoothie | US-CA | 0.5–5 | 6 | 40.82 | 3.61 | 4.35 | 0.00 | 0.13 | 6 | 6 |
| smoothie | US-CA | ≥5 | 50 | 62.81 | 10.05 | 1.00 | 0.43 | 0.02 | 50 | 50 |
| soda | FR | ≤0.5 | 713 | 0.60 | 0.00 | 0.00 | 0.00 | 0.01 | 710 | 707 |
| soda | FR | 0.5–5 | 401 | 19.00 | 4.30 | 0.00 | 0.00 | 0.01 | 401 | 399 |
| soda | FR | ≥5 | 2359 | 38.00 | 9.00 | 0.00 | 0.00 | 0.00 | 2346 | 2343 |
| soda | UK-IE | ≤0.5 | 255 | 1.00 | 0.00 | 0.00 | 0.00 | 0.01 | 255 | 251 |
| soda | UK-IE | 0.5–5 | 230 | 19.00 | 4.30 | 0.00 | 0.00 | 0.00 | 229 | 218 |
| soda | UK-IE | ≥5 | 158 | 39.22 | 9.10 | 0.00 | 0.00 | 0.01 | 156 | 154 |
| soda | US-CA | ≤0.5 | 96 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 95 | 95 |
| soda | US-CA | 0.5–5 | 84 | 10.79 | 1.41 | 0.00 | 0.00 | 0.01 | 84 | 84 |
| soda | US-CA | ≥5 | 240 | 43.99 | 10.99 | 0.00 | 0.00 | 0.03 | 239 | 238 |
| sports/electrolyte drink | FR | ≤0.5 | 6 | 4.61 | 0.00 | 0.00 | 0.00 | 0.00 | 6 | 6 |
| sports/electrolyte drink | FR | 0.5–5 | 12 | 21.50 | 3.95 | 0.00 | 0.00 | 0.13 | 12 | 12 |
| sports/electrolyte drink | FR | ≥5 | 14 | 23.84 | 5.88 | 0.00 | 0.00 | 0.12 | 14 | 14 |
| sports/electrolyte drink | UK-IE | ≤0.5 | 5 | 4.00 | 0.40 | 0.00 | 0.00 | 0.00 | 5 | 5 |
| sports/electrolyte drink | UK-IE | 0.5–5 | 3 | 22.94 | 4.40 | 0.00 | 0.00 | 0.12 | 3 | 3 |
| sports/electrolyte drink | UK-IE | ≥5 | 0 | — | — | — | — | — | 0 | 0 |
| sports/electrolyte drink | US-CA | ≤0.5 | 13 | 4.00 | 0.20 | 0.00 | 0.00 | 0.02 | 13 | 13 |
| sports/electrolyte drink | US-CA | 0.5–5 | 3 | 8.46 | 2.03 | 0.00 | 0.00 | 0.12 | 3 | 3 |
| sports/electrolyte drink | US-CA | ≥5 | 19 | 23.00 | 5.81 | 0.00 | 0.00 | 0.11 | 19 | 19 |
| water: unspecified flavour | FR | ≤0.5 | 1469 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1444 | 1445 |
| water: unspecified flavour | FR | 0.5–5 | 169 | 17.00 | 3.80 | 0.00 | 0.00 | 0.01 | 166 | 167 |
| water: unspecified flavour | FR | ≥5 | 215 | 34.00 | 7.80 | 0.00 | 0.00 | 0.00 | 214 | 212 |
| water: unspecified flavour | UK-IE | ≤0.5 | 145 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 144 | 143 |
| water: unspecified flavour | UK-IE | 0.5–5 | 49 | 17.60 | 3.80 | 0.00 | 0.00 | 0.00 | 48 | 48 |
| water: unspecified flavour | UK-IE | ≥5 | 13 | 30.00 | 7.50 | 0.10 | 0.00 | 0.02 | 13 | 13 |
| water: unspecified flavour | US-CA | ≤0.5 | 174 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 171 | 172 |
| water: unspecified flavour | US-CA | 0.5–5 | 36 | 10.56 | 1.69 | 0.00 | 0.00 | 0.00 | 36 | 35 |
| water: unspecified flavour | US-CA | ≥5 | 16 | 32.35 | 7.37 | 0.00 | 0.00 | 0.03 | 16 | 16 |

</details>

<details><summary>Joint sugar/energy population and sensitivity</summary>

| Form | Region | Restriction | Joint N | ≤0.5 N | ≥5 N | Energy median ≤0.5 | Energy median ≥5 | ≤0.1 N | ≤1 N | Very-low-sugars with energy >20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| alcohol: beer | FR | all | 1096 | 499 | 181 | 45.00 | 32.00 | 378 | 578 | 431 |
| alcohol: beer | FR | Streamlit RTD only | 327 | 172 | 51 | 45.00 | 31.00 | 145 | 196 | 161 |
| alcohol: beer | FR | unshared GTIN | 1078 | 490 | 181 | 45.00 | 32.00 | 371 | 567 | 423 |
| alcohol: beer | UK-IE | all | 141 | 67 | 10 | 39.00 | 33.20 | 48 | 81 | 54 |
| alcohol: beer | UK-IE | Streamlit RTD only | 7 | 3 | 1 | 40.00 | 38.00 | 3 | 4 | 3 |
| alcohol: beer | UK-IE | unshared GTIN | 123 | 58 | 10 | 39.00 | 33.20 | 41 | 70 | 46 |
| alcohol: beer | US-CA | all | 17 | 8 | 5 | 45.00 | 47.89 | 8 | 8 | 6 |
| alcohol: beer | US-CA | Streamlit RTD only | 2 | 1 | 1 | 45.00 | 47.89 | 1 | 1 | 1 |
| alcohol: beer | US-CA | unshared GTIN | 10 | 6 | 2 | 32.92 | 34.50 | 6 | 6 | 4 |
| alcohol: cider | FR | all | 176 | 21 | 100 | 0.00 | 48.90 | 20 | 29 | 4 |
| alcohol: cider | FR | Streamlit RTD only | 8 | 0 | 6 | — | 48.90 | 0 | 0 | 0 |
| alcohol: cider | FR | unshared GTIN | 173 | 21 | 98 | 0.00 | 48.90 | 20 | 29 | 4 |
| alcohol: cider | UK-IE | all | 26 | 2 | 11 | 42.50 | 38.00 | 2 | 2 | 2 |
| alcohol: cider | UK-IE | Streamlit RTD only | 0 | 0 | 0 | — | — | 0 | 0 | 0 |
| alcohol: cider | UK-IE | unshared GTIN | 23 | 2 | 9 | 42.50 | 38.00 | 2 | 2 | 2 |
| alcohol: cider | US-CA | all | 4 | 0 | 2 | — | 218.98 | 0 | 0 | 0 |
| alcohol: cider | US-CA | Streamlit RTD only | 0 | 0 | 0 | — | — | 0 | 0 | 0 |
| alcohol: cider | US-CA | unshared GTIN | 1 | 0 | 1 | — | 57.00 | 0 | 0 | 0 |
| alcohol: cocktail/alcohol-style | FR | all | 12 | 2 | 10 | 0.00 | 49.50 | 2 | 2 | 0 |
| alcohol: cocktail/alcohol-style | FR | Streamlit RTD only | 1 | 0 | 1 | — | 100.00 | 0 | 0 | 0 |
| alcohol: cocktail/alcohol-style | FR | unshared GTIN | 12 | 2 | 10 | 0.00 | 49.50 | 2 | 2 | 0 |
| alcohol: cocktail/alcohol-style | UK-IE | all | 3 | 0 | 2 | — | 29.00 | 0 | 0 | 0 |
| alcohol: cocktail/alcohol-style | UK-IE | Streamlit RTD only | 0 | 0 | 0 | — | — | 0 | 0 | 0 |
| alcohol: cocktail/alcohol-style | UK-IE | unshared GTIN | 3 | 0 | 2 | — | 29.00 | 0 | 0 | 0 |
| alcohol: cocktail/alcohol-style | US-CA | all | 3 | 1 | 0 | 0.00 | — | 1 | 2 | 0 |
| alcohol: cocktail/alcohol-style | US-CA | Streamlit RTD only | 0 | 0 | 0 | — | — | 0 | 0 | 0 |
| alcohol: cocktail/alcohol-style | US-CA | unshared GTIN | 2 | 0 | 0 | — | — | 0 | 1 | 0 |
| alcohol: spirits/liqueurs | FR | all | 112 | 69 | 36 | 220.00 | 182.58 | 67 | 70 | 48 |
| alcohol: spirits/liqueurs | FR | Streamlit RTD only | 0 | 0 | 0 | — | — | 0 | 0 | 0 |
| alcohol: spirits/liqueurs | FR | unshared GTIN | 110 | 67 | 36 | 220.00 | 182.58 | 65 | 68 | 46 |
| alcohol: spirits/liqueurs | UK-IE | all | 17 | 17 | 0 | 242.00 | — | 17 | 17 | 15 |
| alcohol: spirits/liqueurs | UK-IE | Streamlit RTD only | 0 | 0 | 0 | — | — | 0 | 0 | 0 |
| alcohol: spirits/liqueurs | UK-IE | unshared GTIN | 15 | 15 | 0 | 242.00 | — | 15 | 15 | 13 |
| alcohol: spirits/liqueurs | US-CA | all | 8 | 7 | 1 | 195.45 | 392.20 | 6 | 7 | 6 |
| alcohol: spirits/liqueurs | US-CA | Streamlit RTD only | 0 | 0 | 0 | — | — | 0 | 0 | 0 |
| alcohol: spirits/liqueurs | US-CA | unshared GTIN | 6 | 5 | 1 | 95.00 | 392.20 | 4 | 5 | 4 |
| alcohol: wine | FR | all | 798 | 347 | 179 | 85.00 | 73.20 | 276 | 485 | 245 |
| alcohol: wine | FR | Streamlit RTD only | 246 | 116 | 69 | 507.55 | 73.20 | 92 | 154 | 80 |
| alcohol: wine | FR | unshared GTIN | 787 | 343 | 177 | 85.00 | 73.20 | 273 | 481 | 243 |
| alcohol: wine | UK-IE | all | 66 | 20 | 11 | 78.55 | 73.20 | 16 | 26 | 17 |
| alcohol: wine | UK-IE | Streamlit RTD only | 1 | 0 | 0 | — | — | 0 | 0 | 0 |
| alcohol: wine | UK-IE | unshared GTIN | 55 | 16 | 9 | 83.05 | 73.20 | 13 | 22 | 15 |
| alcohol: wine | US-CA | all | 3 | 1 | 1 | 85.00 | 73.33 | 1 | 1 | 1 |
| alcohol: wine | US-CA | Streamlit RTD only | 0 | 0 | 0 | — | — | 0 | 0 | 0 |
| alcohol: wine | US-CA | unshared GTIN | 3 | 1 | 1 | 85.00 | 73.33 | 1 | 1 | 1 |
| coconut water | FR | all | 206 | 4 | 51 | 17.50 | 24.00 | 4 | 5 | 2 |
| coconut water | FR | Streamlit RTD only | 206 | 4 | 51 | 17.50 | 24.00 | 4 | 5 | 2 |
| coconut water | FR | unshared GTIN | 189 | 4 | 49 | 17.50 | 24.00 | 4 | 4 | 2 |
| coconut water | UK-IE | all | 30 | 0 | 3 | — | 26.00 | 0 | 1 | 0 |
| coconut water | UK-IE | Streamlit RTD only | 30 | 0 | 3 | — | 26.00 | 0 | 1 | 0 |
| coconut water | UK-IE | unshared GTIN | 13 | 0 | 1 | — | 38.00 | 0 | 0 | 0 |
| coconut water | US-CA | all | 75 | 2 | 30 | 17.44 | 25.48 | 0 | 2 | 0 |
| coconut water | US-CA | Streamlit RTD only | 75 | 2 | 30 | 17.44 | 25.48 | 0 | 2 | 0 |
| coconut water | US-CA | unshared GTIN | 48 | 2 | 19 | 17.44 | 28.99 | 0 | 2 | 0 |
| energy drink | FR | all | 684 | 151 | 435 | 3.00 | 46.00 | 146 | 153 | 9 |
| energy drink | FR | Streamlit RTD only | 684 | 151 | 435 | 3.00 | 46.00 | 146 | 153 | 9 |
| energy drink | FR | unshared GTIN | 661 | 147 | 426 | 3.00 | 46.00 | 142 | 149 | 9 |
| energy drink | UK-IE | all | 241 | 87 | 81 | 3.00 | 46.00 | 84 | 92 | 2 |
| energy drink | UK-IE | Streamlit RTD only | 241 | 87 | 81 | 3.00 | 46.00 | 84 | 92 | 2 |
| energy drink | UK-IE | unshared GTIN | 218 | 83 | 72 | 3.00 | 46.00 | 80 | 88 | 2 |
| energy drink | US-CA | all | 145 | 97 | 38 | 2.82 | 45.07 | 93 | 99 | 6 |
| energy drink | US-CA | Streamlit RTD only | 145 | 97 | 38 | 2.82 | 45.07 | 93 | 99 | 6 |
| energy drink | US-CA | unshared GTIN | 127 | 92 | 27 | 2.82 | 45.07 | 88 | 93 | 5 |
| fermented soft drink | FR | all | 642 | 69 | 37 | 6.40 | 24.00 | 51 | 72 | 9 |
| fermented soft drink | FR | Streamlit RTD only | 628 | 66 | 37 | 6.40 | 24.00 | 48 | 69 | 9 |
| fermented soft drink | FR | unshared GTIN | 637 | 65 | 37 | 6.40 | 24.00 | 48 | 68 | 9 |
| fermented soft drink | UK-IE | all | 148 | 31 | 1 | 2.73 | 45.00 | 25 | 35 | 0 |
| fermented soft drink | UK-IE | Streamlit RTD only | 144 | 31 | 1 | 2.73 | 45.00 | 25 | 35 | 0 |
| fermented soft drink | UK-IE | unshared GTIN | 143 | 27 | 1 | 2.80 | 45.00 | 22 | 31 | 0 |
| fermented soft drink | US-CA | all | 50 | 4 | 3 | 2.48 | 76.26 | 4 | 7 | 0 |
| fermented soft drink | US-CA | Streamlit RTD only | 48 | 4 | 1 | 2.48 | 76.26 | 4 | 7 | 0 |
| fermented soft drink | US-CA | unshared GTIN | 42 | 3 | 3 | 2.82 | 76.26 | 3 | 6 | 0 |
| flavoured water | FR | all | 335 | 199 | 30 | 0.00 | 28.00 | 186 | 207 | 0 |
| flavoured water | FR | Streamlit RTD only | 331 | 196 | 30 | 0.00 | 28.00 | 183 | 204 | 0 |
| flavoured water | FR | unshared GTIN | 310 | 181 | 27 | 0.00 | 28.00 | 171 | 189 | 0 |
| flavoured water | UK-IE | all | 180 | 135 | 10 | 0.40 | 30.50 | 117 | 137 | 0 |
| flavoured water | UK-IE | Streamlit RTD only | 180 | 135 | 10 | 0.40 | 30.50 | 117 | 137 | 0 |
| flavoured water | UK-IE | unshared GTIN | 155 | 117 | 7 | 0.40 | 30.00 | 102 | 119 | 0 |
| flavoured water | US-CA | all | 66 | 57 | 2 | 0.00 | 77.50 | 57 | 59 | 2 |
| flavoured water | US-CA | Streamlit RTD only | 66 | 57 | 2 | 0.00 | 77.50 | 57 | 59 | 2 |
| flavoured water | US-CA | unshared GTIN | 41 | 35 | 1 | 0.00 | 35.00 | 35 | 37 | 2 |
| fruit drink | FR | all | 99 | 3 | 81 | 41.00 | 44.00 | 1 | 6 | 2 |
| fruit drink | FR | Streamlit RTD only | 99 | 3 | 81 | 41.00 | 44.00 | 1 | 6 | 2 |
| fruit drink | FR | unshared GTIN | 88 | 2 | 74 | 42.50 | 44.00 | 1 | 5 | 2 |
| fruit drink | UK-IE | all | 38 | 6 | 16 | 7.60 | 41.80 | 1 | 8 | 0 |
| fruit drink | UK-IE | Streamlit RTD only | 38 | 6 | 16 | 7.60 | 41.80 | 1 | 8 | 0 |
| fruit drink | UK-IE | unshared GTIN | 27 | 5 | 9 | 11.20 | 39.60 | 1 | 7 | 0 |
| fruit drink | US-CA | all | 31 | 2 | 22 | 19.75 | 41.66 | 1 | 2 | 1 |
| fruit drink | US-CA | Streamlit RTD only | 31 | 2 | 22 | 19.75 | 41.66 | 1 | 2 | 1 |
| fruit drink | US-CA | unshared GTIN | 11 | 2 | 6 | 19.75 | 41.66 | 1 | 2 | 1 |
| iced coffee | FR | all | 10 | 0 | 7 | — | 63.60 | 0 | 0 | 0 |
| iced coffee | FR | Streamlit RTD only | 10 | 0 | 7 | — | 63.60 | 0 | 0 | 0 |
| iced coffee | FR | unshared GTIN | 9 | 0 | 7 | — | 63.60 | 0 | 0 | 0 |
| iced coffee | UK-IE | all | 25 | 3 | 9 | 5.20 | 54.00 | 2 | 3 | 1 |
| iced coffee | UK-IE | Streamlit RTD only | 25 | 3 | 9 | 5.20 | 54.00 | 2 | 3 | 1 |
| iced coffee | UK-IE | unshared GTIN | 24 | 3 | 9 | 5.20 | 54.00 | 2 | 3 | 1 |
| iced coffee | US-CA | all | 26 | 8 | 8 | 4.39 | 58.33 | 7 | 8 | 1 |
| iced coffee | US-CA | Streamlit RTD only | 25 | 8 | 7 | 4.39 | 58.33 | 7 | 8 | 1 |
| iced coffee | US-CA | unshared GTIN | 26 | 8 | 8 | 4.39 | 58.33 | 7 | 8 | 1 |
| iced tea | FR | all | 657 | 68 | 239 | 1.00 | 29.00 | 50 | 71 | 5 |
| iced tea | FR | Streamlit RTD only | 657 | 68 | 239 | 1.00 | 29.00 | 50 | 71 | 5 |
| iced tea | FR | unshared GTIN | 647 | 67 | 237 | 1.00 | 29.00 | 50 | 70 | 5 |
| iced tea | UK-IE | all | 25 | 2 | 4 | 1.48 | 29.50 | 0 | 3 | 0 |
| iced tea | UK-IE | Streamlit RTD only | 25 | 2 | 4 | 1.48 | 29.50 | 0 | 3 | 0 |
| iced tea | UK-IE | unshared GTIN | 15 | 1 | 2 | 0.96 | 29.24 | 0 | 2 | 0 |
| iced tea | US-CA | all | 53 | 7 | 32 | 1.00 | 30.56 | 7 | 8 | 1 |
| iced tea | US-CA | Streamlit RTD only | 53 | 7 | 32 | 1.00 | 30.56 | 7 | 8 | 1 |
| iced tea | US-CA | unshared GTIN | 27 | 4 | 16 | 0.50 | 29.28 | 4 | 5 | 0 |
| juice | FR | all | 7536 | 136 | 6561 | 25.70 | 45.83 | 104 | 193 | 81 |
| juice | FR | Streamlit RTD only | 7119 | 130 | 6199 | 24.20 | 46.00 | 100 | 184 | 77 |
| juice | FR | unshared GTIN | 7383 | 135 | 6422 | 26.00 | 46.00 | 103 | 190 | 81 |
| juice | UK-IE | all | 743 | 24 | 624 | 2.00 | 45.00 | 10 | 37 | 3 |
| juice | UK-IE | Streamlit RTD only | 647 | 15 | 545 | 4.00 | 45.00 | 8 | 26 | 3 |
| juice | UK-IE | unshared GTIN | 590 | 23 | 485 | 2.00 | 45.00 | 9 | 34 | 3 |
| juice | US-CA | all | 318 | 15 | 268 | 1.88 | 46.00 | 14 | 16 | 2 |
| juice | US-CA | Streamlit RTD only | 291 | 14 | 243 | 0.94 | 46.00 | 13 | 14 | 1 |
| juice | US-CA | unshared GTIN | 193 | 11 | 161 | 2.08 | 45.83 | 10 | 12 | 2 |
| nectar | FR | all | 1759 | 11 | 1682 | 46.00 | 48.00 | 11 | 12 | 11 |
| nectar | FR | Streamlit RTD only | 1623 | 11 | 1561 | 46.00 | 48.00 | 11 | 12 | 11 |
| nectar | FR | unshared GTIN | 1756 | 11 | 1679 | 46.00 | 48.00 | 11 | 12 | 11 |
| nectar | UK-IE | all | 12 | 1 | 8 | 2.00 | 41.50 | 0 | 3 | 0 |
| nectar | UK-IE | Streamlit RTD only | 6 | 0 | 4 | — | 53.50 | 0 | 1 | 0 |
| nectar | UK-IE | unshared GTIN | 9 | 1 | 5 | 2.00 | 52.00 | 0 | 3 | 0 |
| nectar | US-CA | all | 36 | 0 | 36 | — | 58.67 | 0 | 0 | 0 |
| nectar | US-CA | Streamlit RTD only | 34 | 0 | 34 | — | 58.67 | 0 | 0 | 0 |
| nectar | US-CA | unshared GTIN | 26 | 0 | 26 | — | 60.30 | 0 | 0 | 0 |
| plant drink: almond | FR | all | 293 | 119 | 54 | 25.00 | 59.50 | 59 | 120 | 79 |
| plant drink: almond | FR | Streamlit RTD only | 288 | 117 | 53 | 25.00 | 59.00 | 57 | 118 | 78 |
| plant drink: almond | FR | unshared GTIN | 283 | 112 | 53 | 25.00 | 60.00 | 56 | 113 | 75 |
| plant drink: almond | UK-IE | all | 51 | 33 | 2 | 18.00 | 55.00 | 12 | 33 | 10 |
| plant drink: almond | UK-IE | Streamlit RTD only | 49 | 33 | 2 | 18.00 | 55.00 | 12 | 33 | 10 |
| plant drink: almond | UK-IE | unshared GTIN | 41 | 26 | 1 | 17.50 | 62.00 | 9 | 26 | 6 |
| plant drink: almond | US-CA | all | 60 | 32 | 14 | 14.89 | 58.70 | 26 | 33 | 10 |
| plant drink: almond | US-CA | Streamlit RTD only | 56 | 30 | 14 | 14.58 | 58.70 | 24 | 31 | 9 |
| plant drink: almond | US-CA | unshared GTIN | 43 | 24 | 9 | 14.58 | 41.67 | 20 | 25 | 7 |
| plant drink: coconut | FR | all | 29 | 11 | 4 | 34.00 | 80.00 | 7 | 13 | 7 |
| plant drink: coconut | FR | Streamlit RTD only | 16 | 9 | 2 | 33.00 | 80.00 | 5 | 10 | 5 |
| plant drink: coconut | FR | unshared GTIN | 27 | 11 | 4 | 34.00 | 80.00 | 7 | 13 | 7 |
| plant drink: coconut | UK-IE | all | 13 | 3 | 1 | 19.00 | 503.00 | 0 | 3 | 1 |
| plant drink: coconut | UK-IE | Streamlit RTD only | 7 | 1 | 0 | 19.00 | — | 0 | 1 | 0 |
| plant drink: coconut | UK-IE | unshared GTIN | 11 | 3 | 1 | 19.00 | 503.00 | 0 | 3 | 1 |
| plant drink: coconut | US-CA | all | 10 | 6 | 1 | 27.15 | 90.00 | 2 | 6 | 4 |
| plant drink: coconut | US-CA | Streamlit RTD only | 6 | 3 | 1 | 21.00 | 90.00 | 1 | 3 | 2 |
| plant drink: coconut | US-CA | unshared GTIN | 7 | 4 | 0 | 27.15 | — | 1 | 4 | 3 |
| plant drink: oat | FR | all | 10 | 1 | 2 | 29.00 | 63.00 | 0 | 1 | 1 |
| plant drink: oat | FR | Streamlit RTD only | 5 | 0 | 1 | — | 73.00 | 0 | 0 | 0 |
| plant drink: oat | FR | unshared GTIN | 10 | 1 | 2 | 29.00 | 63.00 | 0 | 1 | 1 |
| plant drink: oat | UK-IE | all | 3 | 0 | 0 | — | — | 0 | 0 | 0 |
| plant drink: oat | UK-IE | Streamlit RTD only | 3 | 0 | 0 | — | — | 0 | 0 | 0 |
| plant drink: oat | UK-IE | unshared GTIN | 3 | 0 | 0 | — | — | 0 | 0 | 0 |
| plant drink: oat | US-CA | all | 4 | 1 | 0 | 29.00 | — | 0 | 1 | 1 |
| plant drink: oat | US-CA | Streamlit RTD only | 1 | 0 | 0 | — | — | 0 | 0 | 0 |
| plant drink: oat | US-CA | unshared GTIN | 3 | 0 | 0 | — | — | 0 | 0 | 0 |
| plant drink: rice | FR | all | 7 | 0 | 5 | — | 61.00 | 0 | 0 | 0 |
| plant drink: rice | FR | Streamlit RTD only | 7 | 0 | 5 | — | 61.00 | 0 | 0 | 0 |
| plant drink: rice | FR | unshared GTIN | 7 | 0 | 5 | — | 61.00 | 0 | 0 | 0 |
| plant drink: rice | UK-IE | all | 1 | 0 | 0 | — | — | 0 | 0 | 0 |
| plant drink: rice | UK-IE | Streamlit RTD only | 1 | 0 | 0 | — | — | 0 | 0 | 0 |
| plant drink: rice | UK-IE | unshared GTIN | 1 | 0 | 0 | — | — | 0 | 0 | 0 |
| plant drink: soy | FR | all | 253 | 42 | 82 | 35.50 | 64.50 | 10 | 78 | 41 |
| plant drink: soy | FR | Streamlit RTD only | 249 | 42 | 82 | 35.50 | 64.50 | 10 | 76 | 41 |
| plant drink: soy | FR | unshared GTIN | 238 | 37 | 78 | 36.00 | 65.50 | 7 | 72 | 37 |
| plant drink: soy | UK-IE | all | 78 | 33 | 12 | 32.00 | 63.60 | 15 | 38 | 29 |
| plant drink: soy | UK-IE | Streamlit RTD only | 78 | 33 | 12 | 32.00 | 63.60 | 15 | 38 | 29 |
| plant drink: soy | UK-IE | unshared GTIN | 63 | 28 | 8 | 32.00 | 67.00 | 12 | 32 | 25 |
| plant drink: soy | US-CA | all | 20 | 6 | 5 | 36.67 | 90.00 | 1 | 7 | 6 |
| plant drink: soy | US-CA | Streamlit RTD only | 17 | 5 | 5 | 40.00 | 90.00 | 0 | 5 | 5 |
| plant drink: soy | US-CA | unshared GTIN | 16 | 6 | 3 | 36.67 | 90.00 | 1 | 6 | 6 |
| smoothie | FR | all | 517 | 5 | 496 | 54.00 | 54.83 | 4 | 5 | 5 |
| smoothie | FR | Streamlit RTD only | 473 | 5 | 452 | 54.00 | 54.83 | 4 | 5 | 5 |
| smoothie | FR | unshared GTIN | 488 | 5 | 467 | 54.00 | 54.00 | 4 | 5 | 5 |
| smoothie | UK-IE | all | 159 | 0 | 154 | — | 52.83 | 0 | 2 | 0 |
| smoothie | UK-IE | Streamlit RTD only | 123 | 0 | 119 | — | 52.00 | 0 | 1 | 0 |
| smoothie | UK-IE | unshared GTIN | 130 | 0 | 125 | — | 52.00 | 0 | 2 | 0 |
| smoothie | US-CA | all | 57 | 1 | 50 | 46.36 | 62.81 | 1 | 1 | 1 |
| smoothie | US-CA | Streamlit RTD only | 47 | 1 | 40 | 46.36 | 64.31 | 1 | 1 | 1 |
| smoothie | US-CA | unshared GTIN | 46 | 1 | 39 | 46.36 | 65.00 | 1 | 1 | 1 |
| soda | FR | all | 3457 | 710 | 2346 | 0.60 | 38.00 | 597 | 728 | 23 |
| soda | FR | Streamlit RTD only | 3444 | 709 | 2338 | 0.60 | 38.00 | 596 | 727 | 23 |
| soda | FR | unshared GTIN | 3326 | 669 | 2300 | 0.50 | 38.00 | 565 | 686 | 23 |
| soda | UK-IE | all | 640 | 255 | 156 | 1.00 | 39.22 | 200 | 265 | 1 |
| soda | UK-IE | Streamlit RTD only | 639 | 255 | 156 | 1.00 | 39.22 | 200 | 265 | 1 |
| soda | UK-IE | unshared GTIN | 509 | 214 | 110 | 1.00 | 38.50 | 168 | 223 | 1 |
| soda | US-CA | all | 418 | 95 | 239 | 0.00 | 43.99 | 86 | 110 | 3 |
| soda | US-CA | Streamlit RTD only | 417 | 95 | 239 | 0.00 | 43.99 | 86 | 110 | 3 |
| soda | US-CA | unshared GTIN | 299 | 72 | 148 | 0.00 | 44.63 | 63 | 86 | 2 |
| sports/electrolyte drink | FR | all | 32 | 6 | 14 | 4.61 | 23.84 | 5 | 6 | 1 |
| sports/electrolyte drink | FR | Streamlit RTD only | 32 | 6 | 14 | 4.61 | 23.84 | 5 | 6 | 1 |
| sports/electrolyte drink | FR | unshared GTIN | 32 | 6 | 14 | 4.61 | 23.84 | 5 | 6 | 1 |
| sports/electrolyte drink | UK-IE | all | 8 | 5 | 0 | 4.00 | — | 0 | 5 | 0 |
| sports/electrolyte drink | UK-IE | Streamlit RTD only | 8 | 5 | 0 | 4.00 | — | 0 | 5 | 0 |
| sports/electrolyte drink | UK-IE | unshared GTIN | 8 | 5 | 0 | 4.00 | — | 0 | 5 | 0 |
| sports/electrolyte drink | US-CA | all | 35 | 13 | 19 | 4.00 | 23.00 | 6 | 13 | 0 |
| sports/electrolyte drink | US-CA | Streamlit RTD only | 35 | 13 | 19 | 4.00 | 23.00 | 6 | 13 | 0 |
| sports/electrolyte drink | US-CA | unshared GTIN | 24 | 10 | 12 | 4.00 | 23.00 | 4 | 10 | 0 |
| water: unspecified flavour | FR | all | 1824 | 1444 | 214 | 0.00 | 34.00 | 1414 | 1454 | 33 |
| water: unspecified flavour | FR | Streamlit RTD only | 1658 | 1317 | 202 | 0.00 | 34.00 | 1290 | 1326 | 29 |
| water: unspecified flavour | FR | unshared GTIN | 1764 | 1397 | 210 | 0.00 | 34.00 | 1371 | 1407 | 31 |
| water: unspecified flavour | UK-IE | all | 205 | 144 | 13 | 0.00 | 30.00 | 133 | 150 | 4 |
| water: unspecified flavour | UK-IE | Streamlit RTD only | 171 | 127 | 12 | 0.00 | 30.00 | 117 | 132 | 3 |
| water: unspecified flavour | UK-IE | unshared GTIN | 145 | 97 | 9 | 0.70 | 28.00 | 90 | 103 | 2 |
| water: unspecified flavour | US-CA | all | 223 | 171 | 16 | 0.00 | 32.35 | 160 | 183 | 5 |
| water: unspecified flavour | US-CA | Streamlit RTD only | 170 | 135 | 8 | 0.00 | 36.16 | 128 | 145 | 4 |
| water: unspecified flavour | US-CA | unshared GTIN | 152 | 108 | 12 | 0.00 | 32.35 | 100 | 120 | 3 |

</details>

<details><summary>Plant-base protein evidence</summary>

| Form | Region | Assignments | Valid protein | Protein ≥2 N | Valid protein and energy ≥10 | Zero-energy denominator | 0<E<10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| plant drink: almond | FR | 307 | 298 | 19 | 297 | 0 | 0 |
| plant drink: almond | UK-IE | 56 | 54 | 0 | 53 | 0 | 0 |
| plant drink: almond | US-CA | 413 | 63 | 8 | 63 | 0 | 0 |
| plant drink: coconut | FR | 31 | 29 | 1 | 29 | 0 | 0 |
| plant drink: coconut | UK-IE | 13 | 13 | 1 | 13 | 0 | 0 |
| plant drink: coconut | US-CA | 38 | 11 | 3 | 11 | 0 | 0 |
| plant drink: oat | FR | 10 | 10 | 2 | 10 | 0 | 0 |
| plant drink: oat | UK-IE | 5 | 5 | 0 | 5 | 0 | 0 |
| plant drink: oat | US-CA | 31 | 5 | 0 | 5 | 0 | 0 |
| plant drink: rice | FR | 9 | 7 | 0 | 7 | 0 | 0 |
| plant drink: rice | UK-IE | 1 | 1 | 0 | 1 | 0 | 0 |
| plant drink: rice | US-CA | 19 | 0 | 0 | 0 | 0 | 0 |
| plant drink: soy | FR | 282 | 255 | 247 | 253 | 0 | 0 |
| plant drink: soy | UK-IE | 80 | 79 | 78 | 79 | 0 | 0 |
| plant drink: soy | US-CA | 112 | 20 | 19 | 20 | 0 | 0 |

</details>

<details><summary>Product examples</summary>

| Form | Region | Example | Text GTIN | Recorded name | Sugars | Energy |
| --- | --- | --- | --- | --- | --- | --- |
| energy drink | FR | typical very-low sugars | 0070847002901 | Monster Energy Zero Sugar | 0.00 | 2.11 |
| energy drink | FR | near inside | 20063825 | Boisson speedstar energy drink | 0.50 | 333.00 |
| energy drink | FR | near outside | 0070847006145 | Energy drink | 0.83 | 4.00 |
| energy drink | FR | typical higher sugars | 05245383 | Red Bull | 11.00 | 46.00 |
| energy drink | UK-IE | typical very-low sugars | 0810116123186 | PRIME Original Flavour Energy Drink | 0.00 | 2.00 |
| energy drink | UK-IE | near inside | 25357639 | Zero Blast Zero Sugar Energy Drink | 0.50 | 4.00 |
| energy drink | UK-IE | near outside | 5000382104476 | Rock star orange clémentine | 0.60 | 5.00 |
| energy drink | UK-IE | typical higher sugars | 2098765839100 | REV UP Cranberry Taste | 11.00 | 45.00 |
| iced tea | FR | typical very-low sugars | 0000230003170 | ICE TEA | 0.00 | 0.00 |
| iced tea | FR | near inside | 3228886049679 | Lipton Ice Tea Saveur Pêche Zéro Sucres 1,5 L | 0.50 | 1.00 |
| iced tea | FR | near outside | 6091307111364 | Bois cheri ice tea | 0.53 | 28.00 |
| iced tea | FR | typical higher sugars | 0069000008140 | Pomegranate iced tea | 7.00 | 28.00 |
| soda | FR | typical very-low sugars | 0016571951580 | Cherry Limeade Sparkling Ice | 0.00 | 0.00 |
| soda | FR | near inside | 3057640217913 | Fiz Citron Vert | 0.50 | 4.00 |
| soda | FR | near outside | 3057640189708 | Taillefine Fiz Fruits Rouges | 0.60 | 8.90 |
| soda | FR | typical higher sugars | 0090478000749 | Lime | 9.00 | 38.00 |
| soda | UK-IE | typical very-low sugars | 0004900002898 | Coke cola diet | 0.00 | 0.00 |
| soda | UK-IE | near inside | 00154635 | Bitter lemon | 0.50 | 12.00 |
| soda | UK-IE | near outside | 4056489864363 | Carbonated no added sugar orange flavour soft drink with sweetener. | 0.52 | 2.12 |
| soda | UK-IE | typical higher sugars | 50303861 | Britvic spicy Ginger Ale | 9.10 | 38.00 |

</details>
