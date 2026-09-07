# Nutrition Outlier Governance

**Status:** Product Explorer and Market Overview nutrition governance locked for MVP
**Last updated:** 2026-09-06

## Purpose

This document defines how Food \& Beverage Positioning Radar handles suspicious nutrition observations from Open Food Facts (OFF).

The project does **not** overwrite OFF nutrition values. Raw source values remain available for provenance and QA. Derived quality and warning fields determine whether a product is:

* credible enough to display in Product Explorer;
* displayed with a nutrition warning;
* eligible for Market Overview calculations;
* displayed in a selected Market Overview chart range.

The governing principle is deliberately conservative:

> \*\*Hide only products whose available nutrition data contains a high-confidence physical contradiction. Show physically possible products, with warnings where appropriate. Use all Product Explorer-valid products in Market Overview calculations. Use chart-range filtering only for visualization readability.\*\*

\---

# Governing hierarchy

```
                         OFF nutrition record
                                 │
                                 ▼
                    PRODUCT EXPLORER HARD GATE
                    High-confidence contradiction?
                                 │
                         ┌───────┴───────┐
                        YES              NO
                         │                │
                         ▼                ▼
                 HIDE FROM PRODUCT   SHOW IN PRODUCT
                     EXPLORER           EXPLORER
                         │                │
                         │       Cross-field or peer anomaly?
                         │                │
                         │        ┌───────┴───────┐
                         │       YES              NO
                         │        │                │
                         │        ▼                ▼
                         │    SHOW + !        SHOW NORMALLY
                         │                │
                         │                ▼
                         │      MARKET OVERVIEW CALCULATIONS
                         │      use all Product Explorer-valid
                         │      products
                         │                │
                         │                ▼
                         │      MARKET OVERVIEW CHARTS
                         │      same valid population
                         │      + selected-axis chart ranges
                         │
                         ▼
              RAW / QA ONLY
              no Product Explorer
              no Market Overview display
              no Market Overview calculations
```

**Load-bearing rules:**

1. Product Explorer hard gates define minimum data credibility.
2. If a product fails any hard gate, preserve it in raw/QA data but exclude it from Product Explorer, Market Overview display, and Market Overview calculations.
3. If a product passes all hard gates, show it in Product Explorer and use it in Market Overview calculations. Product Explorer warnings do not invalidate it.
4. Market Overview chart-range filters affect display only. They do not change Product Explorer eligibility or Market Overview calculations.

\---

# Raw-value preservation

Raw OFF values must not be silently corrected or replaced.

Where available, raw provenance fields use the `\*\_off\_raw` convention. Derived fields can classify or exclude a record, but the original observation remains traceable.

Core production fields:

```
nutrition\_quality\_status
nutrition\_quality\_reason
outlier\_type
include\_in\_product\_table
include\_in\_aggregates
include\_in\_charts
```

Product Explorer warning fields:

```
warning\_flag
warning\_types
warning\_summary
```

The Product Explorer table should expose only one compact `Warning` indicator. Specific warning names and explanations belong in the selected Product Card.

Current governance semantics:

```
include\_in\_product\_table = Product Explorer hard-gate result

Market Overview calculation eligibility
= include\_in\_product\_table = True

Market Overview chart universe
= include\_in\_product\_table = True
  plus selected-axis non-null requirements
  plus selected chart-range filters
```

`include\_in\_aggregates` and `include\_in\_charts` may remain in the schema for compatibility or audit history, but the current nutrition-governance source of truth is the Product Explorer hard-gate result plus the chart-range logic documented below.

\---

# Product Explorer decision model

## Layer 1 — Hard validity gate

A hard exclusion is appropriate only when the available nutrition values contain a **high-confidence contradiction that cannot reasonably be explained by normal label rounding, product format, or known energy sources omitted from a simple formula**.

Treatment:

```
nutrition\_quality\_status = data\_quality\_error
include\_in\_product\_table = False
include\_in\_aggregates = False
include\_in\_charts = False
```

The product remains in raw/QA data.

### Locked hard-exclusion tests

