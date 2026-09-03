# Brand and company mapping

## Purpose

Open Food Facts brand data can contain spelling variants, aliases, multiple brands, retailer references, historical labels, manufacturer names, and inconsistent company attribution.

The Food & Beverage Positioning Radar therefore separates:

1. **Normalized brand** — the consumer-facing brand used for brand-level analysis.

2. **Company / owner** — the current canonical owner or reviewed commercial route used for company-level analysis.

3. **Reviewed product override** — an exact GTIN-level correction used when a broad mapping is unsafe.

Brand and company must remain separate. A product branded `KitKat`, `Cadbury Dairy Milk`, `Milbona`, or `Starbucks` should retain the supported consumer-facing brand rather than being renamed to its owner.

The mapping is a curated analytical ownership layer for the Radar, not a universal legal ownership register.

## Scope and status

Regions: `FRANCE`, `UK_IE`, `US_CANADA`

Categories: `snacks`, `beverages`, `cereals`, `dairies`

Products reviewed outside these four categories can be assigned `OUT_OF_SCOPE` through the product-override layer.

Current launch status:

* reviewed retailer/private-label portfolios are complete and **LOCKED**;
* all nine priority manufacturer portfolios are **LOCKED** after product-level audit and regression validation;
* regional-category orphan-brand completion is complete across `FRANCE`, `UK_IE`, and `US_CANADA`;
* France and US/Canada were reviewed, implemented, and validated through the regional-category orphan workflow;
* UK/Ireland had no qualifying orphan candidates at the `>=100` products per region-category threshold;
* the final residual review confirms that no normalized brand with at least 100 products in any single region-category remains under `Other / not mapped to a company` without reviewed resolution.

The launch retailer, company, and regional orphan-mapping cleanup is therefore complete and **LOCKED**.

---

# Mapping architecture

## 1. Normalize the consumer-facing brand

Normalize supported spelling, punctuation, capitalization, accent, and known alias variants to the most specific supported consumer-facing brand.

Normalization is conservative. Generic or collision-prone strings such as `Simply`, `Selection`, `Deluxe`, `ZERO`, `ONE`, `Boost`, `MiO`, or `Protein` must not become reusable aliases without sufficient evidence.

Meaningful ranges and private-label brands should be preserved, for example `Cadbury Dairy Milk`, `Hershey's Kisses`, `Tesco Finest`, `Milbona`, and `Carrefour Bio`.

A raw string that can legitimately represent more than one brand must not be forced into one global alias.

## 2. Resolve current company / owner

Resolve ownership after brand normalization.

The company layer represents the **current canonical operating owner or reviewed commercial route** relevant to the observed product.

Ownership is not assumed to be globally uniform. Region, market, product form, licensing, joint ventures, divestitures, and imported products can require different outcomes for the same brand.

Examples include:

* `KitKat` and `Cadbury` — market-specific rights;

* `Philadelphia`, `Maxwell House`, `Gevalia`, and `Capri Sun` — market/product-specific ownership;

* `Starbucks` — at-home coffee, North American RTD, EMEA chilled RTD, and direct Starbucks products use different routes;

* former Unilever tea and ice-cream portfolios — current ownership differs from historical Unilever ownership.

Project region is evidence, not proof of product market. Imported products can require exact product-level routing.

## 3. Apply reviewed product overrides

Product overrides are exact GTIN decisions used when reviewed product evidence is stronger than reusable brand/company rules.

They can correct brand, company, category, or `OUT_OF_SCOPE` status and must not automatically create reusable aliases.

If the same GTIN has different reviewed outcomes by region, the region-scoped override takes precedence over the unscoped override.

---

# Precedence

```

1. Region-scoped reviewed product override

2. Unscoped reviewed product override

3. Explicit market / product-form / category scoped company rule

4. Exact normalized brand -> company rule

5. Safe validated brand alias

6. Non-exact matching for candidate generation only

7. Other / not mapped to a company

```

Core rules:

* exact reviewed product evidence outranks broad historical portfolio relationships;

* supplier, manufacturer, bottler, importer, distributor, or co-packer does not automatically equal brand owner;

* flavour or licensed-brand text does not automatically become the product brand;

* retailer availability does not establish private-label ownership;

* prefix, substring, regex, and fuzzy matching are candidate-generation tools, not automatic ownership rules.

---

# Reference files

### `brand_alias_mapping.csv`

Validated observed variants -> canonical consumer-facing brands. A reusable variant should have one unambiguous canonical outcome.

### `company_brand_mapping.csv`

Reusable brand -> company routing rules, including explicit scope where it can be represented safely. Unsafe historical relationships should be removed or retained only as non-executable/manual-review guardrails.

