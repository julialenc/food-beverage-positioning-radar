# Nutrition Outlier Governance

## Purpose

This document defines a systematic approach for spotting and treating nutrition outliers in the Food & Beverage Positioning Radar project.

The goal is not to correct Open Food Facts data. The goal is to preserve raw source values while deciding whether each value is suitable for:

- product-level display;
- aggregate calculations;
- charts and product maps;
- QA / manual review.

Outliers matter because they can distort category-level metrics and make charts unreadable. For example, if most products sit between 200 and 500 kcal/100g but a few records show values above 2,000 kcal/100g, the visual scale becomes dominated by the extreme records and the meaningful differences between normal products disappear.

## Core principle

Raw Open Food Facts values should not be overwritten.

If a value looks wrong or analytically disruptive, the project should add quality and outlier flags. The raw value remains available in the source data, but the flags determine whether it is used in the app, summaries, charts, and exports.

Suggested principle:

```text
The project does not overwrite Open Food Facts nutrition values. It preserves raw source data and adds quality / outlier flags that determine whether a value is used in product display, aggregate metrics, and charts.
```

Suggested user-facing wording:

```text
Some values are excluded from summaries or charts when they appear inconsistent or would distort the selected category view. Raw source values are not edited.
```

## Final MVP lock state — 2026-08-25

Nutrition outlier governance is complete for the MVP launch. The locked
sequence is:

```text
1. Hard impossibility checks — DONE
2. Per-100 kcal nutrient-density checks — DONE
3. Energy consistency checks — DONE, Scenario C2 locked
4. Distributional plausibility review — DONE for method/output
5. Tail-pattern classification — DONE enough for MVP conclusion
6. Convert stable patterns into deterministic rules — DONE for the one approved
   MVP deterministic rule: beverage_view_segment
```

Production/app fields are:

```text
nutrition_quality_status
nutrition_quality_reason
outlier_type
include_in_product_table
include_in_aggregates
include_in_charts
```

Earlier draft names such as `include_in_product_explorer`,
`include_in_market_overview_calculations`, and
`include_in_market_overview_charts` may appear in historical notes or review
instructions. The loaded database and launch app use the production fields
above.

Final Scenario C2 is the locked production energy-consistency treatment. The
final Market Overview calculation-exclusion rate is approximately **3.02%**,
accepted for MVP because the rules are explicit, auditable, and preserve raw
Open Food Facts values.

Within-brand nutrition plausibility checks, such as unusually low or high
values compared with comparable products from the same brand, are not yet fully
implemented in the launch MVP. They are planned for a later governance update.

## Current implemented governance layer

### 2026-08-23 — Nutrition-quality flags and aggregate exclusions

Files changed:

```text
pipeline/nutrition_outliers/build_quality_flags.py
pipeline/nutrition_outliers/validate_quality_flags.py
docs/NUTRITION_OUTLIER_GOVERNANCE.md
data/nutrition_outlier_review/audits/  (generated local audit outputs)
```

This layer implements the audited treatment model after manual review of the
15% energy-macro sample. The manual review showed that products with material
reported-kcal versus macro-derived-kcal differences do not have one clean
profile. The mismatch may come from reported energy, macro values, fibre,
polyols, alcohol, labelling conventions, source mismatch, or remaining category
scope noise.

For this reason, the project does not overwrite Open Food Facts values and does
not treat every energy-macro mismatch as a hard source-data error.

Raw OFF values are preserved. The script adds derived fields:

```text
nutrition_quality_status
nutrition_quality_reason
include_in_product_table
include_in_aggregates
include_in_charts
energy_kcal_macro_calculated_100g
energy_kcal_macro_diff_abs
energy_kcal_macro_diff_pct
protein_g_per_100kcal
carbs_g_per_100kcal
fat_g_per_100kcal
```

### Hard data-quality errors

Hard data-quality errors are credibility-damaging contradictions or
impossibilities. They are excluded from Product Explorer, Market Overview
calculations, and Market Overview charts.

Treatment:

```text
nutrition_quality_status = data_quality_error
include_in_product_table = False
include_in_aggregates = False
include_in_charts = False
```

Reasons currently implemented:

```text
negative_nutrient_value
energy_above_900_kcal
nutrient_value_above_100g
macro_mass_balance_exceeds_100g
sugars_greater_than_carbs
saturated_fat_greater_than_fat
nutrient_density_exceeds_energy_limit
```

The hard mass-balance rule used by this implemented governance layer is:

```text
protein_g_100g + carbs_g_100g + fat_g_100g > 100
```

This differs from the earlier candidate-generation checkpoint that temporarily
used `>105g` to study rounding tolerance. The final aggregate-governance rule
uses the stricter mass-balance definition requested for the audited layer.

### Per-100 kcal impossibility checks

Per-100g values such as 41.5g fat per 100g can be realistic. The stronger check
is relative to reported energy. The implemented density fields are calculated
only when reported energy is available and greater than zero:

```text
protein_g_per_100kcal = protein_g_100g / energy_kcal_100g * 100
carbs_g_per_100kcal   = carbs_g_100g / energy_kcal_100g * 100
fat_g_per_100kcal     = fat_g_100g / energy_kcal_100g * 100
```

Automatic hard-exclusion thresholds:

```text
protein_g_per_100kcal > 27
carbs_g_per_100kcal > 27
fat_g_per_100kcal > 12.5
```

These thresholds are slightly above theoretical limits to avoid ordinary
rounding noise.

### Energy-macro inconsistency

Energy-macro inconsistency is not treated as a hard data-quality error by
default. It is treated through the locked Scenario C2 rule: material or unsafe
energy-macro mismatches are excluded from aggregate nutrition analysis, while
small absolute gaps and guarded beverage formula exceptions can remain in
Market Overview calculations and charts.

Formula:

```text
energy_kcal_macro_calculated_100g =
  fat_g_100g * 9 + protein_g_100g * 4 + carbs_g_100g * 4

energy_kcal_macro_diff_abs =
  energy_kcal_100g - energy_kcal_macro_calculated_100g

energy_kcal_macro_diff_pct =
  energy_kcal_macro_diff_abs / energy_kcal_100g
```

Rule:

```text
abs(energy_kcal_macro_diff_pct) >= 0.15
```

Baseline detection when no hard data-quality error is already present:

```text
nutrition_quality_reason = energy_macro_difference_15pct_or_more
```

Locked Scenario C2 accepted exceptions:

```text
1. abs(energy_kcal_macro_diff_abs) <= 20
   reason includes energy_macro_small_absolute_gap_accepted

2. category = beverages
   energy_kcal_100g <= 60
   abs(energy_kcal_macro_diff_abs) <= 10
   reason includes low_energy_beverage_macro_gap_accepted

3. category = beverages
   product name indicates alcohol or fermented beverage
   0 < energy_kcal_100g <= 100
   reason includes alcohol_formula_exception_accepted
```

Treatment for accepted exceptions:

```text
nutrition_quality_status = valid
include_in_product_table = True
include_in_aggregates = True
include_in_charts = True
energy_macro_exception_type records the accepted exception rule
```

Treatment for remaining material/unsafe energy-macro inconsistencies:

```text
nutrition_quality_status = energy_macro_inconsistency
include_in_product_table = True
include_in_aggregates = False
include_in_charts = False
```

High-energy alcohol/fermented beverage safeguard:

```text
If category = beverages
and product name indicates alcohol or fermented beverage
and energy_kcal_100g > 100
then keep visible in Product Explorer but exclude from Market Overview
calculations and charts.

reason includes high_energy_beverage_formula_exception_review
```

User-facing neutral note:

```text
This product is shown at product level but excluded from aggregate nutrition summaries because reported energy and macronutrient-derived energy differ materially.
```

Do not describe these records in the UI as wrong, bad, misleading, or invalid
products.

### Inclusion logic

Product Explorer:

```text
Show records where include_in_product_table = True.
Hide only hard data-quality errors from normal product-level display.
```

Market Overview calculations:

```text
Use records where include_in_aggregates = True.
Exclude data_quality_error, remaining energy_macro_inconsistency,
genuine_outlier, category_scope_outlier, and manual_review unless an approved
rule explicitly allows inclusion.
```

Market Overview charts:

```text
Use records where include_in_charts = True.
Exclude the same records as calculations by default, because even valid
outliers can distort scatterplots, boxplots, distributions, and percentile
visuals.
```

### QA audit outputs

The implemented script writes these local audit files when run:

```text
data/nutrition_outlier_review/audits/hard_data_quality_errors.csv
data/nutrition_outlier_review/audits/energy_macro_inconsistency_15pct.csv
data/nutrition_outlier_review/audits/energy_macro_accepted_exceptions.csv
data/nutrition_outlier_review/audits/genuine_outliers.csv
data/nutrition_outlier_review/audits/category_scope_outliers.csv
data/nutrition_outlier_review/audits/nutrition_quality_summary_by_region_category.csv
data/nutrition_outlier_review/audits/nutrition_quality_flags.csv
```

The key QA metric is:

```text
% of products excluded from Market Overview calculations
```

If this is materially above the 2-3% comfort range, the generated audit files
must be reviewed before finalizing downstream app/database use.

### 2026-08-23 — Scenario C under review

Scenario testing was added after reviewing the exclusion-reduction file and the
manual notes in `clean_up_23.08.2026.docx`. The notes are treated as review
evidence, not executable instructions.

The observed issue is methodological: the `abs(energy_kcal_macro_diff_pct) >=
0.15` rule is too blunt for beverages and records with very low absolute kcal
values. A tiny absolute kcal difference can become a large percentage
difference when reported energy is close to zero.

Scenario results:

| Scenario | Treatment | Excluded records | Excluded % |
|---|---|---:|---:|
| Scenario A | Current rules | 19,635 | 5.18% |
| Scenario B | Re-include `small_absolute_kcal_gap` | 14,011 | 3.70% |
| Scenario C | Re-include `small_absolute_kcal_gap` + `beverage_energy_not_captured_by_macros` | 8,574 | 2.26% |

