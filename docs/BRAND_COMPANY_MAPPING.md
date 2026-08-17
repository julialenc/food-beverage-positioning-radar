# Brand and company mapping

This document explains how brand strings from Open Food Facts are normalized
and mapped to parent companies, what the mapping covers, and what it
deliberately does not attempt.

The mapping file itself is at `data/reference/company_brand_mapping.csv`.
Brand-alias cleanup is maintained separately in
`data/reference/brand_alias_mapping.csv`; see "Two mapping layers" below.

## Purpose

Open Food Facts brand strings are entered by contributors and are often
inconsistent, fragmented, or multi-valued. A single product may list its
brand as "Nestlé", "nestle", or "Nestlé France", and the same underlying
brand appears under different parent companies depending on the market (see
known complications below). This mapping exists to support company-level
filtering and cautious company roll-up in the Streamlit app.

All claim-pattern analysis and benchmark-flag computation is performed at
brand level, not company level, since a parent company's portfolio is
typically too heterogeneous to support meaningful company-level findings.
Company mapping is provided for navigation and filtering — to allow a user
to ask "show me all products I associate with Nestlé" — not for aggregate
scoring across a portfolio.

Company / owner is resolved using project brand mapping and, for
market-specific brands, Open Food Facts country tags or derived project region
codes. This is a directional ownership filter, not a legal ownership audit.

## Two mapping layers

The repository has two separate brand-reference layers:

- `data/reference/brand_alias_mapping.csv` maps observed brand variants to a
  canonical brand string. Confirmed rows are applied during cleaning in
  `pipeline/clean.py`, before products are loaded into the database.
- `data/reference/company_brand_mapping.csv` maps canonical `primary_brand`
  values to parent companies or scoped ownership-resolution rows. It is not
  used to compute claim taxonomy.

This distinction matters: changing an alias can change stored
`products.primary_brand` values after re-cleaning/reloading, while changing
the company mapping changes company filters and derived company labels without
changing product-level claim classifications.

The company mapping CSV now includes scoped ownership metadata, but the current
Streamlit reader still uses a simple `parent_company -> primary_brand_db`
lookup. The scoped resolver described below is the intended next logic for the
Company / owner filter, not yet the current app behavior.

## File structure

`data/reference/company_brand_mapping.csv` has twelve columns:

| Column | Description |
|---|---|
| `parent_company` | Current reference parent company maintained for this project, or `Manual review` for rows that should not be attributed to a resolved owner without additional evidence. Reflects the latest project review, not historical ownership and not a guarantee of current legal ownership in every market. |
| `brand` | The brand name as it commonly appears in the source data or in market usage. |
| `primary_brand_db` | The normalized form of the brand used as a join key to `products.primary_brand` in the database — lowercased, accent-stripped, comma-normalized. This is the field used for all joins. |
| `category` | Broad product category the brand is primarily associated with. Not a hard constraint — brands may appear in other categories in the actual data. |
| `hq_country` | Headquarters country of the parent company (ISO 2-letter code), as a reference point for company-level geographic context. |
| `notes` | Analyst notes on brand-ownership caveats, licensing conflicts, market-scope limitations, or acquisition status. These are methodologically important and should be read before using a brand in company-level analysis. |
| `ownership_resolution_status` | Ownership-resolution mode: `direct`, `market_scoped`, or `manual_review`. |
| `market_scope` | Human-readable scope for market-specific rows, e.g. `US / Canada` or `Europe / many non-US CPW markets`. |
| `country_tags_include` | Optional pipe-separated OFF country tags that include this row's scope. Currently reserved for future resolver logic. |
| `country_tags_exclude` | Optional pipe-separated OFF country tags that exclude this row's scope. Currently reserved for future resolver logic. |
| `region_codes_include` | Optional pipe-separated project region codes that include this row's scope, e.g. `US_CANADA` or `FRANCE|UK_IE|DACH`. |
| `product_scope_note` | Human-readable note explaining when the row should be applied or sent to manual review. |

`ownership_resolution_status` has three allowed values:

- `direct`: safe enough one-brand-to-one-owner mapping for this project.
- `market_scoped`: ownership depends on market, region, country tags, or
  product scope.
- `manual_review`: do not attribute to a real owner without additional review.

Duplicate `primary_brand_db` values are allowed only for scoped ownership
cases. In the current file, the duplicate scoped keys are `cheerios`,
`kellogg's`, and `kitkat`.

## Coverage

The current mapping file contains 407 rows across 101 parent-company values,
selected on the basis of brand presence in the actual Open Food Facts product
data and prominence in the markets currently covered by the project. It covers
snacks, beverages, breakfast cereals, dairy, dairy drinks, plant-based products,
biscuits, bars, powder drinks, and related categories. It is not exhaustive
relative to the full universe of brands present in the underlying data.

Brands not in this mapping remain in the dataset and are fully analysable
at brand level — they simply do not appear in the company-level filter.

## Known complications and mapping decisions

Several situations in this mapping require interpretation rather than a
clean one-to-one relationship between brand and parent company. The most
important are documented here.

