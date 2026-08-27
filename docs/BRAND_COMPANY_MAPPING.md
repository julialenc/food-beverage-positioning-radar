# Brand and company mapping

This document explains how brand strings from Open Food Facts are normalized
and mapped to parent companies, what the mapping covers, and what it
deliberately does not attempt.

The mapping file itself is at `data/reference/company_brand_mapping.csv`.
Brand-alias cleanup is maintained separately in
`data/reference/brand_alias_mapping.csv`; see "Two mapping layers" below.

## Final MVP lock state — 2026-08-25

The launch mapping layer is frozen for MVP with known caveats. The current
pipeline separates brand/company work into these layers:

```text
off_brands_raw      = raw Open Food Facts brand evidence
brand_entity_raw    = conservative extracted consumer-facing brand entity
normalized_brand    = cleaned brand or stable brand line used by Streamlit
brand_family        = optional broader umbrella for useful roll-ups
resolved_company    = directional company / owner routing used for filtering and navigation
```

Launch decisions now locked:

- Carrefour private-label mapping is frozen as a pilot and is not expanded to
  other private labels before MVP launch.
- Top 9 strategic company routing has been merged into
  `data/reference/company_brand_mapping.csv`.
- Controlled Nestlé snack product-name recovery is implemented for approved
  France, UK/Ireland, and US/Canada snack cases only.
- Top 9 prefix-orphan cleanup has been applied only where Julia approved strict
  allow/reject decisions.
- Streamlit must not display `Manual review` as a company / owner. Remaining
  unresolved or unsafe ownership cases appear as `Other / not mapped to a
  company` or as a scoped launch label, while backend review status remains
  available separately.

Known residual issues are accepted for MVP unless they create visible launch
credibility problems. For example, Alprose can remain a known edge case rather
than reopening broad prefix matching.

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

## MVP brand-mapping workflow

The launch brand-mapping review follows a three-stage sequence. The order is
important: do not jump directly from raw Open Food Facts brand strings to
parent-company ownership, because that creates avoidable attribution errors.

```text
1. Bottom-up brand unification
2. Top-down strategic company portfolio coverage
3. Other-big unresolved brand prioritisation
```

### Three analytical levels

Brand mapping uses three separate levels:

```text
A. Raw brand
   Exactly what Open Food Facts provides in the `brands` field.
   Examples: Coca Cola; coca-cola; Coke; Coca Cola Zero.

B. Normalized brand
   The cleaned brand entity used for brand-level analysis.
   Example: Coca-Cola.

C. Parent company / owner
   The assigned owner or company filter label, sometimes scoped by market.
   Example: The Coca-Cola Company.
```

For MVP, every review output should preserve enough evidence to move from
raw brand to normalized brand to parent company without losing traceability.

### Stage 1: bottom-up brand unification

Purpose: reduce messy observed brand variants into one normalized brand entity.

This stage does not assign company ownership. It only proposes that multiple
raw strings probably refer to the same brand.

Example:

```text
cocacola
coca
coca cola
coca-cola
Coca Cola Zero
Coca-Cola
-> Coca-Cola
```

Minimum bottom-up audit columns:

```text
country_or_market
observed_market_region_codes
category
raw_brand
normalized_brand_candidate
product_count
example_product_names
mapping_reason
review_note
```

Generated local audit output:

```text
data/brand_mapping_review/brand_alias_suggestions_bottom_up.csv
data/brand_mapping_review/brand_alias_suggestions_bottom_up_reviewed.csv
data/brand_mapping_review/brand_alias_bottom_up_review_summary.csv
```

The first file is the raw cluster audit. The reviewed file adds a conservative
decision layer for launch-stage review:

```text
approve_alias
reject_generic_alias
manual_review_private_label_line
manual_review_repeated_prefix
manual_review_parent_brand_mix
manual_review
defer_to_top_down_portfolio_mapping
```