Scenario C review exports:

```text
data/nutrition_outlier_review/audits/scenario_c_reincluded_for_review.csv
data/nutrition_outlier_review/audits/scenario_c_still_excluded_for_review.csv
data/nutrition_outlier_review/audits/scenario_c_summary.csv
```

Scenario C is the leading candidate rule set for this review round because it
brings Market Overview calculation exclusions into the target 2-3% range while
keeping hard physical contradictions excluded by default.

Status:

```text
provisional_under_review
```

No app/database behavior is changed until the Scenario C record-level output is
reviewed and explicitly locked.

### 2026-08-23 — Scenario C2 locked

Scenario C was directionally correct but too broad. The review found that the
full Scenario C re-inclusion file mixed genuinely non-material cases with
records that should stay excluded or remain under audit.

Key findings:

```text
1. Low/zero-calorie beverages can fail the 15% macro-consistency rule because
   the denominator is tiny, even when the absolute kcal gap is analytically
   irrelevant.
2. Some beverages in the broad Scenario C file have suspicious high energy
   values, including repeated values around 660.1 kcal/100g and 857.1 kcal/100g.
3. Some food-category records in the small_absolute_kcal_gap bucket have
   50-75 kcal/100g gaps, which are material for snacks, cereals, and dairy.
4. Alcohol or fermented beverages need formula-exception logic because alcohol
   contributes energy that is not captured by the protein-carbohydrate-fat
   macro formula.
```

Scenario C2 guarded re-inclusion rules:

```text
Re-include:
1. small_absolute_kcal_gap where abs(energy_kcal_macro_diff_abs) <= 20
2. beverage_energy_not_captured_by_macros where:
   category = beverages
   energy_kcal_100g <= 60
   abs(energy_kcal_macro_diff_abs) <= 10
3. alcohol/fermented beverage formula exceptions where:
   category = beverages
   product name indicates alcohol or fermented beverage
   0 < energy_kcal_100g <= 100

Keep excluded:
1. hard physical contradictions
2. alcohol/fermented beverage energy_kcal_100g > 100 unless reviewed
3. repeated suspicious high-kcal beverage values
4. snacks/cereals/dairy with material kcal gaps above the guarded threshold
```

Final locked Scenario C2 result after implementation in
`pipeline/nutrition_outliers/build_quality_flags.py`:

| Scenario | Treatment | Excluded records | Excluded % |
|---|---|---:|---:|
| Scenario A | Current rules | 19,635 | 5.18% |
| Scenario C | Broad re-include of small-gap and beverage-formula buckets | 8,574 | 2.26% |
| Scenario C2 locked | Guarded kcal-gap and beverage formula exceptions, with alcohol/fermented beverage auto-include capped at <=100 kcal/100g | 11,437 | 3.02% |

Final status counts:

```text
valid                         367,398
data_quality_error              6,026
energy_macro_inconsistency      5,411
```

Accepted energy-macro exceptions:

```text
total accepted exceptions: 8,198
```

Scenario C2 review exports:

```text
data/nutrition_outlier_review/audits/energy_macro_accepted_exceptions.csv
data/nutrition_outlier_review/audits/energy_macro_inconsistency_15pct.csv
data/nutrition_outlier_review/audits/nutrition_quality_flags.csv
data/nutrition_outlier_review/audits/scenario_c2_reincluded_for_review.csv
data/nutrition_outlier_review/audits/scenario_c2_still_excluded_for_review.csv
data/nutrition_outlier_review/audits/scenario_c2_summary.csv
```

Status:

```text
locked_for_current_review_round
```

The rule is locked in the quality-flag builder. App/database behavior still
depends on downstream wiring to use the generated inclusion flags.

### Examples: visible at product level, excluded from Market Overview

Some products have useful product-level records but are not reliable enough for
aggregate nutrition summaries.

For example, a high-fibre cereal or granola may have reported kcal that differs
materially from kcal calculated from protein, carbohydrates, and fat. This can
happen because of fibre, labelling conventions, source-data differences, or OFF
entry issues. The product remains visible in Product Explorer, but it is
excluded from Market Overview calculations and charts.

A zero-sugar or reduced-sugar confectionery product may also show an
energy-macro mismatch because polyols or other carbohydrate conventions are not
captured cleanly by the simple macro formula. It remains visible at product
level but is excluded from aggregate nutrition summaries.

An alcohol-containing drink may have energy that is not captured by the
protein-carbohydrate-fat formula. Under the locked Scenario C2 rule, plausible
alcohol or fermented beverages at `<=100 kcal/100g` can remain in Market
Overview calculations and charts, while high-energy alcohol-like beverage
exceptions remain product-visible but excluded pending review.

## Implementation log

### 2026-08-22 — Foundation and basic impossible values

Files changed:

