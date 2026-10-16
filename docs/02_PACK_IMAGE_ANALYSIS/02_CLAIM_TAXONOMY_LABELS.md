# UI display labels

This document is the canonical mapping from stored taxonomy codes
(`claim_category_1`, `claim_category_2` in `product_analysis` — see
`docs/03_PROJECT_REFERENCE/04_DATA_DICTIONARY.md`) to the display labels used in the
Streamlit app.

**Why this file exists:** the stored codes (`FUNCTIONAL`, `no_added_x`,
etc.) are deliberately short, stable, and rename-resistant for use as
database values, filter keys, and join columns. They are not meant to
be shown to users directly. This file defines the one set of
user-facing labels the app should use, so wording does not drift
between database outputs and the Streamlit interface.

**Rule:** any interface displaying `claim_category_1` or
`claim_category_2` to a person reads its label from this file, not from
the raw stored code. Stored codes never change without a migration;
display labels can be revised here without touching pipeline code.

## claim_category_1

| Stored code | Display label |
|---|---|
| `FUNCTIONAL` | Functional & benefit-led claims |
| `FREE_OF` | Free-from & reduced-content claims |
| `NATURAL_ORGANIC` | Natural & organic positioning |
| `OTHER` | Other positioning cues |
| `NO_CLAIM` | No claim identified |

## claim_category_2

| Stored code | Display label |
|---|---|
| `protein` | Protein |
| `fiber` | Fibre |
| `gut_health` | Gut health |
| `vitamins` | Vitamins / fortification |
| `immune` | Immune support |
| `energy` | Energy |
| `sleep` | Sleep |
| `brain_health` | Brain health |
| `whole_grain` | Whole grain |
| `no_added_x` | No added / reduced sugar |
| `reduced_fat` | Reduced fat |
| `no_artificial` | No artificial ingredients |
| `free_from` | Free-from / plant-based |
| `natural` | Natural |
| `organic` | Organic |
| `comparative` | Comparative positioning |
| `heritage` | Heritage / origin |
| `sustainability` | Sustainability |
| `other` | Other |
| `none` | No subcategory |

## nutrition_benchmark_flags

`nutrition_benchmark_flags` (in `product_analysis`) stores a pipe-separated
list of zero or more of these codes per product — not a single value.

| Stored code | Display label |
|---|---|
| `sugar_above_reference` | Sugar above reference threshold |
| `saturated_fat_above_reference` | Saturated fat above reference threshold |
| `fat_above_reference` | Fat above reference threshold |
| `salt_above_reference` | Salt above reference threshold |

## Implementation note

`shared/labels.py` reads these Markdown tables directly and caches the mappings
once per process. This file is therefore a runtime dependency, not only prose
documentation. Keep the exact section headings and the table row format
(two columns, with the stored code in backticks) intact. A wording change here
is picked up in a fresh process; there is no second hardcoded label dictionary
to update.

Labels are applied at display time. Filtering, joins and stored analytical
exports should continue to use the underlying codes. This documentation pass
changes only this implementation note; stored codes and display labels remain
unchanged.