After the September 2026 Top-9, retailer/private-label, France, and US/Canada regional-category orphan cleanup, the launch file contains **3,631 rows across 208 parent-company values**.

### `private_label_brand_mapping.csv`

Curated private-label brand architecture. It preserves meaningful consumer-facing private-label brands and sub-brands separately from retailer ownership, which is resolved later at the company layer.

After the completed September 2026 retailer review, the file contains **1,388 reviewed rows**.

### `reviewed_product_mapping_overrides.csv`

Authoritative reviewed GTIN-level decisions and the highest-precedence reference for product-specific corrections. The optional `region` field scopes the override.

After the September 2026 Top-9 and France/US-Canada orphan audits, the file contains **12,577 active reviewed override rows**.

### `top_company_brand_portfolio_matrix.csv`

Portfolio-research and candidate-generation reference for the priority manufacturer universe. It is **not final execution truth** for complex or licensed portfolios; final routing comes from `company_brand_mapping.csv` plus higher-precedence product overrides.

The current launch matrix contains **247 portfolio/discovery rows**.

---

# Retailer and private-label mapping

The reviewed launch retailer/private-label mapping phase is complete and **LOCKED**.

Retailer ownership does not mean collapsing private-label architecture to the retailer name.

Examples: `Carrefour Bio -> Carrefour`, `Milbona -> Lidl`, `Kirkland Signature -> Costco`, `Good & Gather -> Target`, `Tesco Finest -> Tesco`.

Retailer portfolios can differ by market; a private label validated in one market must not automatically become a global alias.

Suppliers, co-packers, distributors, and retailer availability are evidence but do not by themselves establish private-label ownership.

Imported retailer-owned products are allowed when product evidence supports the mapping.

---

# Regional-category orphan-brand completion

An orphan candidate is a normalized consumer-facing brand still assigned to `Other / not mapped to a company` after strategic manufacturer and retailer mapping.

The review threshold is **at least 100 products within one specific project-region × category bucket**, evaluated independently for each `region × category × normalized_brand` combination. A brand does not qualify merely because its total across several categories or regions is at least 100.

Qualifying brands are researched using the same ownership principles. Independent brands are assigned to their own current company-navigation entity rather than left in the generic `Other` bucket. Exact reviewed GTIN evidence has precedence over broad company or alias rules, and category decisions are reviewed independently from ownership.

Do not force an ownership assignment merely to eliminate `Other`. If current ownership cannot be established with sufficiently strong evidence, keep `Other / not mapped to a company`. **False negatives are preferable to false-positive owner assignments.**

This conservative rule applies at product level. Individual reviewed products may remain under `Other / not mapped to a company` when ownership is genuinely ambiguous, but they must not be treated as unfinished work if the ambiguity has already been reviewed. The orphan-completion criterion is brand-bucket based: no unresolved normalized brand may remain at or above the `>=100` threshold within a single region-category.

Reviewed non-brand/operator placeholders, such as no-brand labels or store-counter/distributor tokens, must not become company mappings and should be excluded from future orphan-candidate counts once reviewed. They do not cause product removal by themselves.

`OUT_OF_SCOPE` reviewed product overrides remove products from the app-facing four-category universe while preserving underlying source/provenance rows. Retailer/private-label architecture remains specific: private-label lines are preserved as consumer-facing brands and routed to the retailer only at the company layer.

Launch completion state:

* **FRANCE — LOCKED:** qualifying regional-category orphan brands were reviewed, implemented, and validated.
* **UK_IE — LOCKED:** the residual scan found no qualifying orphan candidates at the `>=100` region-category threshold.
* **US_CANADA — LOCKED:** qualifying regional-category orphan brands were reviewed, implemented, and validated.

The regional-category orphan phase is therefore complete across all launch regions. The final success criterion is satisfied: **no normalized brand with at least 100 products in a single launch region-category remains assigned to `Other / not mapped to a company` without reviewed resolution.**

Future changes to locked-region routing should use the same reference layers, exact-override discipline, conservative ownership standard, residual-orphan validation, and regression checks against previously locked manufacturer and retailer architecture.

---

# Source hierarchy

Use a **first-party-first, research-enhanced** approach:

1. official company/retailer directories, catalogues, corporate sites, reports, and transaction announcements;

2. authoritative supporting sources such as regulatory filings, recalls, trademarks, and acquisition/divestiture documentation;

3. reliable secondary sources where needed;

4. Open Food Facts as product-observation evidence, not primary ownership authority.

Current ownership is preferred over historical ownership unless a historical view is explicitly required.

## Maintenance

For future updates: normalize new variants, update manufacturer/retailer ownership, preserve scoped rules, use exact overrides for unsafe exceptions, re-run orphan review, and regression-test previously locked architecture after material changes.