For MVP, fewer reliable aliases are preferred over aggressive normalization.
A false merge is worse than leaving a brand unresolved.

Approved bottom-up aliases are limited to strings that clearly refer to the
same consumer-facing brand or retailer/private-label brand, such as spelling,
punctuation, spacing, apostrophe, hyphen, accent, legal-suffix, or confirmed
alias variants.

Generic descriptors must not become normalized brands on their own. Examples
include `bio`, `organic`, `natural`, `simply`, `classic`, `selection`,
`premium`, `original`, `protein`, `societe`, `company`, and `market`. For
example, `Bio Village`, `Bio Company`, `Bio Today`, and `Bio c' Bon` should
not be collapsed to `Bio` just because they share a generic descriptor.

Private-label subbrands must also remain distinct at brand level. For example,
`lidl solevita` and `lidl lord nelson` should not be collapsed to `lidl` in
Stage 1. Variant spellings of the same private-label subbrand can be unified
with that subbrand, while the later company-mapping stage can assign both
subbrands to Lidl as the company / owner.

Retailer banners and retailer private-label lines are not the same brand-level
entity. `Carrefour`, `Tesco`, `Sainsbury's`, `Auchan`, `Monoprix`, `Casino`,
and similar retailer banners can exist as brands, but retailer-line strings
such as `Carrefour Bio`, `Carrefour Classic`, `Tesco Finest`,
`Tesco Free From`, `Sainsbury's Taste the Difference`, `Monoprix Gourmet`,
`Casino Délices`, `Auchan Mmm`, `U Saveurs`, and `U Bio` must not be
automatically collapsed to the retailer banner. These are kept as full
brand-line candidates where possible or marked `manual_review_private_label_line`.

Some Lidl/Aldi-style private-label subbrands are treated as separate brand
entities rather than retailer banners. For example, `milbona lidl`,
`lidl milbona`, `sondey lidl`, `bellarom lidl`, `solevita lidl`, and
`crownfield aldi` should normalize toward the subbrand, not to `lidl` or
`aldi`.

Parent-company and portfolio-brand cases are deferred to Stage 2 rather than
resolved bottom-up. For example, `nestle nesquik` should not be normalized to
`Nestlé` in Stage 1; it should be treated as a portfolio-brand case for the
top-down company-portfolio review.

Dirty repeated-prefix strings are not approved automatically. Examples include
`nestle nestle dessert`, `coca-cola coca-cola light`,
`carrefour carrefour original`, `u u tout petits`, `hy-vee hy-vee inc`,
`lindt lindt and sprungli`, and `monster monster energy`. The script collapses
the repeated adjacent prefix for audit readability, but these rows are marked
`manual_review_repeated_prefix` unless the pattern is separately approved.

Strategic parent/company prefixes mixed with portfolio-brand text are also not
bottom-up approvals. Examples include `nestle nescafe`,
`nestle san pellegrino`, `nestle kit kat`, `danone activia`,
`mondelez oreo`, and Coca-Cola portfolio mixes such as `fanta the coca-cola
company` or `dr pepper coca cola`. These are deferred to top-down portfolio
mapping or marked `manual_review_parent_brand_mix` when the portfolio signal is
unclear.

#### Carrefour private-label pilot

As of 24 August 2026, Stage 1 includes a Carrefour-only curated private-label
test reference at `data/reference/private_label_brand_mapping.csv`. This is a
controlled pilot before expanding the same approach to Tesco, Sainsbury's,
ASDA, Auchan, Monoprix, Casino, U, E.Leclerc, Lidl, Aldi, and other retailers.

The Carrefour pilot is applied before confirmed aliases, repeated-prefix
cleanup, punctuation heuristics, and product-line suffix stripping. Its purpose
is to prevent meaningful Carrefour private-label lines from collapsing to the
retailer banner. Examples:

```text
carrefour bio -> Carrefour Bio
carrefour classic -> Carrefour Classic
carrefour extra -> Carrefour Extra
carrefour original -> Carrefour Original
carrefour selection -> Carrefour Sélection
reflets de france -> Reflets de France
simpl -> Simpl
filiere qualite carrefour -> Filière Qualité Carrefour
carrefour kids -> Carrefour Kids
carrefour baby -> My Carrefour Baby / manual review
my carrefour baby -> My Carrefour Baby
carrefour companino -> Carrefour Companino
companino -> Carrefour Companino
```

On 24 August 2026, the Carrefour pilot was stabilized at raw-brand row level:
after Carrefour-specific cleaning, any `cleaned_brand_key` that exactly matches
a confirmed row in `private_label_brand_mapping.csv` must use the curated
canonical brand. This curated match overrides repeated-prefix handling,
heuristic approval, confirmed-alias fallback, and product-line suffix stripping.
For example, `carrefour bio carrefour` and `carrefour carrefour bio` both clean
to `carrefour bio` and therefore map to `Carrefour Bio`.

Curated Carrefour rows use `mapping_source =
curated_private_label_mapping`. Confirmed rows are approved; rows explicitly
marked `manual_review` in the reference, such as `carrefour discount` and
`fqc`, remain `manual_review_private_label_line`.

The primary Carrefour-only audit output is row-level, not cluster-level:

```text
data/brand_mapping_review/carrefour_private_label_row_level_audit.csv
```

Each row represents one raw brand value after Carrefour-specific cleaning. This
prevents mixed clusters such as `carrefour`, `carrefour kids`, `carrefour
sensation`, and `carrefour market` from being treated as one brand.

The secondary cluster-level Carrefour audit is:

```text
data/brand_mapping_review/carrefour_private_label_mapping_audit.csv
```

The review decision from these files should feed
`data/reference/brand_alias_mapping.csv` only after manual approval.

#### Brand layer activation and Nestle snacks recovery

On 24-25 August 2026, the project separated brand handling into three
traceable layers in `pipeline/clean.py` and activated the cleaned brand layer
in the Streamlit database helpers.

The product table now preserves the original OFF brand fields and exposes
separate derived brand fields:

```text
off_brands_raw
off_brand_tokens
legacy_primary_brand
brand_entity_raw
brand_entity_source
normalized_brand
brand_alias_source
brand_alias_review_status
```

`primary_brand` remains in the database as a legacy compatibility/provenance
field. Streamlit uses `normalized_brand` as the displayed brand where present,
falling back to `primary_brand` only when no normalized brand is available.
This keeps existing pages working while moving brand display and company
resolution to the new brand layer.

For Product Explorer performance, `pipeline/load.py` also precomputes
`products.resolved_company` during the SQLite load. Product Explorer filters
company selections directly in SQL against this indexed field. It must not
resolve company ownership dynamically in Python on every Streamlit rerun,
because selecting a company or ticking a product row reruns the page and can
otherwise force repeated full-scope ownership resolution.

The first targeted product-name recovery rule was added for high-confidence
Nestle snack rows. This rule exists because OFF sometimes lists only `Nestle`
in the structured `brands` field even when the product name clearly contains
the consumer-facing portfolio brand. The rule is deliberately narrow and is
not a general product-name brand extractor.

The recovery rule applies only when all of these are true:

```text
query_category = snacks
legacy_primary_brand = nestle
brand_entity_source = first_off_brand_token_fallback
brand_entity_raw = nestle
product name contains an approved high-confidence portfolio pattern
country/region is one of the explicitly approved MVP scopes
```

Approved scopes and patterns:

```text
France snacks:
KitKat / Kit Kat
Les Recettes de l'Atelier / L'Atelier
Nestle Dessert
Perugina
After Eight
Galak
Lion
Smarties
Crunch
Nesquik
Aero
Fitness
Quality Street
Rolo
Milkybar / Milky Bar
Chocapic
Balaton

UK/Ireland snacks:
KitKat / Kit Kat
Aero
Smarties
Yorkie
Milkybar / Milky Bar

US/Canada snacks:
KitKat / Kit Kat
Smarties
```

