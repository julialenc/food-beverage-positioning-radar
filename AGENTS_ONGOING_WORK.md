# Food & Beverage Positioning Radar — Ongoing Work Brief

Use this as the small handoff for a fresh chat.

## Locked Context

Repo/app are clean after the 2026-09-03 launch mapping cleanup, the 2026-09-06
nutrition-quality / Market Overview governance closeout, and the 2026-09-08
docs/data/pipeline restructuring.

Locked:

- retailer/private-label mapping;
- Top 9 company mapping;
- France and US/Canada regional-category orphan cleanup;
- UK/Ireland orphan scan at `>=100` products per region-category-brand;
- snack/cereal category cleanup, plus GTIN corrections found during audits;
- nutrition-quality governance for Product Explorer and Market Overview;
- beverage segmentation and precomputed chart-range controls as MVP Market
  Overview chart-readability layers;
- docs/, data/, and pipeline/ naming/navigation structure.

Do not reopen these unless Julia explicitly asks.

## Non-Negotiable Rules

- Default is review only. Edit/create/delete/commit only after Julia says
  `IMPLEMENT`.
- Preserve raw Open Food Facts values.
- NULL is not zero.
- Do not silently correct nutrition, categories, brands, or ownership.
- Add derived flags/reasons and separate app treatment fields instead.
- Product Explorer can show imperfect useful records unless a hard validity
  gate excludes them.
- Product Explorer hard validity gates define the usable population for Market
  Overview calculations.
- Market Overview charts use the same valid population; chart-range controls
  affect visualization only and are not data-quality judgments.
- Exact reviewed GTIN overrides outrank broad rules.

## Brand/Company Architecture

Keep layers separate:

```text
off_brands_raw
brand_entity_raw
normalized_brand
brand_family
resolved_company
```

`resolved_company` is directional navigation/reporting, not legal ownership.
False negatives are better than false-positive owner assignments.

## Current Status

The docs/, data/, pipeline/, database/, pages/, and shared/ passes are aligned
for launch. Streamlit Cloud deployment testing is in progress after hotfixes
that prefer the packaged public database artifact, validate extracted artifacts,
defer initial Market Overview data loading, and harden public-database queries.

The deployed app now shows the selected scope and waits for an explicit
`Load selected market data` action before loading the default France/snacks
Market Overview data. Streamlit Cloud may throttle the app temporarily during
repeated deploy/test cycles.

## Next Priorities

1. Confirm the Streamlit Cloud deployment loads correctly after throttling ends.
2. Update `docs/ONBOARDING.md` once the launch state is final.
3. Do a final root-level documentation check if needed before sharing.
4. After launch, create separate future tasks for segmentation or other feature
   work.
5. Measure and optimize loading time only from observed bottlenecks.

## Files To Read First

- `README.md`
- `docs/ONBOARDING.md`
- `pipeline/README_NAVIGATING_PIPELINE.md`
- `data/README_NAVIGATING_DATA.md`
- relevant governance doc:
  - `docs/01_PRODUCT_DATA_GOVERNANCE/03_NUTRITION_QUALITY_GOVERNANCE.md`
  - `docs/01_PRODUCT_DATA_GOVERNANCE/01_CATEGORY_SCOPE_AND_CLEANUP.md`
  - `docs/01_PRODUCT_DATA_GOVERNANCE/02_BRAND_COMPANY_MAPPING.md`
  - `docs/03_PROJECT_REFERENCE/02_METHODOLOGY.md`
  - `docs/03_PROJECT_REFERENCE/03_LIMITATIONS.md`

## Working Pattern

For each change:

```text
inspect current state -> map dependencies/evidence -> Julia reviews when needed ->
IMPLEMENT -> validate -> document -> commit if requested
```

Do not reopen locked mapping, category, nutrition, or Market Overview governance
unless Julia explicitly asks.
