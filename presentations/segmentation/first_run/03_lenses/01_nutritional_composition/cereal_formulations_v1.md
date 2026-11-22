# Cereal formulation follow-up · Wave 2

**Decision. Retain one descriptive granola profile and stop at commercial format for flakes.** The granola rule identifies individual products at one end of a recurring nutritional gradient. The evidence does not establish a discrete segment boundary in either format.

| Candidate granola definition, per 100 g | Format assignments | Both measurements valid | Qualifying products | Share of measurable |
|---|---:|---:|---:|---:|
| France · sugars ≤14 g and protein ≥11 g | 1,552 | 1,445 | 251 | 17.4% |
| UK/Ireland · same rule | 395 | 377 | 94 | 24.9% |
| US/Canada · exploratory | 2,009 | 948 | 121 | 12.8% |

The two thresholds are French format quartiles, chosen here as research cutoffs. A product can be classified from its own two measurements, including when energy or fibre is missing. Two examples close to the regional medians among qualifiers are Granola Columbus in France (GTIN 3700994200680, 11.2 g sugars and 12.3 g protein) and Grains & Seeds Granola in UK/Ireland (5057008100909, 9.8 g and 12.9 g). These are measured attributes. Pack claims and NOVA play no role in assignment.

**Why granola merits a profile.** Among energy-matched pairs with a sugar gap of at least 5 g, the lower-sugar member also had higher protein **and** lower total carbohydrate in 58% of measurable French pairs and 73% of UK/Irish pairs, versus 26% and 31% in the smaller-gap comparison. Median protein differences were +1.6 and +2.0 g/100 g. Fat and available fibre also tended to be higher. These directions survived alternative matching orders and energy tolerances. The selected US/Canadian pairs showed the same directions. Fibre remains descriptive because requiring it would lose measurable products.

**Why stop at one descriptive rule.** In France, median protein across ascending granola sugar bands fell progressively from 11.0 to 9.9, 9.1 and 8.3 g/100 g. UK/Ireland showed the same progression. The number qualifying also shifts with the chosen quartiles. The data support a recognizable end of a gradient; a natural dividing line remains unestablished. The fat and fibre screens below overlap with the protein screen and do not justify additional segment names. Granola flavour cues are incomplete, so the contribution of product mix remains open.

**Why stop for flakes.** With large sugar gaps, median total carbohydrate differences were −0.6 g/100 g in France and 0.0 in UK/Ireland, with substantial variation on either side. Protein differences were small, and neither fat nor fibre showed a consistent compensating shift. Commercial wording mattered: 31/48 French pairs with different detected flake descriptions had large sugar gaps versus 34/125 with matching descriptions. In UK/Ireland the counts were 8/8 versus 10/41. Many pairs had insufficient wording (242/415 French pairs and 55/104 UK/Irish pairs). This flags commercial mix as an explanation without establishing that frosted versus plain explains most gaps. Retain flakes as the format and report the sugar spread.

**Scope and interpretation.** The [builder](cereal_formulations_v1.py) verifies the frozen cereal input and reproduces all six approved H2 pair counts and large-gap counts from the [original results](hypothesis_results_v1.csv). The corpus contains 5,829 candidate assignments, 4,230 valid energy–sugars observations and 2,095 disjoint pairs. Paired differences are descriptive, conditional on comparable energy. Regional carbohydrate values and their calculated remainders retain the recorded basis. Neither the associations nor the remainder identify a recipe substitution. Coverage describes observed products in each region, with particularly strong selection in US/Canada.

<!-- generated evidence -->

## Matched pairs

Differences are lower-sugar minus higher-sugar, in g/100 g. Each cell gives median [Q1, Q3] and paired measurement count. The <5 g group includes exact sugar ties, whose ordering follows the energy/GTIN sort. Remainder is total carbohydrate minus sugars on coherent measurements. Interpret within region only. It is mathematically coupled to the sugar gap and cannot identify starch or ingredient substitution.