The source labels are region-specific:

```text
product_name_recovery_nestle_france_snacks
product_name_recovery_nestle_uk_ie_snacks
product_name_recovery_nestle_us_canada_snacks
```

Examples of allowed recovery:

```text
OFF brands = Nestle
product_name = Classic KitKat
normalized_brand = KitKat

OFF brands = Nestle
product_name = After Eight Dark Chocolate Thins
normalized_brand = After Eight

OFF brands = Nestle
product_name = Aero Peppermint Chocolate Bar
normalized_brand = Aero
```

Examples intentionally not recovered:

```text
Chocolat noir
Chocolat au lait
Brownie au chocolat
Buche glacee
Barre cereales
Candy
Bars
Dessert Lait
Fins Plaisirs
Fondant Caramel
Clusters
```

These remain under Nestle or future manual review unless a curated
high-confidence brand rule is approved.

The active validation snapshot after this stage was loaded from:

```text
data/sample/clean_20260824_223104.csv
database/positioning_radar.db ingestion timestamp 20260824_223415
```

The controlled Nestle recovery produced 362 recovered rows:

```text
KitKat: 124
Les Recettes de l'Atelier: 87
Lion: 22
Smarties: 20
Galak: 19
Fitness: 16
Aero: 16
Milkybar: 14
Nestle Dessert: 11
Crunch: 10
Nesquik: 10
Yorkie: 6
After Eight: 4
Balaton: 2
Rolo: 1
```

Post-load checks confirmed that market-scoped ownership still applies after
brand recovery:

```text
KitKat + US_CANADA -> The Hershey Company
KitKat + FRANCE/UK_IE -> Nestle
Smarties + US_CANADA -> Smarties Candy Company
Smarties + UK_IE -> Nestle
```

Audit outputs:

```text
data/brand_mapping_review/brand_entity_extraction_review.csv
data/brand_mapping_review/brand_alias_normalization_review.csv
data/brand_mapping_review/nestle_france_snacks_product_name_recovery_audit.csv
data/brand_mapping_review/nestle_france_snacks_product_name_recovery_summary.csv
```

The Nestle recovery audit filename still says `france` for continuity with the
first pilot, but the file now contains all approved Nestle snack recovery
sources for France, UK/Ireland, and US/Canada.

This stage is frozen for MVP directionally. Remaining `nestle` rows are not
automatically changed unless a future curated, high-confidence rule is
approved.

### Stage 2: top-down strategic company portfolio coverage

Purpose: make sure major parent-company portfolios are not missed because of
messy brand names, regional naming, subbrands, licensing, or aliases.

For priority companies, maintain a curated portfolio table with:

```text
parent_company
brand
aliases
region_scope
category_scope
ownership_status
notes
```

This is portfolio coverage input, not full legal truth. It should prioritise
large companies likely to own many products in the dataset and known
launch-relevant complications.

Examples of scoped or review-sensitive cases:

```text
Nestlé | KitKat | kit kat; kit-kat | non-US / most markets | snacks | market_scoped | US differs
Hershey | KitKat | kit kat; kit-kat | US | snacks | market_scoped | licensed US rights
General Mills | Cheerios | cheerios | US/Canada | cereals | market_scoped | Europe differs
CPW / Nestlé | Cheerios | cheerios | Europe | cereals | market_scoped | cereal JV / regional logic
```

Known tricky cases for MVP review include:

```text
KitKat
Cheerios
Kellogg's / Kellanova / WK Kellogg / Ferrero / Mars
Schweppes
Lipton
Bertolli
Godiva
Anchor
```

Common ownership-resolution outputs:

```text
direct
market_scoped
manual_review
unresolved
licensed_or_partnered
recently_changed_market_scoped
mapped_from_manual_review_replacement
```