```text
pipeline/clean.py
pipeline/nutrition_outliers/__init__.py
data/nutrition_outlier_review/candidates/.gitkeep
data/nutrition_outlier_review/reviewed/.gitkeep
data/nutrition_outlier_review/reports/.gitkeep
```

What was implemented:

```text
1. Added a dedicated nutrition-outlier workflow package/folder.
2. Added review-output folders for candidates, reviewed decisions, and reports.
3. Preserved original Open Food Facts nutrition values in *_off_raw columns before any compatibility capping.
4. Added derived quality/inclusion fields in clean.py:
   nutrition_quality_status
   outlier_type
   include_in_product_table
   include_in_aggregates
   include_in_charts
   nutrition_quality_reason
5. Implemented the first formal hard-check step: basic impossible nutrition values.
```

Basic impossible values implemented in this step:

```text
energy_kcal < 0
energy_kcal > 900
protein_100g < 0
carbs_100g < 0
fat_100g < 0
sugars_100g < 0
saturated_fat_100g < 0
fiber_100g < 0
salt_100g < 0
```

Treatment implemented for these rows:

```text
nutrition_quality_status = data_quality_error
outlier_type = data_quality_error
include_in_product_table = False
include_in_aggregates = False
include_in_charts = False
nutrition_quality_reason includes negative_nutrient_value
nutrition_quality_reason includes energy_above_900_kcal when energy_kcal > 900
```

Important transition note:

```text
clean.py still applies the project's previous simple upper caps to the working nutrition columns for downstream compatibility. Those caps are now separated from the formal basic-impossible-values step. They preserve existing app/precompute behavior while raw OFF values remain available in *_off_raw columns. The upper-cap / structural checks have not yet been reviewed as a completed governance step.
```

Not yet implemented:

```text
per-100 kcal nutrient-density checks
energy consistency checks
category-plausibility checks
distributional review
manual-review decision ingestion
database/app use of nutrition quality flags
```

### 2026-08-22 — Per-100g structural checks

Files changed:

```text
pipeline/clean.py
docs/NUTRITION_OUTLIER_GOVERNANCE.md
```

What was implemented:

```text
1. Added the second hard-check step: per-100g structural checks.
2. Kept the checks separate from basic impossible values and legacy compatibility capping.
3. Preserved raw Open Food Facts nutrition values in *_off_raw columns before these checks run.
4. Exported candidate rows separately for audit review after running clean.py.
```

Per-100g structural checks implemented in this step:

```text
protein_100g > 100
carbs_100g > 100
fat_100g > 100
fiber_100g > 100
salt_100g > 100
sugars_100g > carbs_100g
saturated_fat_100g > fat_100g
protein_100g + carbs_100g + fat_100g > 105
```

Treatment implemented for these rows:

```text
nutrition_quality_status = data_quality_error
outlier_type = data_quality_error
include_in_product_table = False
include_in_aggregates = False
include_in_charts = False
nutrition_quality_reason includes one or more of:
  nutrient_value_above_100g
  sugars_greater_than_carbohydrates
  saturated_fat_greater_than_fat
  macros_exceed_100g
```

Run output:

```text
Input: data/sample/sample_all_20260821_191708.csv
Clean output: data/sample/clean_20260822_201908.csv
Candidate audit CSV: data/nutrition_outlier_review/candidates/per_100g_structural_checks_20260822_201908.csv
Flagged product rows: 957
```

Reason-code counts:

```text
sugars_greater_than_carbohydrates    433
saturated_fat_greater_than_fat       284
nutrient_value_above_100g            172
macros_exceed_100g                   101
```

Note: reason-code counts can sum to more than the flagged-row count because a product row can carry more than one reason.

Threshold update:

```text
The macro-sum rule was changed from >100g to >105g on 2026-08-22 after review found products only very slightly above 100g because of rounding. The 105g threshold preserves the structural sanity check while allowing a small tolerance for label rounding and source-field precision.
```

Step status:

```text
Locked for this review round after rerunning clean.py with the >105g macro-sum threshold.
```

Not yet implemented:

```text
energy consistency checks
category-plausibility checks
distributional review
manual-review decision ingestion
database/app use of nutrition quality flags
```

### 2026-08-22 — Per-100 kcal nutrient-density checks

Files changed:

```text
pipeline/clean.py
docs/NUTRITION_OUTLIER_GOVERNANCE.md
```

What was implemented:

```text
1. Added the third hard-check step: per-100 kcal nutrient-density checks.
2. Calculated density only where energy_kcal is available and greater than 0.
3. Ran this step after basic impossible values and per-100g structural checks, so already-invalid values are not reinterpreted as density cases.
4. Used tolerant production thresholds from this governance document.
```

Per-100 kcal nutrient-density checks implemented in this step:

```text
protein_100g / energy_kcal * 100 > 28
carbs_100g / energy_kcal * 100 > 28
fat_100g / energy_kcal * 100 > 12.5
```

Treatment implemented for these rows:

```text
nutrition_quality_status = data_quality_error
outlier_type = data_quality_error
include_in_product_table = False
include_in_aggregates = False
include_in_charts = False
nutrition_quality_reason includes nutrient_density_exceeds_energy_limit
```