| Format | Region | Sugar gap | Pairs | Protein | Fat | Carbohydrate | Fibre | Remainder |
|---|---|---|---|---|---|---|---|---|
| FLAKES | FR | ≥5 | 217 | +0.5 [-1.3, +2.7] (217) | -0.3 [-2.0, +0.9] (217) | -0.6 [-6.2, +6.8] (217) | -0.3 [-3.2, +2.5] (155) | +14.0 [+6.5, +22.5] (217) |
| FLAKES | FR | <5 | 198 | +0.0 [-0.2, +0.1] (198) | +0.0 [-0.1, +0.0] (197) | +0.0 [+0.0, +1.0] (197) | +0.0 [-1.0, +0.3] (132) | +0.0 [+0.0, +3.0] (197) |
| FLAKES | UK-IE | ≥5 | 53 | +0.7 [-0.6, +2.0] (53) | +0.0 [-2.2, +0.7] (53) | +0.0 [-4.2, +5.9] (52) | -0.2 [-4.1, +4.0] (44) | +14.2 [+6.4, +21.6] (52) |
| FLAKES | UK-IE | <5 | 51 | +0.0 [-0.1, +0.0] (51) | +0.0 [-0.1, +0.0] (51) | +0.0 [+0.0, +0.0] (51) | +0.0 [-1.4, +0.0] (42) | +0.0 [+0.0, +1.6] (51) |
| FLAKES | US-CA | ≥5 | 93 | +0.0 [-1.2, +2.5] (93) | +0.0 [-1.3, +1.8] (93) | -3.5 [-7.9, +0.0] (91) | +0.0 [-5.0, +4.1] (80) | +13.0 [+5.6, +17.6] (91) |
| FLAKES | US-CA | <5 | 116 | +0.0 [+0.0, +0.0] (116) | +0.0 [+0.0, +0.0] (115) | +0.0 [-0.6, +0.0] (116) | +0.0 [+0.0, +0.3] (93) | +0.0 [+0.0, +0.0] (116) |
| GRANOLA | FR | ≥5 | 315 | +1.6 [+0.0, +3.7] (314) | +1.0 [-0.9, +3.9] (315) | -5.8 [-13.2, -0.8] (314) | +1.5 [-0.1, +3.2] (238) | +4.0 [-2.8, +8.5] (314) |
| GRANOLA | FR | <5 | 400 | +0.0 [-0.6, +1.1] (400) | +0.0 [-1.0, +1.3] (399) | +0.0 [-4.1, +2.0] (399) | +0.0 [-0.7, +1.0] (293) | +0.0 [-2.0, +4.0] (399) |
| GRANOLA | UK-IE | ≥5 | 93 | +2.0 [+0.5, +4.1] (93) | +1.4 [+0.0, +3.3] (93) | -6.7 [-14.0, -2.8] (93) | +1.9 [+0.2, +3.8] (77) | +3.5 [-2.2, +8.4] (93) |
| GRANOLA | UK-IE | <5 | 91 | +0.0 [-1.1, +0.8] (91) | +0.0 [-1.2, +1.2] (91) | +0.0 [-3.7, +2.1] (91) | +0.0 [-1.0, +1.1] (82) | +1.3 [-2.5, +4.8] (91) |
| GRANOLA | US-CA | ≥5 | 241 | +1.8 [+0.0, +4.9] (241) | +3.1 [-1.2, +7.1] (241) | -7.7 [-17.9, +0.0] (240) | +1.0 [-1.1, +3.3] (195) | +1.9 [-7.1, +8.8] (240) |
| GRANOLA | US-CA | <5 | 227 | +0.0 [-0.7, +1.7] (227) | +0.0 [-1.8, +2.5] (227) | +0.0 [-3.6, +3.3] (223) | +0.0 [-0.7, +1.0] (177) | +0.0 [-1.7, +5.2] (223) |

## Joint direction on the same pairs

Count of pairs where the lower-sugar member has both strictly higher protein and strictly lower total carbohydrate. Small nonzero differences count here; magnitude is reported above.