Output:

```text
data/brand_mapping_review/top_company_portfolio_match_audit.csv
```

#### Nestlé portfolio source matrix

As of 24 August 2026, the first Nestlé-specific top-down portfolio matrix was
used as an intermediate audit source for the Top 9 mapping build. The locked
launch input is now consolidated in:

```text
data/reference/top_company_brand_portfolio_matrix.csv
```

The Nestlé-specific intermediate file is no longer a production reference
input. It combined Nestlé's official Brands A-Z page with the project-provided
regional exception matrix for the first review pass, but launch routing is
applied through the consolidated Top 9 matrix and
`data/reference/company_brand_mapping.csv`.

Rows from the official Nestlé source default to `Nestlé` unless a regional
exception is supplied. Exception rows preserve market-specific ownership or
license logic, including KitKat, Smarties, Rolo, Häagen-Dazs, Froneri ice-cream
brands, Cereal Partners Worldwide cereal brands, Starbucks packaged/at-home
coffee, and Ovaltine.

Some exception brands may not appear as exact labels in the official A-Z extract
used for the matrix. For example, the exception source names `Fitness Cereal`
while the official A-Z source lists `Fitness`. These cases are retained with an
explicit note rather than silently harmonized.

### Stage 3: other-big unresolved brand prioritisation

Purpose: after alias unification and strategic portfolio matching, focus manual
review on remaining normalized brands that materially affect coverage.

Group unresolved brands by:

```text
normalized_brand
product_count
countries_or_regions
categories
example_product_names
```

For MVP, a significant unresolved brand is any normalized brand meeting at
least one of these conditions:

```text
product_count >= 50 overall
OR product_count >= 20 within one country-category
OR appears in 2+ MVP regions
```

These thresholds are pragmatic launch thresholds. They can be adjusted after
reviewing the counts, but the goal is to avoid spending launch time on brands
with only one to three observed records.

Outputs:

```text
data/brand_mapping_review/unmapped_normalized_brands_ranked.csv
data/brand_mapping_review/brand_company_mapping_review_needed.csv
data/brand_mapping_review/brand_mapping_summary.csv
```

### Final Top 9 prefix-orphan cleanup

After the Top 9 company routing merge, Julia reviewed a deterministic
starts-with orphan-picking layer. This layer looked only at currently unmapped
brand strings, not product names, and proposed matches only when the orphaned
brand string started with an exact Top 9 portfolio brand token.

The layer was applied with strict allow/reject logic:

```text
Apply:
  rows where apply_to_mapping = True

Do not apply:
  rows where review_decision starts with "reject prefix match"
```

This recovered obvious cases such as Clif Bar and Company -> Clif, Lay's,
Reese's, and true Milka-prefixed strings such as Milka Oreo / MilkaMondelez.
It deliberately rejected false-prefix cases such as Milkadamia != Milka,
Fantasia != Fanta, Essential Everyday != Essentia, and Perrier-Jouët !=
Perrier water.

Audit outputs:

```text
data/brand_mapping_review/top9_brand_prefix_orphan_candidates.csv
data/brand_mapping_review/top9_brand_prefix_orphan_candidates_reviewed.csv
data/brand_mapping_review/top9_brand_prefix_orphan_candidates_applied_decisions.csv
data/brand_mapping_review/top9_brand_prefix_orphan_apply_summary.csv
```

This cleanup is frozen for MVP. Remaining edge cases are not fixed through
broad prefix matching before launch.

### Recommended processing logic

The review scripts should follow this sequence:

```text
1. Extract all raw brand strings from the cleaned product base.
2. Normalize obvious formatting: lowercase, trim, punctuation cleanup, accents,
   and legal suffixes where appropriate.
3. Apply confirmed brand alias rules.
4. Produce bottom-up unmapped-brand audit.
5. Apply curated top-company portfolio mapping.
6. Assign ownership resolution status: direct, market_scoped, manual_review,
   or unresolved.
7. Group remaining unresolved normalized brands by product count.
8. Review significant unresolved brands only.
9. Export local audit files for review.
```