**Kellogg's brand split.** Following the 2023 Kellogg Company spin-off and
the subsequent Kellanova/Mars and WK Kellogg/Ferrero acquisitions, the
Kellogg's brand mark can appear on products with different corporate parents.
North American cereal ownership is scoped to Ferrero; international cereal and
snack ownership is scoped to Mars. Generic `kellogg's` rows are therefore
represented as `market_scoped` rows plus a `manual_review` fallback. Specific
brand keys such as `frosted flakes`, `froot loops`, `special k north america`,
`special k international`, `rice krispies treats`, and `kashi` should remain
distinct rather than collapsing into generic `kellogg's`.

**KitKat.** Nestlé owns the KitKat brand globally except in the United
States, where Hershey manufactures and sells KitKat under a perpetual
license. Generic `kitkat` is now represented as scoped rows: Nestlé for
covered non-US markets, Hershey for US/Canada scope, and `Manual review` when
country tags are missing, conflicting, or outside scoped rules. A `kitkat us`
helper key remains for future alias or market-aware logic, but generic
`kitkat` must not be treated as a direct universal Nestlé mapping.

**Cheerios.** In most markets outside the United States, Cheerios is a
Cereal Partners Worldwide (CPW) brand, a Nestlé/General Mills joint
venture. In the United States and Canada, Cheerios is a General Mills brand.
In Australia and New Zealand it is distributed through CPW but marketed under
the Uncle Tobys brand name. The CSV therefore keeps scoped `cheerios` rows for
General Mills and CPW plus a `Manual review` fallback for missing,
conflicting, or out-of-scope country tags.

**Kellanova brands now under Mars.** As of August 2024, Mars completed
the acquisition of Kellanova, bringing Pringles, Cheez-It, Pop-Tarts,
RxBar, NutriGrain, and other brands into the Mars portfolio. These are
mapped under Mars in this file. Products in the database ingested before
the acquisition date may carry different brand-owner attribution in their
source records.

**Danone / Huel.** Danone announced a definitive agreement to acquire Huel
in March 2026, but Huel is not mapped to Danone until formal closing is
confirmed. The current CSV keeps `huel` under `Huel` with a note that the
announced transaction should be revisited.

**Fonterra consumer brands / Lactalis.** Fonterra sold the majority of its
consumer brands (Anchor, Mainland, Anlene, Anmum, Kapiti, Bega license)
to Lactalis in most markets. An exception applies: Fonterra retained the
Anchor consumer business in Greater China. The mapping reflects this split.

**Accent normalization.** `primary_brand_db` values are accent-stripped to
match the normalization applied in `clean.py` (NFKD encoding, ASCII
coercion). For example, `gerblé` is stored as `gerble`, `côte d'or` as
`cote d or`. Any join between this file and the database must use
`primary_brand_db`, not `brand`.

## Resolver priority

The intended ownership resolver should use this priority order:

1. Normalize brand via `brand_alias_mapping.csv`.
2. Find all `company_brand_mapping.csv` rows for `primary_brand_db`.
3. If `market_scoped` rows exist, evaluate region, country, and product-scope
   rules first.
4. If exactly one scoped row matches, assign that `parent_company`.
5. If no scoped row matches and a `manual_review` fallback exists, assign
   `Manual review`.
6. If exactly one `direct` row exists and no scoped conflict exists, assign
   that `parent_company`.
7. If multiple rows remain or no rule applies, assign `Manual review`.

The current Streamlit app does not yet implement this resolver. Until it does,
scoped duplicate keys should be treated as a data-model contract and not as
fully resolved app behavior.

## What this mapping does not cover

- **Historical ownership.** Brands are mapped to their parent company as
  a current reference layer for this project. The mapping does not track
  pre-acquisition ownership or attempt to reconstruct historical company
  structures.
- **Sub-brand or product-line detail.** Each row is a brand, not an
  individual product line. Where product-line distinctions are necessary for
  ownership, the CSV uses scoped rows and notes rather than pretending the
  base brand alone resolves ownership.
- **Non-Western European / North American markets.** Coverage prioritises
  the markets most represented in the current project data. Brand ownership
  in South and Southeast Asia, Latin America, and Africa may differ materially
  from what is shown here.
- **Legal compliance or current accuracy.** This is a reference mapping
  for analytical navigation, not a legal document. Ownership structures
  can change; always verify before use in any context where accuracy of
  company attribution is material.

## How to update

When a brand acquisition, spin-off, or ownership change occurs that affects
products in the current dataset:

1. Update `parent_company` in `company_brand_mapping.csv`.
2. Add a note in the `notes` column describing the change and its
   effective date.
3. Set `ownership_resolution_status`:
   - use `direct` for straightforward one-brand-to-one-owner rows;
   - use `market_scoped` when market, region, country tags, or product scope
     determine ownership;
   - use `manual_review` when a row should not be attributed to a resolved
     owner.
4. If a brand splits or is licensed differently by market, add scoped duplicate
   rows with the same `primary_brand_db` where needed, plus a `manual_review`
   fallback. Fill `region_codes_include`, `country_tags_include`, and
   `product_scope_note` as far as the available evidence supports.
5. Commit with a message referencing the acquisition or change:
   `data: update brand mapping for [event] ([date])`.
6. If `company_brand_mapping.csv` changes only parent-company attribution,
   no claim-taxonomy rerun is needed; the Streamlit app reads the file for
   company filters and derived company labels. If `brand_alias_mapping.csv`
   changes canonical brand strings, re-run the cleaning/loading stages so
   `products.primary_brand` is regenerated before relying on the updated
   mapping.