| Format | Region | Sugar gap | Measurable | Both differences | Share |
|---|---|---|---|---|---|
| FLAKES | FR | ≥5 | 217 | 98 | 45.2% |
| FLAKES | FR | <5 | 197 | 32 | 16.2% |
| FLAKES | UK-IE | ≥5 | 52 | 22 | 42.3% |
| FLAKES | UK-IE | <5 | 51 | 6 | 11.8% |
| FLAKES | US-CA | ≥5 | 91 | 32 | 35.2% |
| FLAKES | US-CA | <5 | 116 | 15 | 12.9% |
| GRANOLA | FR | ≥5 | 314 | 182 | 58.0% |
| GRANOLA | FR | <5 | 399 | 104 | 26.1% |
| GRANOLA | UK-IE | ≥5 | 93 | 68 | 73.1% |
| GRANOLA | UK-IE | <5 | 91 | 28 | 30.8% |
| GRANOLA | US-CA | ≥5 | 240 | 130 | 54.2% |
| GRANOLA | US-CA | <5 | 223 | 55 | 24.7% |

## Commercial wording

Compare the fraction of pairs with a large sugar gap within each wording group. Same means identical detected cue sets on both products. Unknown includes any pair with an uncued member. The screen uses product names and OFF tags; plain and unlabelled cannot be distinguished reliably.

| Format | Region | Wording | Pairs | Gap ≥5 | Share | Carbohydrate difference among large gaps |
|---|---|---|---|---|---|---|
| FLAKES | FR | different | 48 | 31 | 65% | -1.8 [-7.1, +3.8] (31) |
| FLAKES | FR | same | 125 | 34 | 27% | -1.0 [-2.4, +1.5] (34) |
| FLAKES | FR | unknown | 242 | 152 | 63% | +0.8 [-7.0, +7.9] (152) |
| FLAKES | UK-IE | different | 8 | 8 | 100% | -2.1 [-13.5, +0.5] (7) |
| FLAKES | UK-IE | same | 41 | 10 | 24% | -0.4 [-1.1, +0.5] (10) |
| FLAKES | UK-IE | unknown | 55 | 35 | 64% | +1.9 [-4.5, +14.6] (35) |
| FLAKES | US-CA | different | 51 | 40 | 78% | -3.0 [-7.2, +0.0] (40) |
| FLAKES | US-CA | same | 90 | 18 | 20% | +0.0 [-5.0, +0.2] (18) |
| FLAKES | US-CA | unknown | 68 | 35 | 51% | -10.0 [-15.2, -1.2] (33) |
| GRANOLA | FR | different | 91 | 44 | 48% | -6.0 [-12.9, -0.2] (44) |
| GRANOLA | FR | same | 86 | 27 | 31% | -3.0 [-6.7, +0.8] (27) |
| GRANOLA | FR | unknown | 538 | 244 | 45% | -6.0 [-13.8, -1.0] (243) |
| GRANOLA | UK-IE | different | 25 | 9 | 36% | -6.8 [-17.3, -3.0] (9) |
| GRANOLA | UK-IE | same | 18 | 9 | 50% | -6.7 [-11.9, -4.7] (9) |
| GRANOLA | UK-IE | unknown | 141 | 75 | 53% | -6.6 [-13.7, -2.6] (75) |
| GRANOLA | US-CA | different | 54 | 34 | 63% | -6.9 [-14.4, -0.0] (34) |
| GRANOLA | US-CA | same | 37 | 14 | 38% | -4.1 [-12.3, -0.4] (14) |
| GRANOLA | US-CA | unknown | 377 | 193 | 51% | -8.2 [-19.8, -0.6] (192) |

## Matching sensitivity

Range of median differences among large-gap pairs across forward/reverse matching at 5, 10 and 20 kcal/100 g.

| Format | Region | Protein | Fat | Carbohydrate | Fibre |
|---|---|---|---|---|---|
| FLAKES | FR | +0.5 to +0.5 | -0.3 to -0.3 | -0.6 to -0.6 | -0.3 to -0.3 |
| FLAKES | UK-IE | +0.7 to +1.0 | -0.2 to +0.0 | +0.0 to +0.0 | -0.2 to +0.3 |
| FLAKES | US-CA | +0.0 to +1.9 | +0.0 to +0.0 | -3.5 to -2.5 | +0.0 to +0.0 |
| GRANOLA | FR | +1.6 to +1.6 | +0.9 to +1.0 | -5.8 to -5.4 | +1.4 to +1.6 |
| GRANOLA | UK-IE | +1.8 to +2.0 | +0.9 to +1.4 | -7.2 to -6.7 | +1.6 to +2.1 |
| GRANOLA | US-CA | +1.7 to +1.8 | +2.0 to +3.2 | -7.8 to -7.5 | +0.5 to +1.0 |