Minimum useful columns across generated brand-mapping audit files:

```text
raw_brand
normalized_brand
parent_company
ownership_resolution_status
market_scope
category_scope
country_or_region
observed_market_region_codes
product_count
example_product_names
mapping_reason
review_note
```

## Two mapping layers

The repository has two separate brand-reference layers:

- `data/reference/brand_alias_mapping.csv` maps observed brand variants to a
  canonical `normalized_brand` string. Confirmed rows are applied during
  cleaning in `pipeline/clean.py`, before products are loaded into the
  database.
- `data/reference/company_brand_mapping.csv` maps normalized brand keys to
  parent companies or scoped ownership-resolution rows. It is not used to
  compute claim taxonomy.

This distinction matters: changing an alias can change stored
`products.normalized_brand` values after re-cleaning/reloading, while changing
the company mapping changes company filters and derived company labels through
`products.resolved_company` without changing product-level claim
classifications. `products.primary_brand` remains a legacy
compatibility/provenance field.

The company mapping CSV includes scoped ownership metadata. Streamlit's company
resolver uses `ownership_resolution_status`, `region_codes_include`,
`region_codes_exclude`, `country_tags_include`, and `country_tags_exclude` for
row-level company attribution.

## File structure

`data/reference/company_brand_mapping.csv` keeps the launch-tested base columns
and adds non-destructive audit metadata columns:

| Column | Description |
|---|---|
| `parent_company` | Current reference parent company maintained for this project. For launch, `Manual review` must not be displayed as a visible company / owner value in Streamlit; unresolved or complex rows are shown as a scoped owner where safe, or as `Other / not mapped to a company`. Reflects the latest project review, not historical ownership and not a guarantee of current legal ownership in every market. |
| `brand` | The brand name as it commonly appears in the source data or in market usage. |
| `primary_brand_db` | Legacy normalized join key retained for compatibility with the reference file. During launch, it should correspond to the normalized brand key used for company routing, not be interpreted as the preferred app brand display field. |
| `category` | Broad product category the brand is primarily associated with. Not a hard constraint — brands may appear in other categories in the actual data. |
| `hq_country` | Legacy metadata field. It is no longer used for routing logic because market scope is easier to audit directly. |
| `notes` | Analyst notes on brand-ownership caveats, licensing conflicts, market-scope limitations, or acquisition status. These are methodologically important and should be read before using a brand in company-level analysis. |
| `ownership_resolution_status` | Ownership-resolution mode: `direct`, `market_scoped`, `manual_review`, `recently_demerged`, `recently_sold_or_spun_off`, or `licensed_or_partnered`. |
| `market_scope` | Human-readable scope for market-specific rows, e.g. `US / Canada` or `Europe / many non-US CPW markets`. |
| `country_tags_include` | Optional pipe-separated OFF country tags that include this row's scope. |
| `country_tags_exclude` | Optional pipe-separated OFF country tags that exclude this row's scope. |
| `region_codes_include` | Optional pipe-separated project region codes that include this row's scope, e.g. `US_CANADA` or `FRANCE|UK_IE|DACH`. |
| `product_scope_note` | Human-readable note explaining when the row should be applied or sent to manual review. |
| `normalized_brand` | Additive audit column mirroring the brand-level entity used for mapping. |
| `category_scope` | Additive audit column for category-level scope. |
| `brand_mapping_source` | Source matrix or review step that produced the row. |
| `source_note` | Source file or source note for audit traceability. |
| `review_note` | Project review note explaining non-obvious routing. |
| `needs_manual_review` | `yes` when the mapping is launch-usable but should remain visible for review. |
| `scope_rule_type` | Machine-readable description of the routing rule type. |
| `region_codes_exclude` | Optional pipe-separated project region codes that exclude this row's scope. |

