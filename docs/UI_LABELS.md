# UI display labels

This document is the canonical mapping from stored taxonomy codes
(`claim_category_1`, `claim_category_2` in `product_analysis` — see
`docs/COLUMN_DESCRIPTIONS.md`) to the display labels used in the
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

The Streamlit app should implement this as a simple lookup, applied only
at display time — filtering, joins, and any stored exports should
continue to use the underlying codes, not the display labels, so queries
remain stable even if display wording changes.

If a label in this table is revised, update it here first, then update
the interface to match — this file is the source of truth, not a record
of what the interface currently does.