## Candidate individual-product definitions and coverage

Each screen requires sugars at or below the French format Q1 and the named nutrient at or above its French format Q3, both in g/100 g. Cutoffs use French products measurable on those two fields, including products without energy. Apply full-precision French cutoffs unchanged within each format. Rows overlap. Share uses measurable products. Sensitivity tightens both tails to 20% or widens both to 30%. US/Canada coverage is exploratory, especially for carbohydrates.

| Format | Region | Higher nutrient | Sugar / nutrient cutoff | Format N | Measurable | Qualify | Share | Sensitivity |
|---|---|---|---|---|---|---|---|---|
| FLAKES | FR | protein | ≤7.00 / ≥9.00 | 902 | 837 | 46 | 5.5% | 4.9–6.1% |
| FLAKES | FR | fat | ≤7.00 / ≥3.62 | 902 | 836 | 13 | 1.6% | 1.0–3.2% |
| FLAKES | FR | carbs | ≤7.00 / ≥83.83 | 902 | 836 | 44 | 5.3% | 4.1–16.0% |
| FLAKES | FR | fibre | ≤7.60 / ≥7.10 | 902 | 689 | 31 | 4.5% | 4.2–5.5% |
| FLAKES | UK-IE | protein | ≤7.00 / ≥9.00 | 228 | 215 | 13 | 6.0% | 5.6–7.0% |
| FLAKES | UK-IE | fat | ≤7.00 / ≥3.62 | 228 | 215 | 1 | 0.5% | 0.5–1.4% |
| FLAKES | UK-IE | carbs | ≤7.00 / ≥83.83 | 228 | 214 | 20 | 9.3% | 2.8–17.8% |
| FLAKES | UK-IE | fibre | ≤7.60 / ≥7.10 | 228 | 195 | 12 | 6.2% | 5.1–7.2% |
| FLAKES | US-CA | protein | ≤7.00 / ≥9.00 | 743 | 428 | 7 | 1.6% | 1.6–2.3% |
| FLAKES | US-CA | fat | ≤7.00 / ≥3.62 | 743 | 427 | 6 | 1.4% | 1.2–1.6% |
| FLAKES | US-CA | carbs | ≤7.00 / ≥83.83 | 743 | 426 | 14 | 3.3% | 1.4–6.6% |
| FLAKES | US-CA | fibre | ≤7.60 / ≥7.10 | 743 | 389 | 7 | 1.8% | 1.5–2.6% |
| GRANOLA | FR | protein | ≤14.00 / ≥11.00 | 1552 | 1445 | 251 | 17.4% | 10.6–19.7% |
| GRANOLA | FR | fat | ≤14.00 / ≥19.00 | 1552 | 1445 | 150 | 10.4% | 6.8–13.8% |
| GRANOLA | FR | carbs | ≤14.00 / ≥65.00 | 1552 | 1444 | 33 | 2.3% | 1.2–3.2% |
| GRANOLA | FR | fibre | ≤14.00 / ≥8.80 | 1552 | 1240 | 177 | 14.3% | 9.4–17.6% |
| GRANOLA | UK-IE | protein | ≤14.00 / ≥11.00 | 395 | 377 | 94 | 24.9% | 20.2–29.2% |
| GRANOLA | UK-IE | fat | ≤14.00 / ≥19.00 | 395 | 377 | 69 | 18.3% | 15.1–22.5% |
| GRANOLA | UK-IE | carbs | ≤14.00 / ≥65.00 | 395 | 377 | 5 | 1.3% | 0.8–2.9% |
| GRANOLA | UK-IE | fibre | ≤14.00 / ≥8.80 | 395 | 350 | 68 | 19.4% | 17.1–22.6% |
| GRANOLA | US-CA | protein | ≤14.00 / ≥11.00 | 2009 | 948 | 121 | 12.8% | 9.4–14.9% |
| GRANOLA | US-CA | fat | ≤14.00 / ≥19.00 | 2009 | 948 | 117 | 12.3% | 9.3–14.9% |
| GRANOLA | US-CA | carbs | ≤14.00 / ≥65.00 | 2009 | 943 | 20 | 2.1% | 1.4–3.5% |
| GRANOLA | US-CA | fibre | ≤14.00 / ≥8.80 | 2009 | 848 | 92 | 10.8% | 8.0–12.9% |