|Test|Product Explorer treatment|Rationale|
|-|-|-|
|Any tracked nutrient < 0|Hide|Negative nutrient mass is physically impossible|
|`energy\_kcal\_100g > 900`|Hide|Exceeds the energy density of pure fat|
|Any tracked nutrient > 100g/100g|Hide|More than 100g of one nutrient in 100g product is impossible|
|`energy\_kcal\_100g = 0` with meaningful positive macros|Hide|Positive energy-yielding macros cannot coexist with true zero energy|
|Reported energy below minimum implied energy|Hide|Available protein plus parent/subset macro lower bounds require more energy than reported|
|`protein + carbs + fat > 105g/100g`|Hide|Allows modest rounding tolerance; larger excess is structurally impossible|
|Minimum known nutrient mass >105g/100g|Hide|Available protein, effective carbs, effective fat, and salt cannot exceed product mass after tolerance|
|`salt\_g\_100g > 50`|Hide|Conservative launch-scope sanity boundary for extreme salt records|
|`sugars > carbs + tolerance`|Hide|Sugars are part of total carbohydrate|
|`saturated\_fat > fat + tolerance`|Hide|Saturated fat is part of total fat|
|`protein\_g\_per\_100kcal > 28`|Hide|Clearly exceeds the approximate physical energy-density limit after tolerance|
|`fat\_g\_per\_100kcal > 12.5`|Hide|Clearly exceeds the approximate physical energy-density limit after tolerance|

### Relational tolerance

The relationships `sugars <= carbs` and `saturated\_fat <= fat` should not use exact equality as the exclusion boundary because independently rounded label values can differ slightly.

For the Product Explorer hard gate, use a small absolute tolerance before declaring a contradiction:

```
sugars\_g\_100g > carbs\_g\_100g + 0.5
saturated\_fat\_g\_100g > fat\_g\_100g + 0.5
```

Values within the tolerance are not hard-excluded on this basis alone.

### Macro mass balance

The hard Product Explorer rule is:

```
protein\_g\_100g + carbs\_g\_100g + fat\_g\_100g > 105
```

The earlier `>100g` version is too strict for a hard-hide rule because independent label rounding can push the reported sum slightly above 100g.

The 105g threshold is therefore the current conservative Product Explorer gate.

### Minimum implied energy lower bound

When total fat or total carbohydrate is missing, available subset nutrients provide a lower bound:

```
effective\_fat =
    fat\_g\_100g if present
    else saturated\_fat\_g\_100g if present
    else 0

effective\_carbs =
    carbs\_g\_100g if present
    else sugars\_g\_100g if present
    else 0

minimum\_implied\_energy\_kcal\_100g =
      protein\_g\_100g \* 4
    + effective\_carbs \* 4
    + effective\_fat \* 9
```

This is a minimum estimate, not a full energy reconstruction. It must not double-count parent and subset nutrients.

Hard-exclude only when both conditions hold:

```
minimum\_implied\_energy\_kcal\_100g > energy\_kcal\_100g \* 1.25
minimum\_implied\_energy\_kcal\_100g - energy\_kcal\_100g > 20
```

This rule is evaluated when reported energy is non-null and non-negative and at least one contributing nutrient is available. Alcohol can explain additional reported energy omitted from the simple 4/4/9 formula, but it cannot explain reported energy being below the minimum already implied by reported nutrients.

Reason code:

```
reported\_energy\_below\_minimum\_implied\_energy
```

### Salt-aware mass balance

Use the same non-double-counting parent/subset logic for fat and carbohydrates, then add salt as independent known mass:

```
minimum\_known\_mass\_g\_100g =
      protein\_g\_100g
    + effective\_carbs
    + effective\_fat
    + salt\_g\_100g
```

Hard-exclude when:

```
minimum\_known\_mass\_g\_100g > 105
```

Reason code:

```
minimum\_known\_nutrient\_mass\_exceeds\_105g
```

Also hard-exclude extreme salt values:

```
salt\_g\_100g > 50
```

Reason code:

```
salt\_above\_50g\_per\_100
```

The `>50g` salt boundary is a conservative launch-scope sanity check, not a claim about a universal physical maximum for all imaginable foods.

\---

## Layer 2 — Per-100 kcal density checks

Per-100g values alone can look extreme while still being valid. Energy density provides a stronger cross-field check.

Calculate only when reported energy is available and greater than zero:

```
protein\_g\_per\_100kcal = protein\_g\_100g / energy\_kcal\_100g \* 100
carbs\_g\_per\_100kcal   = carbs\_g\_100g   / energy\_kcal\_100g \* 100
fat\_g\_per\_100kcal     = fat\_g\_100g     / energy\_kcal\_100g \* 100
```

Approximate theoretical references from the simple 4/4/9 energy model are:

```
protein: 25 g / 100 kcal
carbs:   25 g / 100 kcal
fat:     11.1 g / 100 kcal
```

Production hard gates retain tolerance:

```
protein\_g\_per\_100kcal > 28
fat\_g\_per\_100kcal > 12.5
```

### Carbohydrate density is not a hard-exclusion rule

`carbs\_g\_per\_100kcal > 27/28` must **not** be used as a Product Explorer physical-impossibility gate.

Reported carbohydrate can include components such as polyols whose energy yield is materially below the simple 4 kcal/g assumption. A high reported carbohydrate-per-100-kcal value can therefore be physically possible.

The carbohydrate-density field can remain available for QA diagnostics, but it does not independently hide a product and does not create a separate user-facing warning type.

\---

# Product Explorer warnings

A warning applies only after the product has passed every hard validity gate.

There are two Product Explorer nutrition warning types:

```
energy\_macro\_mismatch
within\_brand\_nutrition\_outlier
```

No other warning type should share the same `!` indicator.

The warning means:

> \*\*The product is physically possible enough to display, but one or more nutrition relationships deserve caution.\*\*

It does **not** mean that the product itself is wrong, misleading, unhealthy, or invalid.

\---

## Warning 1 — Energy-macro mismatch

### Purpose

This warning detects cases where all individual values may be physically possible, but reported energy and macro-derived energy differ materially.

Simple diagnostic formula:

```
energy\_kcal\_macro\_calculated\_100g =
    fat\_g\_100g \* 9
  + protein\_g\_100g \* 4
  + carbs\_g\_100g \* 4

energy\_kcal\_macro\_diff\_abs =
    energy\_kcal\_100g - energy\_kcal\_macro\_calculated\_100g

energy\_kcal\_macro\_diff\_pct =
    energy\_kcal\_macro\_diff\_abs / energy\_kcal\_100g
```

Baseline detection:

```
abs(energy\_kcal\_macro\_diff\_pct) >= 0.15
```

This is a **warning candidate**, not a physical-impossibility test.

### Why mismatch does not automatically mean bad data

The simple formula does not fully represent every labelled product.

A mismatch can arise from:

* fibre;
* polyols / sugar alcohols;
* alcohol;
* labelling conventions;
* source-field mismatch;
* rounding;
* OFF entry error.

Therefore an energy-macro mismatch should not by itself remove a product from Product Explorer.

### Alcohol / fermented beverage exception

If a product is confidently identified as alcoholic or fermented and alcohol is a plausible material energy source, the simple protein-carbohydrate-fat formula is incomplete.

For Product Explorer:

```
known alcohol / fermented beverage
    -> do not generate energy\_macro\_mismatch solely from the 4/4/9 formula
```

Do not loosen the formula until an alcoholic product happens to pass. Treat the formula as **not fully applicable** when a known energy source is omitted.

Other nutrition rules still apply. An alcoholic product can still fail a hard gate for a separate physical contradiction or receive a future peer-based warning.

### Product Card wording

**Energy-macro mismatch**

> Reported kcal and macro-derived kcal differ materially. The product is still useful to inspect, but nutrition interpretation should be cautious.

\---

## Warning 2 — Within-brand nutrition outlier

**Status:** Production rule locked for Product Explorer warning display.

### Purpose

This warning targets the second major Product Explorer problem:

> A nutrition value can be physically possible in isolation and internally possible as a combination, yet still be suspicious compared with genuinely comparable products.

Broad category tails are not sufficient for this purpose because legitimate product formats naturally create extreme values. Chocolate, nuts, chewing gum, granola, protein products, and similar formats can occupy valid category tails.

The comparison therefore needs a narrower peer context.

### Peer hierarchy

Compare products within:

```
normalized\_brand x region x category
```

Use only products that already pass the Product Explorer hard gate.

For products present in more than one launch region, evaluate each region-category occurrence separately against its own `normalized\_brand × region × category` peer set. The same GTIN may therefore be flagged in one region and not in another.