Threshold rationale:

```text
The theoretical maximum densities are approximately 25g/100 kcal for protein, 25g/100 kcal for carbohydrates, and 11.1g/100 kcal for fat. The implemented thresholds use tolerance (28, 28, and 12.5 respectively) to allow for label rounding, fibre/polyol definitions, and source-field precision.
```

Run output:

```text
Input: data/sample/sample_all_20260821_191708.csv
Clean output: data/sample/clean_20260822_202403.csv
Candidate audit CSV: data/nutrition_outlier_review/candidates/per_100kcal_nutrient_density_20260822_202403.csv
Flagged product rows: 4,160
```

Check counts from clean.py:

```text
protein_100g density > 28g/100 kcal     786
carbs_100g density > 28g/100 kcal     3,353
fat_100g density > 12.5g/100 kcal     1,464
```

Note: check counts can sum to more than the flagged-row count because a product row can trip more than one density check. The candidate CSV also includes raw density helper columns for review; those helpers are calculated from preserved *_off_raw values, while the official check counts above come from the cleaned working values at the moment Step 3 runs after Steps 1 and 2.

### 2026-08-22 — Energy consistency check

Files changed:

```text
pipeline/clean.py
docs/NUTRITION_OUTLIER_GOVERNANCE.md
```

What was implemented:

```text
1. Added the fourth hard-check step: reported energy consistency with macro-calculated energy.
2. Calculated macro energy from preserved *_off_raw values so this check can still run after earlier steps have nulled working columns.
3. Treated reported energy as the suspect working value when the check fails; plausible macro values are not nulled by this check.
```

Energy consistency check implemented in this step:

```text
calculated_energy_kcal = 4 * (protein_100g + carbs_100g) + 9 * fat_100g
flag when:
  absolute difference > 75 kcal
  AND relative difference > 40%
```

Treatment implemented for these rows:

```text
nutrition_quality_status = data_quality_error
outlier_type = data_quality_error
include_in_product_table = False
include_in_aggregates = False
include_in_charts = False
nutrition_quality_reason includes energy_inconsistent_with_macros
energy_kcal is set to null in the working column
raw energy and macro values remain preserved in *_off_raw columns
```

Run output:

```text
Input: data/sample/sample_all_20260821_191708.csv
Clean output: data/sample/clean_20260822_205655.csv
Candidate audit CSV: data/nutrition_outlier_review/candidates/energy_consistency_20260822_205655.csv
Flagged product rows: 3,752
```

Candidate CSV helper columns:

```text
calculated_energy_kcal_from_macros_off_raw
energy_difference_abs_off_raw
energy_difference_pct_off_raw
```

Comparison run:

```text
On 2026-08-22, the relative-difference threshold was tightened from 40% to 15% for comparison review. The absolute-difference requirement remains >75 kcal, and the relative difference is absolute, so it catches reported energy that is materially too low or materially too high versus macro-calculated energy.
```

15% comparison output:

```text
Input: data/sample/sample_all_20260821_191708.csv
Clean output: data/sample/clean_20260822_220423.csv
Candidate audit CSV: data/nutrition_outlier_review/candidates/energy_consistency_15pct_20260822_220423.csv
Flagged product rows: 5,244
```

Manual-review sample:

```text
Created on: 2026-08-23
Source: data/nutrition_outlier_review/candidates/energy_consistency_15pct_20260822_220423.csv
Output: data/nutrition_outlier_review/candidates/energy_consistency_15pct_manual_sample_20260823.csv
Rows: 36
Design: 3 rows per MVP region-category combination; target energy-difference percentages approximately 15%, 20%, and 30%; all sampled rows require a non-empty image_url.
```

## Historical implementation notes

The sections below document how the governance logic evolved. They are retained
for auditability, but they are superseded by the **Final MVP lock state —
2026-08-25** section above. For production implementation, use the locked
Scenario C2 rules and production field names.

## Outlier types

Use three main classes.

### 1. Data-quality error

A value is likely wrong, internally inconsistent, unit-confused, or structurally implausible.

Examples:

```text
negative nutrient values
energy too far from calculated energy
protein + carbs + fat materially above 100g per 100g
sugars > carbohydrates
saturated fat > total fat
nutrient density per 100 kcal exceeds theoretical limits
salt / sodium unit confusion
```

Treatment:

```text
Keep in raw data
Do not overwrite
Exclude from product display
Exclude from aggregate calculations
Exclude from charts
Flag as data_quality_error
```

Rationale: visibly impossible values undermine credibility.

### 2. Genuine outlier

The value is extreme but plausible for the product type.

Examples:

```text
chewing gum within snacks
very high-fat nut products
very low-calorie jelly / gum products
pure sweetener-style products
protein powders if they appear inside scope
```

Treatment:

```text
Keep in raw data
Show in product-level tables when useful
Usually exclude from aggregate category metrics if it distorts the category
Exclude from charts, separate visually, or use capped axes
Flag as genuine_outlier
```