## Individual-product gradient

Products grouped by the three French format sugar quartiles from lowest to highest. Each nutrient column is the median of its observed values in that band. These bands describe variation and are not proposed classes.

| Format | Region | Sugar band | N | Sugars | Protein | Fat | Carbohydrate | Fibre |
|---|---|---|---|---|---|---|---|---|
| FLAKES | FR | 1 | 221 | 4.5 | 8.0 | 1.0 | 81.3 | 3.5 |
| FLAKES | FR | 2 | 200 | 9.4 | 8.0 | 1.3 | 81.4 | 4.8 |
| FLAKES | FR | 3 | 217 | 18.0 | 8.3 | 3.0 | 77.0 | 5.7 |
| FLAKES | FR | 4 | 199 | 27.0 | 7.3 | 2.8 | 80.0 | 3.9 |
| FLAKES | UK-IE | 1 | 44 | 5.0 | 7.7 | 1.2 | 82.3 | 4.9 |
| FLAKES | UK-IE | 2 | 72 | 10.7 | 8.2 | 2.2 | 74.9 | 8.9 |
| FLAKES | UK-IE | 3 | 46 | 18.2 | 8.0 | 1.9 | 77.8 | 6.4 |
| FLAKES | UK-IE | 4 | 53 | 27.8 | 7.3 | 4.5 | 82.0 | 2.5 |
| FLAKES | US-CA | 1 | 37 | 4.0 | 7.0 | 1.0 | 81.1 | 3.3 |
| FLAKES | US-CA | 2 | 116 | 10.0 | 7.3 | 0.0 | 80.0 | 2.5 |
| FLAKES | US-CA | 3 | 61 | 16.7 | 10.3 | 2.6 | 79.5 | 12.3 |
| FLAKES | US-CA | 4 | 216 | 32.4 | 5.4 | 1.1 | 86.5 | 4.9 |
| GRANOLA | FR | 1 | 399 | 11.8 | 11.0 | 16.7 | 52.0 | 8.8 |
| GRANOLA | FR | 2 | 347 | 16.7 | 9.9 | 16.0 | 61.0 | 7.7 |
| GRANOLA | FR | 3 | 395 | 20.0 | 9.1 | 16.0 | 63.0 | 7.0 |
| GRANOLA | FR | 4 | 305 | 24.6 | 8.3 | 16.0 | 64.0 | 6.8 |
| GRANOLA | UK-IE | 1 | 146 | 9.7 | 11.6 | 18.0 | 50.6 | 8.8 |
| GRANOLA | UK-IE | 2 | 109 | 16.4 | 10.6 | 15.0 | 61.6 | 6.9 |
| GRANOLA | UK-IE | 3 | 84 | 20.1 | 9.9 | 13.4 | 64.0 | 6.4 |
| GRANOLA | UK-IE | 4 | 38 | 24.9 | 8.8 | 13.9 | 63.5 | 6.1 |
| GRANOLA | US-CA | 1 | 216 | 8.8 | 12.0 | 21.2 | 37.0 | 8.7 |
| GRANOLA | US-CA | 2 | 171 | 16.7 | 10.7 | 17.9 | 58.6 | 7.2 |
| GRANOLA | US-CA | 3 | 249 | 20.0 | 10.0 | 16.4 | 65.0 | 7.1 |
| GRANOLA | US-CA | 4 | 313 | 25.0 | 9.1 | 14.3 | 69.8 | 6.7 |