Do not run this warning for known broad ready-to-drink beverage portfolios maintained in the implementation skip list, such as Coca-Cola- or Pepsi-style portfolios. These brands can legitimately contain regular, low-sugar, zero-sugar, flavoured, and other variants with very wide nutrition ranges, so a single brand median would create misleading warnings. Large non-beverage brands are not skipped solely because they are large.

### Metrics

```
energy\_kcal\_100g
protein\_g\_100g
carbs\_g\_100g
fat\_g\_100g
sugars\_g\_100g
saturated\_fat\_g\_100g
fiber\_g\_100g
salt\_g\_100g
```

Use per-100g / per-100ml values only. Do not use per-100 kcal values for this warning.

### Rule

Calculate the median, MAD, and IQR for each metric within the eligible peer set.

Flag a metric only when all criteria below are met:

**A. Peer group size**

The brand-region-category peer group contains at least:

```
10 Product Explorer-visible products
```

**B. Metric observations**

The metric has at least:

```
10 non-null observations
```

**C. Statistical extremeness**

The product value is statistically extreme within the peer set:

```
abs(robust\_z) >= 4.5
```

where:

```
robust\_z = (value - median) / (1.4826 \* MAD)
```

Use robust z when MAD is positive and finite. If MAD is zero, missing, or otherwise unusable, use an outer IQR fence instead:

```
value < Q1 - 3 \* IQR
or
value > Q3 + 3 \* IQR
```

If IQR is also zero, missing, or unusable, the metric is not flagged by the statistical-extremeness criterion.

**D. Material relative difference**

When median is greater than zero:

```
value <= 50% of median
or
value >= 150% of median
```

When median equals zero, this relative-difference criterion is waived because ratios to zero are not meaningful.

**E. Absolute floor**

The absolute difference from the median must also meet or exceed the metric floor:

```
abs(value - median) >= metric-specific floor
```

|Metric|Floor|
|-|-:|
|`energy\_kcal\_100g`|75 kcal|
|`protein\_g\_100g`|5g|
|`carbs\_g\_100g`|15g|
|`fat\_g\_100g`|7.5g|
|`sugars\_g\_100g`|12g|
|`saturated\_fat\_g\_100g`|5g|
|`fiber\_g\_100g`|5g|
|`salt\_g\_100g`|0.8g|

The warning applies if one or more metrics pass all five criteria.

If the peer group has fewer than 10 products, the metric has fewer than 10 observations, or the product does not pass all criteria for any metric, do not flag the product on this basis.

### Temporary diagnostic observation — September 2026

*Current diagnostics reproduce all 12 region-category warning rates and found no rule-component failures. The IQR fallback accounts for only 5.87% of flagged metric rows. France/UK have higher median test eligibility than US/Canada (71.18% vs 53.59%), and warnings are concentrated in a limited number of brands, especially in cereals and France/UK dairy. Salt, energy, and protein are the most frequent triggering metrics. The statistical rule remains unchanged while these concentrated portfolio patterns are reviewed; this note is temporary and can be removed after that review.*

### Important implementation principle

This is a warning, not an exclusion.

Products with this warning:

```
show in Product Explorer
show one Warning = ! marker
show the warning explanation in the Product Card
remain eligible for Product Explorer search/filter display
```

This rule does not remove products from Market Overview calculations or charts. Products that pass the Product Explorer hard gates remain fully eligible regardless of warning status.

### Product Card wording

**Atypical nutrition profile within brand**

> One or more nutrition values differ substantially from comparable products in the same brand/category/region. This may reflect a distinct product line or format, or an unusual source-data observation.

\---

# What is not a Product Explorer nutrition warning

## Fresh / in-store prepared products

`fresh\_instore\_prepared` is removed from `warning\_types`.

Fresh or retailer-prepared format is not evidence that the nutrition data is wrong. It is a product-format / merchandising distinction, not a nutrition quality warning.

A fresh bakery item can still compete with a packaged snack for the same eating occasion. Physical aisle separation is therefore not sufficient reason to remove it from the analytical category or mark it with a nutrition warning.

For the current MVP:

```
do not show Fresh / in-store prepared as Warning
do not add a special Product Card badge solely for this purpose
```