Rationale: the product is real and the value may be correct, but it can distort category-level analysis.

### 3. Category-scope outlier

The product may belong to the category commercially, but it behaves unlike the main analytical peer group.

Example:

```text
chewing gum is legitimately a snack, but nutritionally it behaves unlike most food snacks
```

Treatment:

```text
Keep in category
Show in tables
Exclude from core category nutrition metrics if needed
Exclude from charts or show separately
Flag as category_scope_outlier
```

Rationale: this preserves commercial category logic while protecting summary statistics and charts.

## Historical recommended output fields — superseded by MVP lock state

Add derived fields rather than changing source values.

```text
nutrition_quality_status
outlier_type
include_in_product_table
include_in_aggregates
include_in_charts
nutrition_quality_reason
```

Suggested values for `nutrition_quality_status`:

```text
valid
genuine_outlier
category_scope_outlier
data_quality_error
manual_review
```

Suggested Boolean flags:

```text
include_in_product_table
include_in_aggregates
include_in_charts
```

Suggested reason codes:

```text
energy_inconsistent_with_macros
nutrient_density_exceeds_energy_limit
negative_nutrient_value
sugars_greater_than_carbohydrates
saturated_fat_greater_than_fat
macros_exceed_100g
valid_extreme_chewing_gum
valid_extreme_nut_product
category_scope_extreme_format
manual_review_required
```

## Treatment matrix

| Outlier type | Product table | Aggregates | Graphs | Raw data |
|---|---:|---:|---:|---:|
| Normal | show | include | include | keep |
| Genuine outlier | show | usually exclude or separate | exclude / separate / capped axis | keep |
| Category-scope outlier | show | exclude from core metrics if needed | exclude or separate | keep |
| Data-quality error | hide from app display | exclude | exclude | keep |
| Manual review | show only in QA / audit | exclude until resolved | exclude | keep |

## Historical hard-check design notes

These rules identify values that are impossible or highly implausible.

### Basic impossible values

Flag as `data_quality_error` when any of the following apply:

```text
energy_kcal_100g < 0
energy_kcal_100g > 900
protein_g_100g < 0
carbs_g_100g < 0
fat_g_100g < 0
sugars_g_100g < 0
saturated_fat_g_100g < 0
fiber_g_100g < 0
salt_g_100g < 0
```

### Per-100g structural checks

Flag as `data_quality_error` or `manual_review` depending on severity:

```text
protein_g_100g > 100
carbs_g_100g > 100
fat_g_100g > 100
sugars_g_100g > carbs_g_100g
saturated_fat_g_100g > fat_g_100g
protein_g_100g + carbs_g_100g + fat_g_100g > 105
fiber_g_100g > 100
salt_g_100g > 100
```

Use `>105g` rather than `>100g` for the macro sum to allow a small tolerance for rounding error and source-field precision.

## Historical nutrient-density design notes

These are critical sanity checks.

Per 100g values such as protein >25g/100g or fat >11g/100g can be perfectly valid. The stronger theoretical check is per 100 kcal.

Approximate Atwater energy factors:

```text
protein = 4 kcal / g
carbs   = 4 kcal / g
fat     = 9 kcal / g
```

Therefore the theoretical maximum nutrient density per 100 kcal is approximately:

```text
protein: 25 g / 100 kcal
carbs:   25 g / 100 kcal
fat:     11.1 g / 100 kcal
```

Calculate only when `energy_kcal_100g > 0` and the nutrient value is available.

```text
protein_g_per_100kcal = protein_g_100g / energy_kcal_100g * 100
carbs_g_per_100kcal   = carbs_g_100g   / energy_kcal_100g * 100
fat_g_per_100kcal     = fat_g_100g     / energy_kcal_100g * 100
```

Strict theoretical checks:

```text
protein_g_per_100kcal > 25
carbs_g_per_100kcal > 25
fat_g_per_100kcal > 11.1
```

Recommended production thresholds with tolerance:

```text
protein_g_per_100kcal > 27 or 28
carbs_g_per_100kcal > 27 or 28
fat_g_per_100kcal > 12 or 12.5
```

Reason for tolerance: rounding, fibre, polyols, label methodology, missing nutrients, and OFF source inconsistencies.

Suggested treatment:

```text
nutrition_quality_status = data_quality_error
include_in_product_table = False
include_in_aggregates = False
include_in_charts = False
nutrition_quality_reason = nutrient_density_exceeds_energy_limit
```

## Historical energy-consistency design notes

Reported energy can be compared with energy calculated from macros.

Approximate formula:

```text
calculated_energy_kcal = 4 * protein_g_100g + 4 * carbs_g_100g + 9 * fat_g_100g
```

Use tolerance, not exact equality.

Recommended starting rule:

```text
flag if absolute difference > 75 kcal
AND relative difference > 30% to 40%
```

Suggested reason code:

```text
energy_inconsistent_with_macros
```

This should usually trigger `manual_review` or `data_quality_error`, depending on how extreme the gap is.

