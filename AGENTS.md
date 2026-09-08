# Food & Beverage Positioning Radar — Agent Rules

This project is an audit-sensitive Streamlit analytics board built from Open
Food Facts. Treat it as analytical data governance work, not generic software
cleanup.

## Start Here

Before editing, read:

1. `README.md`
2. `docs/ONBOARDING.md`
3. the relevant governance doc:
   `docs/03_PROJECT_REFERENCE/02_METHODOLOGY.md`, `docs/03_PROJECT_REFERENCE/03_LIMITATIONS.md`,
   `docs/01_PRODUCT_DATA_GOVERNANCE/01_CATEGORY_SCOPE_AND_CLEANUP.md`, `docs/01_PRODUCT_DATA_GOVERNANCE/02_BRAND_COMPANY_MAPPING.md`,
   `docs/01_PRODUCT_DATA_GOVERNANCE/03_NUTRITION_QUALITY_GOVERNANCE.md`, or
   `docs/03_PROJECT_REFERENCE/04_DATA_DICTIONARY.md`

For short ongoing-context handoff, also read `AGENTS_ONGOING_WORK.md` when
present.

## Change Control

Default mode is **review only**.

Unless Julia explicitly says `IMPLEMENT`, do not modify, create, rename, move,
delete, retire, commit, or push files.

Before edits, state:

- what is wrong;
- what you will change;
- what will remain unchanged.

After edits, show the diff summary and validation performed.

For deletion/retirement/renaming, first search references to the file name,
outputs, functions, and generated files. Never remove production artifacts just
because they look old.

## Data Rules

- Open Food Facts is crowdsourced and can be wrong.
- Preserve raw/source values; never silently correct OFF nutrition or brand
  source fields.
- NULL is not zero. Missing, empty, failed, and declared-zero values are
  different states.
- Add flags, reasons, derived fields, or inclusion/exclusion fields instead of
  overwriting source evidence.
- Product Explorer can show imperfect but useful records unless a hard
  exclusion applies.
- Product Explorer hard validity gates define the usable population for Market
  Overview calculations.
- Market Overview charts use the same valid population; precomputed chart-range
  controls affect visualization only and are not data-quality judgments.
- Exact reviewed GTIN overrides outrank broad category/brand/company rules.

## Locked State

The MVP is launched and the repo was cleaned/committed on 2026-09-03. The
nutrition-quality / Market Overview governance stage was locked and pushed on
2026-09-06. The docs, data, and pipeline folder structures were reorganized and
aligned on 2026-09-08.

Locked for current MVP scope:

- retailer/private-label mapping;
- Top 9 company mapping;
- France and US/Canada regional-category orphan cleanup;
- UK/Ireland orphan scan at the `>=100` region-category threshold;
- snack/cereal category cleanup, plus exact GTIN corrections found during
  mapping/orphan audits;
- nutrition-quality governance for Product Explorer and Market Overview;
- beverage view segmentation and precomputed chart-range controls for Market
  Overview charts;
- docs/, data/, and pipeline/ navigation structure and naming.

Brand layers stay separate:

```text
off_brands_raw -> brand_entity_raw -> normalized_brand -> brand_family
resolved_company is a directional owner/navigation field, not legal truth
```

Do not reopen locked mapping definitions unless Julia explicitly asks.

## Current Priorities

The repository cleanup is closed for docs/, data/, and pipeline/. Next work
should focus on:

1. confirming the Streamlit Cloud deployment is stable after launch hotfixes;
2. updating `docs/ONBOARDING.md` after the launch state is final;
3. reviewing any remaining post-launch documentation coherence;
4. measuring and optimizing loading time where user testing shows a real
   bottleneck;
5. creating future feature tasks only after launch, such as segmentation.

For these, follow:

```text
raw source value -> preserved
derived interpretation -> flagged
app treatment -> controlled by inclusion/display fields
```

For renaming/cleanup, search references first and preserve dependency chains.
For performance work, measure current behavior before changing code.