If fresh-versus-packaged format later proves analytically useful, implement it as a separate governed product-format dimension, not as a nutrition warning.

\---

# Product Explorer inclusion logic

```
1. Preserve raw OFF nutrition values.
2. Run hard physical/structural gates.
3. If any hard gate fails:
      include\_in\_product\_table = False
      hide from Product Explorer
      keep in raw/QA data
      exclude from Market Overview display
      exclude from Market Overview calculations
4. If hard gates pass:
      include\_in\_product\_table = True
      show in Product Explorer
      include in Market Overview calculations
      keep eligible for Market Overview chart display
5. Evaluate warning logic:
      energy\_macro\_mismatch
      within\_brand\_nutrition\_outlier
6. Show one Warning = ! marker when one or both warning types are present.
7. Explain warnings only in the selected Product Card.
```

Product Explorer therefore has three outcomes:

|State|Product Explorer|Warning|Market Overview calculations|
|-|-|-|-|
|Passes hard gate, no warning|Show|blank|Include|
|Passes hard gate, warning present|Show|`!`|Include|
|Fails hard gate|Hide|n/a|Exclude|

Hard-excluded products remain available for QA/audit exports.

\---

# QA and validation approach

## Hard-gate validation

The most important Product Explorer validation metric is **precision**, not the percentage of products removed.

The desired question is:

> Among products hidden from Product Explorer, are virtually all of them genuine high-confidence contradictions?

False-positive hard exclusions are especially costly because the product disappears from the normal analytical interface.

Therefore:

```
prefer leaving a suspicious-but-possible product visible with Warning = !
over hiding a product that may be valid
```

## Warning validation

Warnings should also be high precision.

For each candidate warning rule, manually review stratified samples covering:

* regions;
* categories;
* severity bands;
* high-volume and low-volume brands;
* products with and without usable images;
* repeated patterns and isolated cases.

A warning rule should be promoted only when manual inspection shows that it reliably identifies observations that genuinely deserve caution.

## Existing energy-consistency testing

The project already tested multiple treatments of the 15% energy-macro difference rule and reviewed record-level outputs rather than accepting the threshold blindly.

Historical Scenario results:

|Scenario|Treatment|Excluded records|Excluded %|
|-|-|-:|-:|
|Scenario A|Current rules|19,635|5.18%|
|Scenario B|Re-include `small\_absolute\_kcal\_gap`|14,011|3.70%|
|Scenario C|Re-include `small\_absolute\_kcal\_gap` + `beverage\_energy\_not\_captured\_by\_macros`|8,574|2.26%|

Scenario C was then tightened into Scenario C2 after review showed that the broad re-inclusion bucket mixed non-material cases with records that still needed exclusion or audit.

Final Scenario C2 result recorded in the existing governance:

|Scenario|Treatment|Excluded records|Excluded %|
|-|-|-:|-:|
|Scenario A|Current rules|19,635|5.18%|
|Scenario C|Broad re-include of small-gap and beverage-formula buckets|8,574|2.26%|
|Scenario C2 locked|Guarded kcal-gap and beverage formula exceptions, with alcohol/fermented beverage auto-include capped at <=100 kcal/100g|11,437|3.02%|

These tests remain useful historical audit evidence. They no longer define Market Overview calculation exclusions. In the final governance, energy-macro inconsistency is a **warning layer after the hard gate**, with known alcohol/fermentation formula limitations handled before the warning is generated.

\---

# Market Overview governance

## Calculation population

Market Overview calculations use the complete Product Explorer-valid population:

```
include\_in\_product\_table = True
```

No additional nutrition-outlier exclusion is applied to calculations.

Therefore:

```
energy\_macro\_mismatch
within\_brand\_nutrition\_outlier
```

do **not** exclude products from Market Overview calculations.

Likewise, a product is not excluded from calculations merely because it falls into a Market Overview Lower 3% or Upper 3% chart range.

This is the final MVP rule:

> \*\*If the product passes Product Explorer impossibility gates, it is used in Market Overview calculations.\*\*

The only nutrition-governance products excluded from Market Overview calculations are products that fail Product Explorer hard validity gates.

\---

## Chart universe

Market Overview charts use the same Product Explorer-valid population:

```
include\_in\_product\_table = True
```

Product Explorer warnings do not invalidate products for chart display.