## Category-plausibility checks

These are not theoretical impossibilities. They identify values that may be valid but should be reviewed within the selected category.

Examples for snacks:

```text
energy_kcal_100g > 800
protein_g_100g > 60
fiber_g_100g > 50
salt_g_100g > 10
```

Examples for cereals:

```text
fat_g_100g > 50
protein_g_100g > 50
sugars_g_100g > 90
salt_g_100g > 5
```

These should generally produce:

```text
nutrition_quality_status = manual_review
```

not automatic exclusion.

## Distributional plausibility review

After hard rules and energy-macro consistency treatment, inspect the
distribution by category, market, metric, and tail band.

This combines the earlier category-plausibility and percentile-review steps.
The reason is methodological: category plausibility is hard to define as a
single abstract threshold. A high fat value in snacks may be normal chocolate
or nuts, category-scope noise such as oil or butter, or a data-quality issue.
The percentile tail shows which pattern dominates before any new rule is
created.

Important principle:

```text
Extreme is not the same as wrong.
```

The review question is:

```text
Is the tail dominated by a stable, explainable product type?
```

If yes, it may be a genuine product-format outlier cluster or normal category
structure. If no, keep it as manual review or data-quality audit evidence.

Recommended order:

```text
1. Run hard impossibility checks.
2. Run per-100 kcal nutrient-density checks.
3. Run energy consistency checks.
4. Run distributional plausibility review by country/region, category, metric,
   and incremental tail band.
5. Classify tail patterns.
6. Review top and bottom products by metric where the tail pattern is unclear.
7. Look for repeated patterns by product type, brand, OFF category, unit,
   country, or source field.
8. Convert repeated patterns into deterministic rules only when the pattern is
   stable.
9. Keep unclear one-off cases as review/audit records rather than new rules.
```

Use incremental bands rather than overlapping tails:

```text
P0-P1
P1-P5
P5-P10
P10-P20
P80-P90
P90-P95
P95-P99
P99-P100
```

The output should summarize each:

```text
country / region
category
metric
tail band
```

with:

```text
record_count
median metric value in band
top product-name tokens
top brands
top OFF categories
top product examples
suggested_pattern_label
```

Provisional labels:

```text
likely_genuine_outlier_cluster
likely_category_scope_noise
likely_data_quality_issue
normal_category_tail
needs_manual_review
```

The first implemented distributional plausibility review writes:

```text
data/nutrition_outlier_review/audits/distributional_plausibility_tail_summary.csv
data/nutrition_outlier_review/audits/distributional_plausibility_tail_examples.csv
```

App-treatment principle remains separate from source validity:

```text
A genuine outlier can remain visible in Product Explorer but be excluded from
Market Overview charts if it distorts the visual scale.
```

### 2026-08-23 — MVP beverage view segmentation

The distributional plausibility review showed that most remaining tails are
stable product-format clusters rather than new data-quality errors. The main
MVP chart-governance issue is beverages: ready-to-drink products were being
mixed with syrups, powders, capsules/pods, dry tea or infusions, concentrates,
and alcohol.

Implemented derived field:

```text
beverage_view_segment
```

Allowed values:

```text
ready_to_drink_beverages
beverage_preparations_and_alcohol
not_beverage
unknown_beverage_segment
```

Treatment:

```text
Product Explorer:
  show valid tails.

Market Overview calculations:
  include normal category tails.

Market Overview charts:
  use the beverage segment filter to avoid mixing product forms that are not
  directly comparable in nutrition charts.
```

Classification logic:

```text
Precedence:
  1. non-beverage categories -> not_beverage
  2. protected RTD exceptions -> ready_to_drink_beverages
  3. hard preparation / alcohol terms -> beverage_preparations_and_alcohol
  4. general RTD terms -> ready_to_drink_beverages
  5. otherwise -> unknown_beverage_segment

ready_to_drink_beverages:
  water / eau / agua, flavoured water, sparkling water, soft drinks, soda,
  cola, lemonade, iced tea / RTD tea, kombucha, juice / jus / zumo / sok /
  saft, nectar, smoothie, energy drinks, sports drinks, plant-based drinks,
  oat/almond/soy drinks, milk drinks, and clear RTD brand/product patterns
  such as Volvic, Evian, Fanta, Sprite, Dr Pepper, Pepsi, Coca Cola, Monster,
  Red Bull, Capri-Sun, and Appletiser.

beverage_preparations_and_alcohol:
  syrups, cordials, concentrates, drink powders, cocoa/chocolate powders,
  instant drink preparations, instant coffee, soluble coffee, coffee
  capsules/pods, ground coffee, tea bags, loose tea, herbal tea, infusions,
  tisanes, rooibos, wine, beer, cider, sake, spirits, vodka, whisky, rum,
  gin, cognac, brandy, liqueurs, cocktails, spritz, aperitif, cooking wine,
  and coconut cream.

not_beverage:
  all non-beverage categories.

unknown_beverage_segment:
  beverage records not classifiable by the MVP two-segment logic.
```