`ownership_resolution_status` allowed values:

- `direct`: safe enough one-brand-to-one-owner mapping for this project.
- `market_scoped`: ownership depends on market, region, country tags, or
  product scope.
- `manual_review`: do not attribute to a real owner without additional review.
- `recently_demerged`: launch mapping attributes to a recently separated owner
  while preserving a review flag.
- `recently_sold_or_spun_off`: launch mapping attributes to a sold or spun-off
  owner while preserving a review flag.
- `licensed_or_partnered`: ownership or route-to-market is a license,
  partnership, or joint venture; use scoped rows where needed.

Duplicate `primary_brand_db` values are allowed only for scoped ownership,
licensed/partnered, or manual-review cases.

## Launch display rule: no visible Manual review owner

As of 25 August 2026, `Manual review` is treated as a backend ownership status,
not as a user-facing company / owner label.

During `pipeline/load.py`, rows that would otherwise resolve to
`resolved_company = Manual review` are replaced for the launch app using
deterministic fallback rules:

- Cadbury rows are routed by market to The Hershey Company in the United
  States and to Mondelēz International outside the United States;
- Kellogg's rows are routed to `Ferrero / WK Kellogg` in the United States /
  Canada scope and `Mars / Kellanova` outside that scope;
- Lipton rows use the visible scoped label
  `LIPTON Teas and Infusions / Pepsi Lipton channel-scoped`;
- anything still not safely mapped becomes
  `Other / not mapped to a company` with
  `ownership_resolution_status = manual_review`.

The replacement is stored in the loaded product view through
`resolved_company`, while `company_ownership_resolution_status` and
`company_mapping_source` preserve the audit trail.

## Coverage

As of the 24 August 2026 Top 9 launch merge, the mapping file contains 2,221
rows.
The Top 9 rows are sourced from
`data/reference/top_company_brand_portfolio_matrix.csv`, while existing
non-Top-9 mappings such as Bel Group, Emmi, Carrefour, Lactalis, Froneri,
General Mills, and Cereal Partners Worldwide are preserved.

The current mapping file is
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
WK Kellogg's North American cereal business is scoped to Ferrero after Ferrero
completed its acquisition of WK Kellogg Co on September 26, 2025. International
cereal and snack ownership is scoped to Mars/Kellanova where the project's
market/category scope supports that routing. Generic `kellogg's` rows are
therefore represented as `market_scoped` rows plus a `manual_review` fallback.
Specific brand keys such as `frosted flakes`, `froot loops`,
`special k north america`, `special k international`, `rice krispies treats`,
and `kashi` should remain distinct rather than collapsing into generic
`kellogg's`.

**KitKat.** Nestlé owns the KitKat brand globally except in the United
States, where Hershey manufactures and sells KitKat under a perpetual
license. Generic `kitkat` is represented as scoped rows: The Hershey Company
for US country-tagged records and Nestlé for Canada, UK/Ireland, and France.
Generic `kitkat` must not be treated as a direct universal Nestlé mapping.

**Cheerios.** In most markets outside the United States, Cheerios is a
Cereal Partners Worldwide (CPW) brand, a Nestlé/General Mills joint
venture. In the United States and Canada, Cheerios is a General Mills brand.
In Australia and New Zealand it is distributed through CPW but marketed under
the Uncle Tobys brand name. The CSV therefore keeps scoped `cheerios` rows for
General Mills and CPW plus a `Manual review` fallback for missing,
conflicting, or out-of-scope country tags.

**Top 9 launch routing.** On 24 August 2026, the Top 9 company matrix was
merged into `company_brand_mapping.csv` using upsert logic. The merge preserves
existing non-Top-9 rows and keeps brand-level entities separate from parent
companies. For example, `kitkat` remains the brand key while parent-company
routing depends on market.