Chart readability is controlled separately through **precomputed, metric-specific selected-axis chart ranges**.

This is visualization governance, not data-quality governance.

\---

## Chart-range views

Each selectable chart axis offers four views:

```
Lower 3%
Middle 94%
Upper 3%
All
```

Default:

```
Middle 94%
```

The classification is metric-specific. A product can simultaneously be:

```
energy = Middle 94%
protein = Lower 3%
salt = Upper 3%
```

There is no global product-level tail classification.

### Percentile reference groups

For non-beverage categories, calculate by:

```
region × category × metric
```

For beverages, calculate separately by:

```
region × beverage\_view\_segment × metric
```

Launch regions:

```
FRANCE
UK\_IE
US\_CANADA
```

Launch categories:

```
snacks
cereals
dairies
beverages
```

For non-beverage categories, the implementation may represent the beverage segment key as a neutral/all value.

### Beverage segmentation

Beverages use the same four chart-range views as other categories, but percentile bounds are calculated independently inside each `beverage\_view\_segment`.

This prevents ready-to-drink beverages and beverage preparation/alcohol products from borrowing one another's percentile boundaries.

Existing beverage segments:

```
ready\_to\_drink\_beverages
beverage\_preparations\_and\_alcohol
unknown\_beverage\_segment
not\_beverage
```

Existing Market Overview beverage filter:

```
Default: Ready-to-drink beverages

Options:
All beverages
Ready-to-drink beverages
Beverage preparations and alcohol
Unknown beverage segment
```

The segmentation remains an MVP readability layer rather than a final beverage taxonomy.

\---

## Precomputed P03 / P97 boundaries

For each eligible reference group and metric, calculate from:

```
Product Explorer-valid rows only
non-null values only
```

Persist:

```
P03
P97
non\_null\_n
```

There must be **no interactive percentile calculation in Streamlit**.

The app consumes persisted percentile boundaries and persisted product band membership only.

### Metric band assignment

Each eligible non-null metric value is assigned one precomputed band:

```
L = Lower 3%   = value < P03
M = Middle 94% = P03 <= value <= P97
U = Upper 3%   = value > P97
```

Null values remain null and are not assigned to a band.

Boundary equality belongs to Middle 94%:

```
value == P03 -> M
value == P97 -> M
```

Do not rank-break tied values to force exactly 3% into each tail.

The user-facing names describe **percentile boundaries**, not guaranteed row shares. This is especially important for zero-heavy distributions such as ready-to-drink beverage protein density, where many products can legitimately equal the P03 boundary.

\---

## Two-axis scatter logic

Each selected chart axis has an independent range selector.

Example:

```
X-axis
Metric: Energy
Range: Middle 94%

Y-axis
Metric: Protein
Range: Upper 3%
```

Display a point only when both selected-axis conditions are satisfied.

Conceptually:

```
X condition
AND
Y condition
```

Examples:

```
X Middle 94% + Y Middle 94%
-> show products middle on both selected metrics

X All + Y Lower 3%
-> show all X values, but only products in the Y lower band

X Upper 3% + Y Middle 94%
-> show products upper on X and middle on Y
```

`All` removes only the band restriction for that selected metric.

It does **not**:

* reintroduce Product Explorer-invalid products;
* make null axis values plottable;
* change Market Overview calculation eligibility.

Do not apply a global rule such as:

```
outside P03/P97 on any metric -> hide product everywhere
```

A product outside the fibre range can still appear on an Energy × Protein chart if its energy and protein bands match the selected ranges.

\---

## Chart terminology and user-facing wording

Do not describe Lower 3% or Upper 3% products as:

* bad data;
* invalid;
* incorrect;
* misleading;
* category errors.

Many are legitimate product types.

Use neutral terminology:

```
Lower 3%
Middle 94%
Upper 3%
All
```

Recommended help text:

> Chart range uses precomputed nutrition percentiles for the selected metric. Middle 94% is the default for readability; Lower 3%, Upper 3%, and All remain available.

Do not claim that exactly 94% of products are plotted.

Actual plotted share can differ because:

* tied values may fall on P03/P97 boundaries;
* X and Y use an intersection;
* some products have null selected-axis values.

Use actual plotted counts in the UI.

\---

## Performance rule

No P03/P97 calculation may occur:

* on landing-page load;
* after changing region/category;
* after changing brand/company filters;
* after changing claims or product filters;
* after changing chart axes;
* after changing chart-range controls.

Percentile boundaries and metric bands are precomputed during the analytical build.

At runtime, Streamlit should only apply cheap predicates to already stored band values.

Conceptually:

```
BUILD TIME
    Product Explorer-valid population
        ->
    precompute P03 / P97
        ->
    assign metric bands
        ->
    persist bands

APP TIME
    selected region/category/segment
        ->
    selected X/Y metrics
        ->
    selected X/Y band filters
        ->
    plot
```

\---

## Locked beverage boundary validation — September 2026

A diagnostic review confirmed that beverage chart ranges are calculated and applied correctly by:

```
region × beverage\_view\_segment × metric
```

The implementation trace confirmed:

* bounds are segment-specific;
* persisted product band membership uses the same segment-specific bounds;
* Streamlit applies persisted bands after the selected beverage-segment filter;
* no inline percentile calculation is performed;
* no stale or duplicate segment band rows were found.

An earlier boundary implementation placed `value <= P03` into Lower 3%. This caused zero-heavy beverage metrics to remove large legitimate modal groups from Middle 94%.

The corrected locked rule is:

```
value < P03 -> Lower 3%
P03 <= value <= P97 -> Middle 94%
value > P97 -> Upper 3%
```

After correction, RTD Energy × Protein, g/100 kcal Middle 94% intersection rates were:

|Region|Energy M|Protein/kcal M|Both M|
|-|-:|-:|-:|
|FRANCE|96.78%|97.01%|94.15%|
|UK\_IE|96.87%|97.43%|94.39%|
|US\_CANADA|96.40%|96.99%|93.78%|

This confirms mathematically coherent selected-axis retention while preserving large legitimate zero-value modes.

\---

## Market Overview calculation and display summary

|Product state|Product Explorer|Market Overview calculations|Market Overview charts|
|-|-|-|-|
|Fails hard gate|Hide|Exclude|Exclude|
|Passes hard gate, no warning|Show|Include|Eligible; apply selected-axis chart range|
|Passes hard gate, warning|Show + `!`|Include|Eligible; apply selected-axis chart range|
|Lower 3% / Upper 3% on selected metric|Show|Include|Display only when selected range includes that band|
|Middle 94% on selected metric|Show|Include|Display by default when both selected axes are Middle 94%|
|`All` selected|Show|Include|Show all Product Explorer-valid, non-null selected-axis values|

\---

# Audit outputs

The nutrition-quality workflow currently writes local audit files such as:

```
data/nutrition\_outlier\_review/audits/hard\_data\_quality\_errors.csv
data/nutrition\_outlier\_review/audits/energy\_macro\_inconsistency\_15pct.csv
data/nutrition\_outlier\_review/audits/energy\_macro\_accepted\_exceptions.csv
data/nutrition\_outlier\_review/audits/genuine\_outliers.csv
data/nutrition\_outlier\_review/audits/category\_scope\_outliers.csv
data/nutrition\_outlier\_review/audits/nutrition\_quality\_summary\_by\_region\_category.csv
data/nutrition\_outlier\_review/audits/nutrition\_quality\_flags.csv
data/nutrition\_outlier\_review/audits/distributional\_plausibility\_tail\_summary.csv
data/nutrition\_outlier\_review/audits/distributional\_plausibility\_tail\_examples.csv
data/nutrition\_outlier\_review/audits/beverage\_view\_segment\_audit.csv
```

Chart-range QA outputs include or may include:

```
market\_overview\_chart\_percentile\_bounds.csv
market\_overview\_chart\_band\_summary.csv
beverage\_percentile\_bounds\_verification.csv
beverage\_band\_validation\_summary.csv
```

These remain QA / governance artifacts rather than public Product Explorer outputs.

\---

# Historical implementation record

The following points are retained because they explain how the current approach was reached.

## 2026-08-22 — Basic impossible values

Initial hard checks covered:

```
energy\_kcal < 0
energy\_kcal > 900
protein\_100g < 0
carbs\_100g < 0
fat\_100g < 0
sugars\_100g < 0
saturated\_fat\_100g < 0
fiber\_100g < 0
salt\_100g < 0
```