Protected RTD exceptions are applied before generic tea/preparation rules for
obvious finished tea beverages such as iced tea, ice tea, Nestea, Arizona,
Pure Leaf, Lipton Ice Tea, green tea zero, sweet tea, and kombucha.

Launch principle: it is better to leave unclear brand-only products in
`unknown_beverage_segment` than to put syrups, alcohol, powders, capsules, dry
tea, dry coffee, or coconut cream into the ready-to-drink chart segment.

Final launch keyword pass on 2026-08-23 reduced obvious unknown beverage
records by adding multilingual and brand/product-form coverage for water,
juices, sodas, plant drinks, RTD coffee/tea exceptions, alcohol and
alcohol-adjacent beer/cider/wine products, dry coffee/tea/cocoa preparations,
syrups, concentrates, and ingredient-like coconut milk/cream. Unknown is kept
only when product form is still not clear enough from name or OFF category.

Market Overview UI:

```text
When the selected category is beverages, show a Beverage view segment filter.
Default: Ready-to-drink beverages.
Options: All beverages; Ready-to-drink beverages; Beverage preparations and
alcohol; Unknown beverage segment.
```

This is an MVP segmentation, not a final beverage taxonomy. It is intended to
reduce chart distortion while preserving raw OFF data and product-level
visibility.

### Lock decision: beverage view segment

As of 2026-08-23, `beverage_view_segment` is locked as MVP-ready.

For Market Overview, beverages are split into two practical MVP segments:

```text
ready_to_drink_beverages
beverage_preparations_and_alcohol
```

This split is used to avoid mixing ready-to-drink products such as water, soda,
juice, iced tea, kombucha, and plant drinks with syrups, concentrates, powders,
tea bags, coffee capsules, alcohol, and similar preparation-based or
alcohol-related products.

The classifier is rule-based and intended for launch-stage chart readability,
not as a final beverage taxonomy. Some beverage records remain assigned to
`unknown_beverage_segment` because the product name, category metadata, or
available fields do not provide enough reliable product-form evidence.

Unknown beverage records are work in progress and should not be interpreted as
a separate market segment.

Final MVP-region counts at lock:

```text
ready_to_drink_beverages              58,265
beverage_preparations_and_alcohol     39,886
unknown_beverage_segment              11,218
```

MVP status:

```text
beverage_view_segment = MVP-ready
known limitation = unknown segment remains
next version = better beverage type taxonomy, not more keyword patching
```

With this lock, the nutrition-outlier governance sequence is complete for MVP:

```text
1. Hard impossibility checks — DONE
2. Per-100 kcal nutrient-density checks — DONE
3. Energy consistency checks — DONE, Scenario C2 locked
4. Distributional plausibility review — DONE for method/output
5. Tail-pattern classification — DONE enough for MVP conclusion
6. Convert stable patterns into deterministic rules — DONE for the one approved
   MVP deterministic rule: beverage_view_segment
```

Audit output:

```text
data/nutrition_outlier_review/audits/beverage_view_segment_audit.csv
```

## Manual review workflow

For the first manual pass, create audit tables such as:

```text
metric
product_name
brand
category
market_region
energy_kcal_100g
protein_g_100g
carbs_g_100g
fat_g_100g
sugars_g_100g
sat_fat_g_100g
fiber_g_100g
salt_g_100g
protein_g_per_100kcal
carbs_g_per_100kcal
fat_g_per_100kcal
calculated_energy_kcal
energy_difference_abs
energy_difference_pct
suggested_quality_status
suggested_reason
reviewer_decision
reviewer_note
```

Manual decisions should become either:

```text
valid
genuine_outlier
category_scope_outlier
data_quality_error
manual_review
```

Only stable, repeated patterns should be converted into code rules.

## UI treatment

### Product tables

- Show normal products.
- Show genuine outliers if they are valid and useful.
- Hide data-quality errors from normal product display.
- Keep data-quality errors available in QA/audit exports.

### Aggregate metrics

Exclude:

```text
data_quality_error
manual_review until resolved
genuine_outlier when it materially distorts the category
category_scope_outlier when the metric is intended to describe the core peer group
```

### Charts and product maps

Options:

```text
exclude from chart
show separately
use capped axes
use log scale only if clearly explained
```

For MVP, the simplest and safest approach is:

```text
include_in_charts = False
```

for data-quality errors and disruptive genuine/category-scope outliers.

## Recommended MVP approach

For the first implementation:

```text
1. Preserve all raw OFF nutrition values.
2. Add derived quality and inclusion flags.
3. Automatically exclude only hard data-quality errors.
4. Send category-plausibility and distributional outliers to manual review.
5. Exclude unresolved manual-review rows from aggregates and charts.
6. Show only valid and reviewed genuine outliers in product tables.
7. Document all exclusions clearly in Methodology.
```

## Final working principle

```text
Do not correct the source data.
Do not silently drop records.
Flag values, preserve auditability, and decide separately whether each value belongs in tables, aggregates, and charts.
```