**Unilever ice cream.** Ice cream brands including `magnum`,
`magnum ice cream`, `ben and jerry s`, `cornetto`, `wall s`,
`wall s ice cream`, `carte d or`, `miko`, `solero`, `viennetta`, and `breyers`
are mapped to The Magnum Ice Cream Company with
`ownership_resolution_status = recently_demerged` and
`needs_manual_review = yes`. They are not mapped as direct Unilever assets for
launch.

**Lipton and tea brands.** Dry tea brands such as `lipton dry tea`, `pg tips`,
`tazo`, and `pukka` are mapped to
`LIPTON Teas and Infusions / Ekaterra` with
`ownership_resolution_status = recently_sold_or_spun_off`. Generic `lipton`
is routed to manual review because dry tea and RTD Lipton products have
different ownership or partnership logic. RTD/Pepsi Lipton rows use
`licensed_or_partnered` routing where product form is explicit.

**Starbucks.** Starbucks is product/channel-specific. `starbucks coffee at
home`, `starbucks whole bean`, `starbucks k cup`, and
`starbucks via soluble` route to Nestlé or licensed/partnered Nestlé retail
coffee rows where explicit. Starbucks RTD rows route to
PepsiCo / North American Coffee Partnership. Generic `starbucks` remains
manual review.

**Kellanova brands now under Mars.** Mars announced the Kellanova acquisition
in August 2024 and completed it on December 11, 2025. The transaction brought
Pringles, Cheez-It, Pop-Tarts, Rice Krispies Treats, RXBAR, Kellogg's
international cereal brands, and other Kellanova brands into the Mars
portfolio. These are mapped under Mars in this file where the project's
market/category scope supports that routing. Products in the database ingested
before the acquisition date may carry different brand-owner attribution in
their source records.

**Danone / Huel.** Danone announced a definitive agreement to acquire Huel
in March 2026, but Huel is not mapped to Danone until formal closing is
confirmed. The current CSV keeps `huel` under `Huel` with a note that the
announced transaction should be revisited.

**Fonterra consumer brands / Lactalis.** Fonterra sold the majority of its
consumer brands (Anchor, Mainland, Anlene, Anmum, Kapiti, Bega license)
to Lactalis in most markets. An exception applies: Fonterra retained the
Anchor consumer business in Greater China. The mapping reflects this split.

**Accent normalization.** Reference join keys such as `primary_brand_db` are
accent-stripped to match the normalization applied in `clean.py` (NFKD
encoding, ASCII coercion). For example, `gerblé` is stored as `gerble`,
`côte d'or` as `cote d or`. Human-readable `brand` / `normalized_brand`
labels should be kept separate from normalized join keys.

## Resolver priority

The intended ownership resolver should use this priority order:

1. Normalize brand via `brand_alias_mapping.csv`.
2. Find all `company_brand_mapping.csv` rows for the normalized brand key.
3. If `market_scoped` rows exist, evaluate region, country, and product-scope
   rules first.
4. If exactly one scoped row matches, assign that `parent_company`.
5. If no scoped row matches and a `manual_review` fallback exists, preserve the
   backend review status but do not expose `Manual review` as the Streamlit
   company / owner label.
6. If exactly one `direct` row exists and no scoped conflict exists, assign
   that `parent_company`.
7. If multiple rows remain or no rule applies, preserve the ambiguity in audit
   fields and use the launch-safe visible fallback
   `Other / not mapped to a company` unless a scoped launch label is approved.

The Streamlit app implements this resolver in `shared/db.py`. It resolves
company ownership against the displayed/normalized brand and the selected
region context, while preserving manual-review status separately from the
visible company / owner label.

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
   company filters and derived company labels. If alias or brand-entity logic
   changes canonical brand strings, re-run `pipeline/clean.py` and then
   `pipeline/load.py --products-only --input data/sample/<latest_clean>.csv`
   so `products.normalized_brand` is regenerated before relying on the
   updated mapping.