Raw OFF values were preserved before compatibility transformations.

## 2026-08-22 — Per-100g structural checks

The initial implementation tested:

```
protein\_100g > 100
carbs\_100g > 100
fat\_100g > 100
fiber\_100g > 100
salt\_100g > 100
sugars\_100g > carbs\_100g
saturated\_fat\_100g > fat\_100g
protein\_100g + carbs\_100g + fat\_100g > 105
```

The macro-sum threshold had already been moved from `>100g` to `>105g` after review found small excesses attributable to rounding.

The current Product Explorer governance retains `>105g` and additionally adds explicit tolerance to the sugars/carbohydrate and saturated-fat/fat relational checks.

## 2026-08-22 — Per-100 kcal checks

Historical implementation used tolerant density checks around:

```
protein > 28g / 100 kcal
carbs   > 28g / 100 kcal
fat     > 12.5g / 100 kcal
```

The current Product Explorer governance **removes carbohydrate density from the hard gate** because the 4 kcal/g assumption is not universally valid for reported carbohydrate.

Protein and fat retain conservative hard thresholds.

## 2026-08-22 to 2026-08-23 — Energy consistency testing

The energy formula:

```
4 \* protein + 4 \* carbs + 9 \* fat
```

was tested with progressively tighter percentage thresholds and then reviewed through a 36-row image-backed sample stratified across MVP region-category combinations.

The later Scenario A/B/C/C2 work demonstrated that a single percentage threshold was too blunt, especially for low-energy beverages and products whose energy is not fully represented by the simple macro formula.

The final conclusion is:

```
energy-macro mismatch = Product Explorer warning candidate
not a hard physical-impossibility gate
not a Market Overview calculation exclusion
```

Known alcohol/fermentation formula limitations should be handled before generating the warning.

## Distributional plausibility review

The tail review established an important principle:

```
Extreme is not the same as wrong.
```

Category tails often contain stable, legitimate product-format clusters. Therefore broad percentile or category thresholds should not automatically hide products from Product Explorer.

This review motivated the now-locked `within\_brand\_nutrition\_outlier` Product Explorer warning layer.

\---

# Current implementation status

|Component|Status|
|-|-|
|Raw OFF nutrition preservation|Locked|
|Product Explorer hard impossibility gates|Locked|
|Negative values / >100g / >900 kcal checks|Locked|
|Macro mass-balance hard gate|Locked at `>105g`|
|Sugars > carbs relational test|Locked with 0.5g tolerance|
|Saturated fat > fat relational test|Locked with 0.5g tolerance|
|Minimum implied energy lower-bound rule|Locked|
|Salt-aware minimum-known-mass rule|Locked|
|Salt sanity boundary|Locked at `>50g/100g`|
|Protein per-100 kcal hard gate|Locked at `>28`|
|Fat per-100 kcal hard gate|Locked at `>12.5`|
|Carbs per-100 kcal hard gate|Removed|
|Energy-macro mismatch|Locked Product Explorer warning|
|Alcohol/fermented 4/4/9 handling|Locked exception logic|
|Within-brand nutrition outlier|Locked Product Explorer warning|
|`fresh\_instore\_prepared` warning|Removed|
|Product Explorer Warning column|One `!` marker for two warning types|
|Market Overview calculation population|All Product Explorer-valid products|
|Market Overview chart universe|All Product Explorer-valid products|
|Market Overview chart ranges|Lower 3%, Middle 94%, Upper 3%, All|
|Default chart range|Middle 94%|
|X/Y chart ranges|Independent|
|Beverage chart ranges|Segment-specific|
|P03/P97 boundary equality|Middle 94%|
|Inline percentile calculation in Streamlit|Not allowed|

\---

# Final working principle

```
Do not correct the source data.
Do not silently delete raw observations.

Product Explorer:
Hide only high-confidence physical contradictions.
Show all other credible products.
Use neutral warnings for suspicious-but-possible observations.

Market Overview calculations:
Use every product that passes the Product Explorer hard gates.
Warnings do not exclude products.

Market Overview charts:
Use the same Product Explorer-valid population.
Control readability only through precomputed selected-axis chart ranges:
Lower 3%, Middle 94%, Upper 3%, All.

Chart-range membership is not a data-quality judgement.
```
